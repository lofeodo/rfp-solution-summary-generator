"""Problem statement (S6): what the client is asking for and why, with citations.

Two paths, selected by ``Settings.full_text_problem`` (the S13 ablation):

- **Hierarchical** (production): stage one summarises every chunk on its own with one
  ``structured_call`` per chunk, run concurrently; code attaches the chunk ID, so the
  model never writes a citation at this stage. Stage two synthesises the relevant
  summaries into a ``ProblemStatement`` whose every claim cites chunk IDs.
- **Full text** (baseline): one synthesis call over the own text of every chunk, labelled
  with the same IDs, through the same prompt. The evidence is the only variable.

Citations are checked inside the retry loop: the synthesis schema is a per-call subclass
of ``ProblemStatement`` whose validator rejects a chunk ID that was not in the evidence
and rejects an empty claim list, so ``structured_call`` feeds the offending IDs back and
retries. When the retry budget is exhausted the node raises; nothing is dropped
silently. A stage-one call that fails after its retries is kept as a not-relevant
summary carrying the error, so one flaky call cannot stop a seventy-call stage.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Literal

from langchain_core.messages import HumanMessage
from pydantic import create_model, model_validator

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
    Chunk,
    ChunkSummary,
    ChunkSummaryDraft,
    ProblemStatement,
    SplitDocument,
    StrictModel,
    validate_ids_exist,
)
from rfp_agent.splitting.chunker import own_text

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

CHUNK_NODE = "problem_chunk"
SYNTHESIS_NODE = "problem_synthesis"
FULL_TEXT_NODE = "problem_full_text"
CHUNK_PROMPT = "problem_chunk"
SYNTHESIS_PROMPT = "problem_synthesis"

HIERARCHICAL_EVIDENCE = (
    "Below are summaries of the relevant chunks of the RFP, in document order, each "
    "written from that chunk alone."
)
FULL_TEXT_EVIDENCE = "Below is the full text of the RFP, split into chunks in document order."

CLAIM_LISTS = ("client_situation", "goal", "success_criteria", "constraints")

ProblemMode = Literal["hierarchical", "full_text"]


class ProblemResult(StrictModel):
    """What the step produced: the statement plus, in hierarchical mode, the stage-one
    summaries (for the UI and for debugging which chunks fed the synthesis)."""

    mode: ProblemMode
    statement: ProblemStatement
    chunk_summaries: list[ChunkSummary] = []


class NoEvidenceError(RuntimeError):
    """Stage one marked every chunk irrelevant, so there is nothing to synthesise."""


# --------------------------------------------------------------------------------------
# Stage one: one summary per chunk
# --------------------------------------------------------------------------------------


def section_path_of(chunk: Chunk) -> str:
    return " > ".join(chunk.section_path)


def pages_of(chunk: Chunk) -> str:
    if chunk.page_end == chunk.page_start:
        return str(chunk.page_start)
    return f"{chunk.page_start}-{chunk.page_end}"


def render_chunk_prompt(chunk: Chunk, *, title: str, prompt: Prompt | None = None) -> str:
    prompt = prompt or load_prompt(CHUNK_PROMPT)
    return prompt.render(
        title=title,
        chunk_id=chunk.id,
        section_path=section_path_of(chunk),
        pages=pages_of(chunk),
        text=chunk.text.strip() or "(empty)",
    )


def summarise_chunk(
    chunk: Chunk,
    *,
    title: str,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    prompt: Prompt | None = None,
) -> ChunkSummary:
    """One LLM call for one chunk. The chunk ID is attached here, by code.

    A relevant verdict with an empty summary carries no evidence and is recorded as not
    relevant. A call that fails after its retries returns a not-relevant summary with the
    error text instead of raising.
    """
    text = render_chunk_prompt(chunk, title=title, prompt=prompt)
    try:
        result = structured_call(
            model,
            ChunkSummaryDraft,
            [HumanMessage(text)],
            node=CHUNK_NODE,
            settings=settings,
            recorder=recorder,
            config=config,
        )
    except StructuredOutputError as error:
        logger.warning("%s: chunk %s failed, kept as not relevant: %s", CHUNK_NODE, chunk.id, error)
        return ChunkSummary(
            chunk_id=chunk.id,
            summary="",
            relevant=False,
            error=f"summary failed after {len(error.attempts)} attempts: {error}",
        )
    draft = result.value
    summary = draft.summary.strip() if draft.relevant else ""
    return ChunkSummary(chunk_id=chunk.id, summary=summary, relevant=bool(summary))


def summarise_chunks(
    split: SplitDocument,
    *,
    title: str,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> list[ChunkSummary]:
    """Stage one over every chunk, ``Settings.llm_concurrency`` calls at a time, results
    in document order. The prompt and the recorder are resolved here, on the calling
    thread, because context variables do not reach ``ThreadPoolExecutor`` workers."""
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    prompt = load_prompt(CHUNK_PROMPT)
    chunks = split.chunks()

    def one(chunk: Chunk) -> ChunkSummary:
        return summarise_chunk(
            chunk,
            title=title,
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
            prompt=prompt,
        )

    workers = max(1, min(settings.llm_concurrency, len(chunks)))
    if workers == 1:
        return [one(c) for c in chunks]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, chunks))


# --------------------------------------------------------------------------------------
# Evidence for the synthesis
# --------------------------------------------------------------------------------------


def _item(chunk: Chunk | None, chunk_id: str, body: str) -> str:
    header = f"[{chunk_id}]"
    if chunk is not None:
        header += f" {section_path_of(chunk)} (pages {pages_of(chunk)})"
    return f"{header}\n{body.strip()}"


def evidence_ids(summaries: Iterable[ChunkSummary]) -> list[str]:
    """The chunk IDs the synthesis may cite in hierarchical mode."""
    return [s.chunk_id for s in summaries if s.relevant and s.summary.strip()]


def format_evidence(summaries: Iterable[ChunkSummary], split: SplitDocument) -> str:
    """Relevant summaries in document order, each labelled with its chunk ID, section
    path and pages."""
    by_id = {c.id: c for c in split.chunks()}
    return "\n\n".join(
        _item(by_id.get(s.chunk_id), s.chunk_id, s.summary)
        for s in summaries
        if s.relevant and s.summary.strip()
    )


def format_full_text(split: SplitDocument) -> tuple[str, list[str]]:
    """Every chunk's own text (the sentence repeated from the previous chunk of the same
    section is stripped), labelled like the summaries, plus the citable IDs."""
    items: list[str] = []
    ids: list[str] = []
    for section in split.sections:
        previous: str | None = None
        for chunk in section.chunks:
            items.append(_item(chunk, chunk.id, own_text(chunk.text, previous)))
            ids.append(chunk.id)
            previous = chunk.text
    return "\n\n".join(items), ids


# --------------------------------------------------------------------------------------
# Stage two: synthesis with citations checked inside the retry loop
# --------------------------------------------------------------------------------------


def problem_schema(allowed_ids: Iterable[str]) -> type[ProblemStatement]:
    """A ``ProblemStatement`` subclass for one synthesis call that rejects an empty claim
    list and any chunk ID outside ``allowed_ids``. The validation error names the list
    and the bad IDs, so the retry feedback tells the model exactly what to fix. The class
    keeps the name ``ProblemStatement`` because it doubles as the tool name."""
    allowed = list(allowed_ids)

    def check(self: ProblemStatement) -> ProblemStatement:
        problems: list[str] = []
        for name in CLAIM_LISTS:
            claims = getattr(self, name)
            if not claims:
                problems.append(f"{name} is empty; every list needs at least one claim")
                continue
            unknown = validate_ids_exist((i for c in claims for i in c.chunk_ids), allowed)
            if unknown:
                problems.append(
                    f"{name} cites chunk IDs that are not in the evidence: {unknown}; "
                    "cite only IDs shown in the evidence"
                )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return create_model(
        "ProblemStatement",
        __base__=ProblemStatement,
        __module__=__name__,
        __validators__={"check_claims": model_validator(mode="after")(check)},
    )


def synthesise(
    evidence: str,
    allowed_ids: Iterable[str],
    *,
    evidence_kind: str,
    title: str,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    node: str = SYNTHESIS_NODE,
) -> ProblemStatement:
    """One synthesis call. Raises ``StructuredOutputError`` when the model cannot produce
    a statement whose citations all resolve within the retry budget."""
    text = load_prompt(SYNTHESIS_PROMPT).render(
        title=title, evidence_kind=evidence_kind, evidence=evidence
    )
    result = structured_call(
        model,
        problem_schema(allowed_ids),
        [HumanMessage(text)],
        node=node,
        settings=settings,
        recorder=recorder,
        config=config,
    )
    # Hand back the plain contract class, not the per-call subclass.
    return ProblemStatement.model_validate(result.value.model_dump())


# --------------------------------------------------------------------------------------
# The step
# --------------------------------------------------------------------------------------


def build_problem_statement(
    split: SplitDocument,
    *,
    title: str | None = None,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    full_text: bool | None = None,
) -> ProblemResult:
    """Build the problem statement for a split document.

    ``full_text`` overrides ``Settings.full_text_problem``. Raises ``NoEvidenceError``
    when stage one finds no relevant chunk, and ``StructuredOutputError`` when the
    synthesis cannot be validated within the retry budget.
    """
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    if full_text is None:
        full_text = settings.full_text_problem
    if model is None:
        model = get_chat_model(settings=settings)
    title = title or "untitled RFP"
    common = dict(title=title, model=model, settings=settings, recorder=recorder, config=config)

    if full_text:
        evidence, ids = format_full_text(split)
        statement = synthesise(
            evidence, ids, evidence_kind=FULL_TEXT_EVIDENCE, node=FULL_TEXT_NODE, **common
        )
        return ProblemResult(mode="full_text", statement=statement)

    summaries = summarise_chunks(split, **common)
    ids = evidence_ids(summaries)
    if not ids:
        raise NoEvidenceError(
            f"{CHUNK_NODE}: none of the {len(summaries)} chunks was found relevant; "
            "nothing to synthesise"
        )
    statement = synthesise(
        format_evidence(summaries, split), ids, evidence_kind=HIERARCHICAL_EVIDENCE, **common
    )
    return ProblemResult(mode="hierarchical", statement=statement, chunk_summaries=summaries)


# --------------------------------------------------------------------------------------
# Debug entry point: python -m rfp_agent.agents.problem <pdf> [--full-text] [--out f.json]
# --------------------------------------------------------------------------------------


def main() -> None:  # pragma: no cover - thin CLI over the functions above
    from pathlib import Path
    from typing import Annotated

    import typer
    from rich.console import Console
    from rich.table import Table

    from rfp_agent.observability import RunRecorder
    from rfp_agent.parsing import parse_pdf
    from rfp_agent.splitting import split_document

    def run(
        pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF")],
        full_text: Annotated[
            bool, typer.Option("--full-text", help="One full-text call instead of two stages")
        ] = False,
        out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
    ) -> None:
        console = Console(stderr=True)
        parsed = parse_pdf(pdf)
        split = split_document(parsed)
        recorder = RunRecorder.from_settings(pdf)
        with recorder.activate(write=False):
            result = build_problem_statement(
                split, title=parsed.title or pdf.name, recorder=recorder, full_text=full_text
            )

        relevant = sum(s.relevant for s in result.chunk_summaries)
        failed = sum(s.error is not None for s in result.chunk_summaries)
        console.print(
            f"[bold]{pdf.name}[/bold] ({result.mode}): {len(split.chunks())} chunks, "
            f"{relevant} relevant, {failed} failed"
        )
        nodes = Table("node", "calls", "in", "out", "cost $", "latency s", "retries")
        counts: dict[str, int] = {}
        for n in recorder.log.nodes:
            counts[n.node] = counts.get(n.node, 0) + 1
        for node, t in recorder.per_node().items():
            nodes.add_row(
                node,
                str(counts[node]),
                str(t.input_tokens),
                str(t.output_tokens),
                f"{t.cost_usd:.4f}",
                f"{t.latency_s:.1f}",
                str(t.retries),
            )
        console.print(nodes)
        for name in CLAIM_LISTS:
            console.print(f"\n[bold]{name}[/bold]")
            for claim in getattr(result.statement, name):
                mark = "" if claim.kind == "fact" else " [italic](inference)[/italic]"
                console.print(f"- {claim.text} [{', '.join(claim.chunk_ids)}]{mark}")

        if out:
            out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            console.print(f"\nwrote {out}")

    typer.run(run)


if __name__ == "__main__":
    main()
