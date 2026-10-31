"""Requirements against gold: recall by matching, precision by judging every item.

Gold is core-only (D23), so recall is measured against gold and precision is judged per
extracted item: a correct boilerplate clause is surplus, not a false positive (D31).

Matching runs in two tiers. **Code** pairs a gold item with every extracted item whose
quote contains, or is contained in, the gold quote (after ``normalise``), whose
statement contains the gold quote, or whose quote shares at least half its words with
the gold quote. **Judge**: each gold item code could not pair is shown with the
extracted items cited on nearby pages, and the judge names the ones that state the same
requirement. Matching is many-to-many: the pipeline splits some gold items in two and
merges others.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, Field

from evals.gold.schema import GoldRequirement, GoldSet
from evals.harness.judge import Judge, exact_ids
from evals.harness.load import EvalRun
from evals.harness.schemas import MatchRecord, RequirementScores, RequirementVerdict
from rfp_agent.schemas import Requirement
from rfp_agent.textmatch import normalise

JACCARD_MIN = 0.5
CONTAIN_MIN_WORDS = 4  # the contained side must be at least this long to count
MATCH_BATCH = 15
PAGE_SLACK = 1
PRECISION_CHUNKS_PER_BATCH = 5
PRECISION_ITEMS_PER_BATCH = 25

_WORD = re.compile(r"[a-z0-9$%]+")


def words(text: str) -> set[str]:
    return set(_WORD.findall(normalise(text)))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def code_score(gold: GoldRequirement, req: Requirement) -> float | None:
    """1.0 for containment, the Jaccard of the quotes when it reaches ``JACCARD_MIN``,
    otherwise ``None`` (no code match)."""
    gq, rq, rt = normalise(gold.quote), normalise(req.quote), normalise(req.text)

    def long_enough(s: str) -> bool:
        return len(s.split()) >= CONTAIN_MIN_WORDS

    if gq and rq and ((long_enough(rq) and rq in gq) or (long_enough(gq) and gq in rq)):
        return 1.0
    if gq and long_enough(gq) and gq in rt:
        return 1.0
    j = jaccard(words(gold.quote), words(req.quote))
    return j if j >= JACCARD_MIN else None


def code_matches(gold: GoldSet, reqs: list[Requirement]) -> dict[str, list[tuple[str, float]]]:
    """gold ID -> [(requirement ID, score)] best first, for every code-tier pair."""
    out: dict[str, list[tuple[str, float]]] = {}
    for g in gold.requirements:
        pairs = [(r.id, s) for r in reqs if (s := code_score(g, r)) is not None]
        out[g.id] = sorted(pairs, key=lambda p: -p[1])
    return out


# --------------------------------------------------------------------------------------
# Judge tier
# --------------------------------------------------------------------------------------


class GoldMatch(BaseModel):
    gold_id: str
    requirement_ids: list[str] = Field(
        description="Extracted IDs that state the same requirement; empty when none does"
    )
    reason: str = Field(description="At most 15 words")


class MatchVerdicts(BaseModel):
    matches: list[GoldMatch]


def _candidates(run: EvalRun, g: GoldRequirement, reqs: list[Requirement]) -> list[Requirement]:
    if g.page is None:
        return reqs
    near = set(range(g.page - PAGE_SLACK, g.page + PAGE_SLACK + 1))
    found = [r for r in reqs if run.pages_of(r) & near]
    return found or reqs


def _batches[T](items: list[T], size: int) -> list[list[T]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def judge_matches(
    run: EvalRun, unmatched: list[GoldRequirement], judge: Judge
) -> dict[str, tuple[list[str], str]]:
    """gold ID -> (matched requirement IDs, reason) from the judge. Unknown requirement
    IDs in the answer are dropped."""
    reqs = run.summary.requirements.requirements
    ordered = sorted(unmatched, key=lambda g: (g.page or 0, g.id))
    batches = _batches(ordered, MATCH_BATCH)

    def one(batch: list[GoldRequirement]) -> list[GoldMatch]:
        cands: dict[str, Requirement] = {}
        for g in batch:
            for r in _candidates(run, g, reqs):
                cands.setdefault(r.id, r)
        gold_block = "\n".join(
            f"{g.id} [{g.strictness}, {g.type}, page {g.page or '?'}] {g.text}\n"
            f"    quote: {g.quote}"
            for g in batch
        )
        cand_block = "\n".join(
            f"{r.id} [{r.strictness}, {r.type}] {r.text}"
            for r in sorted(cands.values(), key=lambda r: r.id)
        )
        schema = exact_ids(MatchVerdicts, "matches", "gold_id", [g.id for g in batch])
        out = judge.call(
            schema, "judge_match", "judge_match", gold=gold_block, candidates=cand_block
        )
        return [
            m.model_copy(update={"requirement_ids": [i for i in m.requirement_ids if i in cands]})
            for m in out.matches
        ]

    result: dict[str, tuple[list[str], str]] = {}
    for answer in judge.map(one, batches):
        for m in answer or []:
            result[m.gold_id] = (list(dict.fromkeys(m.requirement_ids)), m.reason)
    return result


# --------------------------------------------------------------------------------------
# Precision judge
# --------------------------------------------------------------------------------------


class ItemVerdict(BaseModel):
    id: str
    supported: bool = Field(description="The quoted source text states this requirement")
    is_requirement: bool = Field(
        description="An obligation, constraint, deadline, limit or deliverable, not narrative"
    )
    in_scope: bool = Field(description="Core per the scope rule; generic boilerplate is false")
    reason: str = Field(description="At most 15 words; say what is wrong when anything is false")


class ItemVerdicts(BaseModel):
    verdicts: list[ItemVerdict]


def _precision_batches(run: EvalRun) -> list[tuple[list[str], list[Requirement]]]:
    """Group requirements by their first cited chunk, then pack consecutive chunks into
    batches of at most ``PRECISION_CHUNKS_PER_BATCH`` chunks and
    ``PRECISION_ITEMS_PER_BATCH`` items."""
    by_chunk: dict[str, list[Requirement]] = {}
    for r in run.summary.requirements.requirements:
        by_chunk.setdefault(r.chunk_ids[0] if r.chunk_ids else "?", []).append(r)
    batches: list[tuple[list[str], list[Requirement]]] = []
    chunks: list[str] = []
    items: list[Requirement] = []
    for cid, group in by_chunk.items():
        if chunks and (
            len(chunks) >= PRECISION_CHUNKS_PER_BATCH
            or len(items) + len(group) > PRECISION_ITEMS_PER_BATCH
        ):
            batches.append((chunks, items))
            chunks, items = [], []
        chunks.append(cid)
        items.extend(group)
    if items:
        batches.append((chunks, items))
    return batches


def judge_precision(run: EvalRun, judge: Judge) -> dict[str, ItemVerdict]:
    def one(batch: tuple[list[str], list[Requirement]]) -> list[ItemVerdict]:
        _, items = batch
        cited = list(dict.fromkeys(c for r in items for c in r.chunk_ids))
        sources = "\n".join(
            f'<chunk id="{cid}">\n{text}\n</chunk>' for cid, text in run.source_blocks(cited)
        )
        listing = "\n".join(
            f"{r.id} [{r.strictness}, {r.type}] {r.text}\n"
            f"    quote: {r.quote}\n    cites: {', '.join(r.chunk_ids)}"
            for r in items
        )
        schema = exact_ids(ItemVerdicts, "verdicts", "id", [r.id for r in items])
        out = judge.call(
            schema,
            "judge_requirements",
            "judge_requirements",
            sources=sources,
            requirements=listing,
        )
        return out.verdicts

    verdicts: dict[str, ItemVerdict] = {}
    for answer in judge.map(one, _precision_batches(run)):
        for v in answer or []:
            verdicts[v.id] = v
    return verdicts


# --------------------------------------------------------------------------------------
# Scores
# --------------------------------------------------------------------------------------


def _rate(num: int, den: int) -> float:
    return num / den if den else 0.0


def match_gold(run: EvalRun, gold: GoldSet, judge: Judge | None) -> list[MatchRecord]:
    """One record per gold requirement: the code tier, then the judge tier on the gold
    items code could not pair (when a judge is given)."""
    reqs = run.summary.requirements.requirements
    by_id = {r.id: r for r in reqs}
    code = code_matches(gold, reqs)
    unmatched = [g for g in gold.requirements if not code[g.id]]
    judged = judge_matches(run, unmatched, judge) if (judge and unmatched) else {}

    records: list[MatchRecord] = []
    for g in gold.requirements:
        record = MatchRecord(
            gold_id=g.id,
            gold_text=g.text,
            gold_type=g.type.value,
            gold_strictness=g.strictness.value,
            gold_page=g.page,
            quote_verifiable=g.quote_verifiable,
        )
        if code[g.id]:
            ids = [rid for rid, _ in code[g.id]]
            record.matched_ids, record.tier, record.best_id = ids, "code", ids[0]
        elif g.id in judged and judged[g.id][0]:
            ids, reason = judged[g.id]
            record.matched_ids, record.tier, record.best_id = ids, "judge", ids[0]
            record.reason = reason
        elif g.id in judged:
            record.reason = judged[g.id][1]
        if record.best_id:
            best = by_id[record.best_id]
            record.best_type, record.best_strictness = best.type.value, best.strictness.value
        records.append(record)
    return records


def judge_items(run: EvalRun, judge: Judge | None) -> list[RequirementVerdict]:
    """One verdict per extracted requirement; the judged fields stay ``None`` without a
    judge."""
    reqs = run.summary.requirements.requirements
    verdicts: list[RequirementVerdict] = []
    item_verdicts = judge_precision(run, judge) if judge else {}
    for r in reqs:
        v = item_verdicts.get(r.id)
        verdicts.append(
            RequirementVerdict(
                id=r.id,
                text=r.text,
                type=r.type.value,
                strictness=r.strictness.value,
                chunk_ids=r.chunk_ids,
                supported=v.supported if v else None,
                is_requirement=v.is_requirement if v else None,
                in_scope=v.in_scope if v else None,
                reason=v.reason if v else None,
            )
        )
    return verdicts


def assemble_requirements(
    reqs: Sequence[Requirement],
    records: Sequence[MatchRecord],
    verdicts: Sequence[RequirementVerdict],
) -> RequirementScores:
    """The requirement scores from the two judged halves and the run's own counts."""
    matched = [m for m in records if m.tier != "none"]
    reachable = [m for m in records if m.quote_verifiable]
    matched_reachable = [m for m in matched if m.quote_verifiable]
    confusion: dict[str, dict[str, int]] = {}
    for m in matched:
        row = confusion.setdefault(m.gold_type, {})
        row[m.best_type or "?"] = row.get(m.best_type or "?", 0) + 1

    precision = in_scope_share = None
    judged_items = [v for v in verdicts if v.correct is not None]
    if judged_items:
        precision = _rate(sum(bool(v.correct) for v in judged_items), len(judged_items))
        in_scope_share = _rate(sum(bool(v.in_scope) for v in judged_items), len(judged_items))

    return RequirementScores(
        extracted=len(reqs),
        by_type=dict(Counter(r.type.value for r in reqs)),
        by_strictness=dict(Counter(r.strictness.value for r in reqs)),
        gold=len(records),
        gold_reachable=len(reachable),
        matched_gold=len(matched),
        matched_gold_reachable=len(matched_reachable),
        matched_by_code=sum(m.tier == "code" for m in records),
        matched_by_judge=sum(m.tier == "judge" for m in records),
        recall=_rate(len(matched), len(records)),
        recall_reachable=_rate(len(matched_reachable), len(reachable)),
        type_accuracy=_accuracy(matched, "gold_type", "best_type"),
        strictness_accuracy=_accuracy(matched, "gold_strictness", "best_strictness"),
        type_confusion=confusion,
        precision=precision,
        in_scope_share=in_scope_share,
        judged=len(judged_items),
        unverified_quotes=sum(not r.quote_verified for r in reqs),
        matches=list(records),
        verdicts=list(verdicts),
    )


def score_requirements(
    run: EvalRun,
    gold: GoldSet,
    judge: Judge | None,
    *,
    match: bool = True,
    precision: bool = True,
    previous: RequirementScores | None = None,
) -> RequirementScores:
    """Gold matching and the per-item precision judge, either half reusable from
    ``previous`` (scores of the same run) when it is switched off, so one judge prompt
    can be re-run without paying for the other."""
    reqs = run.summary.requirements.requirements
    if match or previous is None:
        records = match_gold(run, gold, judge if match else None)
    else:
        records = previous.matches
    if precision or previous is None:
        verdicts = judge_items(run, judge if precision else None)
    else:
        verdicts = previous.verdicts
    return assemble_requirements(reqs, records, verdicts)


def _accuracy(matched: Iterable[MatchRecord], gold_field: str, best_field: str) -> float | None:
    pairs = [(getattr(m, gold_field), getattr(m, best_field)) for m in matched]
    if not pairs:
        return None
    return sum(a == b for a, b in pairs) / len(pairs)
