"""Requirements extractor (S5): per-chunk structured extraction, quote verification,
exact and fuzzy dedupe, into a ``RequirementsOutput``.

The LLM does the reading; code owns everything that can be checked:

1. One ``structured_call`` per chunk returns requirements (text, type, strictness,
   verbatim quote), ambiguities and gaps. Code looks every quote up in the chunk
   (``textmatch.find_quote``); if any is missing, the model gets one more turn with the
   failing quotes named. Items whose quote still cannot be found are kept with
   ``quote_verified=False``: a sloppy quote does not make the obligation go away.
2. Code assigns ``R001`` IDs in document order, cites the chunk the item came from and
   folds exact duplicates (same normalised text or quote), which the one-sentence chunk
   overlap of S3 produces routinely.
3. One grouping call returns groups of IDs that state the same obligation and pairs that
   contradict (D6). Code checks the answer (every ID exists, no ID in two groups, no
   conflict pair inside a group), feeds violations back once, then sanitises whatever
   remains so that every original ID lands in exactly one group by construction. Merging
   keeps the representative's text and quote, unions chunk IDs, keeps the stricter
   strictness and lists the absorbed IDs in ``merged_from``. Conflicts are flagged on
   both items and surfaced as an ambiguity, never merged.

``Settings.single_call_extraction`` switches to one call over the whole document (the
D5 ablation baseline): the model then cites chunk IDs itself, code verifies each quote
against the cited chunk and drops items citing unknown chunks; the grouping call is
skipped because the model saw everything at once.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel

from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import (
    Prompt,
    StructuredOutputError,
    get_chat_model,
    load_prompt,
    structured_call,
)
from rfp_agent.observability import current_recorder
from rfp_agent.schemas import (
    STRICTNESS_RANK,
    Ambiguity,
    Chunk,
    ChunkExtraction,
    DedupeOutput,
    DocumentExtraction,
    ExtractedRequirement,
    Gap,
    Requirement,
    RequirementsOutput,
    SplitDocument,
    validate_ids_exist,
)
from rfp_agent.textmatch import find_quote, normalise

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODE_EXTRACT = "requirements_extract"
NODE_EXTRACT_SINGLE = "requirements_extract_single"
NODE_DEDUPE = "requirements_dedupe"
PROMPT_EXTRACT = "requirements_extract"
PROMPT_DEDUPE = "requirements_dedupe"


@dataclass
class RequirementsReport:
    """What the extractor did, for the debug CLI, the run log reader and tests."""

    chunks: int = 0
    single_call: bool = False
    calls_failed: list[str] = field(default_factory=list)  # chunk IDs
    quote_retries: int = 0
    unverified_quotes: list[str] = field(default_factory=list)  # requirement IDs
    dropped_unknown_chunk: int = 0  # single-call items citing a chunk that does not exist
    pre_dedupe: int = 0
    exact_merges: int = 0
    fuzzy_merges: int = 0
    conflicts: int = 0
    dedupe_retried: bool = False
    dedupe_violations: list[str] = field(default_factory=list)
    dedupe_fallback: bool = False
    dedupe_failed: bool = False  # grouping call exhausted its retries; no fuzzy dedupe


# --------------------------------------------------------------------------------------
# Prompt rendering
# --------------------------------------------------------------------------------------

CHUNK_UNIT = (
    "one chunk of the RFP; the other chunks are handled separately, so work only from "
    "the text you are given and never assume what the rest of the document says"
)
DOCUMENT_UNIT = "every chunk of the RFP, in document order"
CHUNK_MODE_RULES = ""
DOCUMENT_MODE_RULES = (
    "- `chunk_id`: the ID of the chunk the quote is copied from, exactly as given below\n"
    "  (for example `S3.2`). Ambiguities and gaps cite the chunks they come from in\n"
    "  `chunk_ids` the same way. Only use IDs that appear below."
)


def format_chunk(chunk: Chunk) -> str:
    pages = (
        str(chunk.page_start)
        if chunk.page_end == chunk.page_start
        else f"{chunk.page_start}-{chunk.page_end}"
    )
    return (
        f"### Chunk {chunk.id}\n"
        f"Section: {' > '.join(chunk.section_path)}\n"
        f"Pages: {pages}\n\n"
        f'<chunk id="{chunk.id}">\n{chunk.text.strip()}\n</chunk>'
    )


def render_chunk_prompt(prompt: Prompt, chunk: Chunk, title: str) -> str:
    return prompt.render(
        unit=CHUNK_UNIT, mode_rules=CHUNK_MODE_RULES, title=title, input=format_chunk(chunk)
    )


def render_document_prompt(prompt: Prompt, chunks: Sequence[Chunk], title: str) -> str:
    return prompt.render(
        unit=DOCUMENT_UNIT,
        mode_rules=DOCUMENT_MODE_RULES,
        title=title,
        input="\n\n".join(format_chunk(c) for c in chunks),
    )


def format_for_dedupe(requirements: Sequence[Requirement]) -> str:
    return "\n".join(
        f'{r.id} [{r.strictness.value}, {r.type.value}] {r.text} — "{r.quote}" '
        f"({', '.join(r.chunk_ids)})"
        for r in requirements
    )


# --------------------------------------------------------------------------------------
# Verified calls: structured output, then a code check, then one feedback turn
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Problem:
    """One thing code found wrong with an item of a reply."""

    index: int
    message: str
    drop: bool = False  # True when the item cannot be kept (it cites nothing real)


def verify_quotes(items: Sequence[ExtractedRequirement], text: str, chunk_id: str) -> list[Problem]:
    return [
        Problem(
            i,
            f'requirements[{i}]: the quote "{r.quote}" was not found verbatim in chunk '
            f"{chunk_id}. Copy the exact span, character for character, or drop the item "
            "if nothing in the chunk states it.",
        )
        for i, r in enumerate(items)
        if not find_quote(text, r.quote)
    ]


def verify_document(extraction: DocumentExtraction, chunks: dict[str, Chunk]) -> list[Problem]:
    problems: list[Problem] = []
    for i, r in enumerate(extraction.requirements):
        chunk = chunks.get(r.chunk_id)
        if chunk is None:
            problems.append(
                Problem(
                    i,
                    f"requirements[{i}]: chunk ID {r.chunk_id} does not exist; use one of "
                    "the chunk IDs given.",
                    drop=True,
                )
            )
        else:
            problems.extend(
                Problem(i, p.message) for p in verify_quotes([r], chunk.text, r.chunk_id)
            )
    return problems


def feedback_for(problems: Sequence[Problem]) -> str:
    lines = "\n".join(f"- {p.message}" for p in problems)
    return (
        "Code checked your output against the chunk text and found these problems:\n"
        f"{lines}\n"
        "Return the full corrected output (every item, not only the fixed ones)."
    )


def verified_call[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    messages: list[BaseMessage],
    verify: Callable[[T], list[Problem]],
    *,
    node: str,
    settings: Settings,
    recorder: RunRecorder | None,
    config: RunnableConfig | None,
) -> tuple[T, list[Problem], bool]:
    """``structured_call`` plus one code-checked retry.

    Returns the reply, the problems that remain, and whether a retry happened. The retry
    is kept only when it has no more problems than the first reply, so a model that makes
    things worse on the second turn cannot regress the output.
    """
    kwargs = dict(node=node, settings=settings, recorder=recorder, config=config)
    first = structured_call(model, schema, messages, **kwargs).value
    problems = verify(first)
    if not problems:
        return first, [], False
    history = [
        *messages,
        AIMessage(content=first.model_dump_json()),
        HumanMessage(feedback_for(problems)),
    ]
    try:
        second = structured_call(model, schema, history, **kwargs).value
    except StructuredOutputError as error:
        logger.info("%s: feedback retry failed, keeping the first reply: %s", node, error)
        return first, problems, True
    second_problems = verify(second)
    if len(second_problems) <= len(problems):
        return second, second_problems, True
    return first, problems, True


# --------------------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------------------


@dataclass
class ChunkResult:
    chunk: Chunk
    extraction: ChunkExtraction | None  # None when the call failed
    unverified: set[int] = field(default_factory=set)
    retried: bool = False


def extract_chunk(
    chunk: Chunk,
    *,
    prompt: Prompt,
    title: str,
    model: BaseChatModel,
    settings: Settings,
    recorder: RunRecorder | None,
    config: RunnableConfig | None,
) -> ChunkResult:
    """Extract from one chunk; a call that exhausts its retries yields no items."""
    messages: list[BaseMessage] = [HumanMessage(render_chunk_prompt(prompt, chunk, title))]
    try:
        extraction, problems, retried = verified_call(
            model,
            ChunkExtraction,
            messages,
            lambda e: verify_quotes(e.requirements, chunk.text, chunk.id),
            node=NODE_EXTRACT,
            settings=settings,
            recorder=recorder,
            config=config,
        )
    except StructuredOutputError as error:
        logger.warning("%s: chunk %s failed, skipping it: %s", NODE_EXTRACT, chunk.id, error)
        return ChunkResult(chunk, None)
    return ChunkResult(chunk, extraction, {p.index for p in problems}, retried)


def extract_chunks(
    chunks: Sequence[Chunk],
    *,
    prompt: Prompt,
    title: str,
    model: BaseChatModel,
    settings: Settings,
    recorder: RunRecorder | None,
    config: RunnableConfig | None,
) -> list[ChunkResult]:
    """One call per chunk, ``settings.extract_concurrency`` at a time, document order kept.

    The recorder is passed explicitly because the context variable that
    ``current_recorder()`` reads does not cross threads.
    """

    def one(chunk: Chunk) -> ChunkResult:
        return extract_chunk(
            chunk,
            prompt=prompt,
            title=title,
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
        )

    workers = max(1, min(settings.extract_concurrency, len(chunks)))
    if workers == 1:
        return [one(c) for c in chunks]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, chunks))


# --------------------------------------------------------------------------------------
# Assembly: IDs, citations, exact dedupe
# --------------------------------------------------------------------------------------


def _rid(n: int) -> str:
    return f"R{n:03d}"


def _aid(n: int) -> str:
    return f"A{n:02d}"


def _gid(n: int) -> str:
    return f"G{n:02d}"


def _union(*lists: Sequence[str]) -> list[str]:
    out: list[str] = []
    for ids in lists:
        for i in ids:
            if i not in out:
                out.append(i)
    return out


def _requirement(n: int, item: ExtractedRequirement, chunk_ids: list[str], verified: bool):
    return Requirement(
        id=_rid(n),
        text=item.text,
        type=item.type,
        strictness=item.strictness,
        quote=item.quote,
        chunk_ids=chunk_ids,
        quote_verified=verified,
    )


def _ambiguity(n: int, description: str, chunk_ids: list[str], requirement_ids: list[str]):
    return Ambiguity(
        id=_aid(n), description=description, chunk_ids=chunk_ids, requirement_ids=requirement_ids
    )


def _map_indexes(indexes: Sequence[int], ids: Sequence[str], where: str) -> list[str]:
    out: list[str] = []
    for i in indexes:
        if 0 <= i < len(ids):
            if ids[i] not in out:
                out.append(ids[i])
        else:
            logger.warning("%s: ambiguity cites requirement index %d of %d", where, i, len(ids))
    return out


def assemble_chunks(
    results: Sequence[ChunkResult],
) -> tuple[list[Requirement], list[Ambiguity], list[Gap]]:
    """Per-chunk replies into cited, numbered items in document order."""
    reqs: list[Requirement] = []
    ambs: list[Ambiguity] = []
    gaps: list[Gap] = []
    for res in results:
        if res.extraction is None:
            continue
        ids: list[str] = []
        for i, item in enumerate(res.extraction.requirements):
            reqs.append(_requirement(len(reqs) + 1, item, [res.chunk.id], i not in res.unverified))
            ids.append(reqs[-1].id)
        for a in res.extraction.ambiguities:
            cited = _map_indexes(a.requirement_indexes, ids, res.chunk.id)
            ambs.append(_ambiguity(len(ambs) + 1, a.description, [res.chunk.id], cited))
        for g in res.extraction.gaps:
            gaps.append(
                Gap(
                    id=_gid(len(gaps) + 1),
                    description=g.description,
                    chunk_ids=[res.chunk.id],
                    referenced_document=g.referenced_document,
                )
            )
    return reqs, ambs, gaps


def assemble_document(
    extraction: DocumentExtraction,
    problems: Sequence[Problem],
    chunk_order: dict[str, int],
) -> tuple[list[Requirement], list[Ambiguity], list[Gap], int]:
    """Single-call reply into numbered items ordered by cited chunk; items citing an
    unknown chunk are dropped. Returns the dropped count as well."""
    drop = {p.index for p in problems if p.drop}
    unverified = {p.index for p in problems if not p.drop}
    keep = [i for i in range(len(extraction.requirements)) if i not in drop]
    keep.sort(key=lambda i: (chunk_order[extraction.requirements[i].chunk_id], i))
    reqs: list[Requirement] = []
    id_of: dict[int, str] = {}
    for i in keep:
        item = extraction.requirements[i]
        reqs.append(_requirement(len(reqs) + 1, item, [item.chunk_id], i not in unverified))
        id_of[i] = reqs[-1].id
    ids_by_index = [id_of.get(i, "") for i in range(len(extraction.requirements))]
    known = set(chunk_order)
    ambs: list[Ambiguity] = []
    for a in extraction.ambiguities:
        chunk_ids = [c for c in a.chunk_ids if c in known]
        if not chunk_ids:
            logger.warning("%s: ambiguity cites no known chunk, dropped", NODE_EXTRACT_SINGLE)
            continue
        cited = [r for r in _map_indexes(a.requirement_indexes, ids_by_index, "document") if r]
        ambs.append(_ambiguity(len(ambs) + 1, a.description, chunk_ids, cited))
    gaps = [
        Gap(
            id=_gid(n),
            description=g.description,
            chunk_ids=[c for c in g.chunk_ids if c in known],
            referenced_document=g.referenced_document,
        )
        for n, g in enumerate(extraction.gaps, 1)
    ]
    return reqs, ambs, gaps, len(drop)


def merge_into(keeper: Requirement, absorbed: Requirement) -> Requirement:
    """Fold ``absorbed`` into ``keeper``: union of chunk IDs, stricter strictness, lineage.
    The keeper's quote stays unless it is unverified and the absorbed one is verified."""
    quote, verified = keeper.quote, keeper.quote_verified
    if not verified and absorbed.quote_verified:
        quote, verified = absorbed.quote, True
    stricter = max(keeper.strictness, absorbed.strictness, key=STRICTNESS_RANK.__getitem__)
    return keeper.model_copy(
        update={
            "chunk_ids": _union(keeper.chunk_ids, absorbed.chunk_ids),
            "strictness": stricter,
            "quote": quote,
            "quote_verified": verified,
            "merged_from": _union(keeper.merged_from, [absorbed.id], absorbed.merged_from),
            "conflicts_with": _union(keeper.conflicts_with, absorbed.conflicts_with),
        }
    )


def exact_dedupe(reqs: Sequence[Requirement]) -> tuple[list[Requirement], dict[str, str]]:
    """Fold items whose normalised text or quote equals an earlier item's.

    Returns the survivors and a map from every folded ID to the ID it landed in.
    """
    by_key: dict[str, int] = {}
    out: list[Requirement] = []
    fold: dict[str, str] = {}
    for r in reqs:
        keys = [k for k in (normalise(r.text), normalise(r.quote)) if k]
        hit = next((by_key[k] for k in keys if k in by_key), None)
        if hit is None:
            for k in keys:
                by_key.setdefault(k, len(out))
            out.append(r)
        else:
            out[hit] = merge_into(out[hit], r)
            fold[r.id] = out[hit].id
            for k in keys:
                by_key.setdefault(k, hit)
    return out, fold


def remap_ids(ids: Sequence[str], fold: dict[str, str]) -> list[str]:
    return _union([fold.get(i, i) for i in ids])


# --------------------------------------------------------------------------------------
# Fuzzy dedupe: the grouping call and its checks
# --------------------------------------------------------------------------------------


def check_groups(output: DedupeOutput, ids: Sequence[str]) -> list[str]:
    """Violations of the grouping contract, as sentences the model can act on."""
    known = set(ids)
    problems: list[str] = []
    seen: dict[str, int] = {}
    for n, g in enumerate(output.groups):
        members = [g.representative_id, *g.member_ids]
        for m in validate_ids_exist(members, known):
            problems.append(f"group {n}: requirement ID {m} does not exist")
        if g.representative_id in g.member_ids:
            problems.append(f"group {n}: representative {g.representative_id} is also a member")
        for m in members:
            if m in seen and seen[m] != n:
                problems.append(f"{m} appears in group {seen[m]} and group {n}")
            seen.setdefault(m, n)
    for c in output.conflicts:
        for m in validate_ids_exist(c.requirement_ids, known):
            problems.append(f"conflict: requirement ID {m} does not exist")
        groups = {seen[m] for m in c.requirement_ids if m in seen}
        if len(groups) == 1 and sum(m in seen for m in c.requirement_ids) > 1:
            problems.append(
                f"conflicting items {', '.join(c.requirement_ids)} are inside the same group"
            )
    return _union(problems)


def sanitise_groups(output: DedupeOutput, ids: Sequence[str]) -> DedupeOutput:
    """Make any grouping answer satisfy the contract: unknown IDs are dropped, an ID keeps
    its first appearance only, a conflict pair inside a group loses the non-representative
    item, and groups left with no member disappear. Every surviving requirement is then
    in exactly one group or in none, so merging is safe."""
    known = set(ids)
    conflicts = [
        c.model_copy(
            update={"requirement_ids": _union([i for i in c.requirement_ids if i in known])}
        )
        for c in output.conflicts
    ]
    conflicts = [c for c in conflicts if len(c.requirement_ids) >= 2]
    conflicting: set[frozenset[str]] = set()
    for c in conflicts:
        for a in c.requirement_ids:
            for b in c.requirement_ids:
                if a != b:
                    conflicting.add(frozenset((a, b)))
    used: set[str] = set()
    groups = []
    for g in output.groups:
        rep = g.representative_id
        if rep not in known or rep in used:
            continue
        members: list[str] = []
        for m in g.member_ids:
            if m not in known or m == rep or m in used or m in members:
                continue
            if any(frozenset((m, other)) in conflicting for other in (rep, *members)):
                continue
            members.append(m)
        if members:
            used.update((rep, *members))
            groups.append(g.model_copy(update={"representative_id": rep, "member_ids": members}))
    return DedupeOutput(groups=groups, conflicts=conflicts)


def apply_groups(
    reqs: Sequence[Requirement], output: DedupeOutput
) -> tuple[list[Requirement], dict[str, str]]:
    """Merge a sanitised grouping into the requirement list, keeping document order.
    Returns the survivors and the fold map (member ID -> representative ID)."""
    by_id = {r.id: r for r in reqs}
    fold: dict[str, str] = {}
    for g in output.groups:
        keeper = by_id[g.representative_id]
        for m in g.member_ids:
            keeper = merge_into(keeper, by_id.pop(m))
            fold[m] = g.representative_id
        by_id[g.representative_id] = keeper
    return [by_id[r.id] for r in reqs if r.id in by_id], fold


def apply_conflicts(
    reqs: Sequence[Requirement],
    output: DedupeOutput,
    fold: dict[str, str],
    ambiguities: list[Ambiguity],
) -> tuple[list[Requirement], int]:
    """Mark conflicting items on each other and add one ambiguity per conflict."""
    by_id = {r.id: r for r in reqs}
    applied = 0
    for c in output.conflicts:
        ids = [i for i in remap_ids(c.requirement_ids, fold) if i in by_id]
        if len(ids) < 2:
            continue
        for i in ids:
            others = [o for o in ids if o != i]
            by_id[i] = by_id[i].model_copy(
                update={"conflicts_with": _union(by_id[i].conflicts_with, others)}
            )
        ambiguities.append(
            _ambiguity(
                len(ambiguities) + 1,
                f"Conflicting requirements {' and '.join(ids)}: {c.reason}",
                _union(*(by_id[i].chunk_ids for i in ids)),
                ids,
            )
        )
        applied += 1
    return [by_id[r.id] for r in reqs], applied


def dedupe_llm(
    reqs: Sequence[Requirement],
    *,
    model: BaseChatModel,
    settings: Settings,
    recorder: RunRecorder | None,
    config: RunnableConfig | None,
    report: RequirementsReport,
) -> DedupeOutput:
    """The grouping call with one feedback retry on contract violations, then sanitised.
    A call that fails outright returns an empty grouping (no fuzzy dedupe, run continues)."""
    ids = [r.id for r in reqs]
    prompt = load_prompt(PROMPT_DEDUPE)
    messages: list[BaseMessage] = [
        HumanMessage(prompt.render(requirements=format_for_dedupe(reqs)))
    ]
    try:
        output, problems, retried = verified_call(
            model,
            DedupeOutput,
            messages,
            lambda o: [Problem(0, p) for p in check_groups(o, ids)],
            node=NODE_DEDUPE,
            settings=settings,
            recorder=recorder,
            config=config,
        )
    except StructuredOutputError as error:
        logger.warning("%s: grouping call failed, no fuzzy dedupe: %s", NODE_DEDUPE, error)
        report.dedupe_failed = True
        return DedupeOutput()
    report.dedupe_retried = retried
    report.dedupe_violations = [p.message for p in problems]
    report.dedupe_fallback = bool(problems)
    return sanitise_groups(output, ids)


def _same_document(a: str, b: str) -> bool:
    """``"attachment f"`` and ``"attachment f: software requirements"`` name one document;
    the shorter name must end at a word boundary of the longer one."""
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    return long.startswith(short) and long[len(short)] in " :-,.(/"


def dedupe_gaps(gaps: Sequence[Gap]) -> list[Gap]:
    """Fold gaps that name the same document (or, unnamed, say the same thing); the
    first mention keeps its wording and collects every chunk ID."""
    keys: list[str] = []
    out: list[Gap] = []
    for g in gaps:
        key = normalise(g.referenced_document or g.description)
        hit = next((i for i, k in enumerate(keys) if _same_document(k, key)), None)
        if hit is None:
            keys.append(key)
            out.append(g.model_copy(update={"id": _gid(len(out) + 1)}))
        else:
            out[hit] = out[hit].model_copy(
                update={"chunk_ids": _union(out[hit].chunk_ids, g.chunk_ids)}
            )
    return out


# --------------------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------------------


def extract_requirements(
    split: SplitDocument,
    *,
    title: str | None = None,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    single_call: bool | None = None,
) -> tuple[RequirementsOutput, RequirementsReport]:
    """Extract, verify, cite and dedupe the requirements of a split document.

    ``single_call`` defaults to ``Settings.single_call_extraction``. Every LLM call goes
    through ``structured_call`` and lands on ``recorder`` (or the active one).
    """
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    if single_call is None:
        single_call = settings.single_call_extraction
    chunks = split.chunks()
    report = RequirementsReport(chunks=len(chunks), single_call=single_call)
    if not chunks:
        return RequirementsOutput(), report
    if model is None:
        model = get_chat_model(settings=settings)
    title = title or "untitled RFP"
    prompt = load_prompt(PROMPT_EXTRACT)
    kwargs = dict(settings=settings, recorder=recorder, config=config)

    if single_call:
        by_id = {c.id: c for c in chunks}
        order = {c.id: n for n, c in enumerate(chunks)}
        messages: list[BaseMessage] = [HumanMessage(render_document_prompt(prompt, chunks, title))]
        extraction, problems, retried = verified_call(
            model,
            DocumentExtraction,
            messages,
            lambda e: verify_document(e, by_id),
            node=NODE_EXTRACT_SINGLE,
            **kwargs,
        )
        report.quote_retries = int(retried)
        reqs, ambs, gaps, dropped = assemble_document(extraction, problems, order)
        report.dropped_unknown_chunk = dropped
    else:
        results = extract_chunks(chunks, prompt=prompt, title=title, model=model, **kwargs)
        report.calls_failed = [r.chunk.id for r in results if r.extraction is None]
        report.quote_retries = sum(r.retried for r in results)
        reqs, ambs, gaps = assemble_chunks(results)

    report.pre_dedupe = len(reqs)
    reqs, fold = exact_dedupe(reqs)
    report.exact_merges = len(fold)

    grouping = DedupeOutput()
    if not single_call and len(reqs) >= 2:
        grouping = dedupe_llm(reqs, model=model, report=report, **kwargs)
        reqs, fuzzy_fold = apply_groups(reqs, grouping)
        report.fuzzy_merges = len(fuzzy_fold)
        fold = {k: fuzzy_fold.get(v, v) for k, v in fold.items()} | fuzzy_fold

    ambs = [
        a.model_copy(update={"requirement_ids": remap_ids(a.requirement_ids, fold)}) for a in ambs
    ]
    reqs, report.conflicts = apply_conflicts(reqs, grouping, fold, ambs)
    report.unverified_quotes = [r.id for r in reqs if not r.quote_verified]
    output = RequirementsOutput(requirements=reqs, ambiguities=ambs, gaps=dedupe_gaps(gaps))
    return output, report


if __name__ == "__main__":  # pragma: no cover
    from rfp_agent.agents.requirements_cli import main

    main()
