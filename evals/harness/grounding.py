"""Grounding of every cited assertion: code checks first, then a judge.

Items: the problem statement's claims, each solution component's claims, the solution's
assumptions and each risk (title, description and justification against its cited
requirements and chunks).

**Code.** Every cited ID must resolve. Every number (amounts, counts, dates, years) and
every capitalised name in the item's text must appear in the cited text. This is a
heuristic: it catches an invented figure or a wrong system name cheaply, and it
over-flags a name the model capitalised for style. The judge is the quality number.

**Judge.** Sees only the item and the text of what it cites, never the rest of the RFP,
and says supported, partially or unsupported; for an inference, whether it is a
reasonable inference from that text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, Field, create_model, model_validator

from evals.harness.judge import Judge, exact_ids
from evals.harness.load import EvalRun
from evals.harness.schemas import GroundingItem, GroundingScores, GroundingTally
from rfp_agent.agents.problem import CLAIM_LISTS
from rfp_agent.schemas import Claim
from rfp_agent.textmatch import normalise

GROUNDING_BATCH = 10
OUTPUTS = ("problem", "solution", "risks")

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)*")  # 236.4.6.2 is one token
_DIGIT_SEP = re.compile(r"(?<=\d)[,](?=\d)")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9&.']*")  # MoDOT-approved -> MoDOT, approved
_SENTENCE_START = re.compile(r"(?:^|[.!?:]\s+|\(\s*|[\"“]\s*)$")
# Capitalised words that are style, not facts: sentence glue, document parts, generic
# roles. Kept short on purpose; a miss here costs a false flag, not a wrong score.
STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those", "it", "its", "if", "in", "on", "of",
    "for", "and", "or", "to", "by", "with", "as", "at", "from", "all", "each", "any", "no",
    "rfp", "rfq", "rfi", "request", "proposal", "proposals", "section", "sections", "page",
    "pages", "task", "tasks", "phase", "phases", "contractor", "vendor", "vendors",
    "bidder", "bidders", "offeror", "offerors", "proposer", "proposers", "respondent",
    "respondents", "client", "agency", "state", "city", "county", "department", "project",
    "solution", "system", "i", "ii", "iii", "iv", "v", "vi",
    # Month and day names: the RFP often writes dates as 7/17/2024 while a claim spells
    # the month out; the day and year numbers are still checked.
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday",
}  # fmt: skip


def _digits(text: str) -> str:
    return _DIGIT_SEP.sub("", text)


def entities(text: str) -> list[str]:
    """Numbers (separators stripped) and capitalised words not at a sentence start and
    not in ``STOPWORDS``, in order, without duplicates."""
    found: list[str] = []
    for m in _NUMBER.finditer(text):
        found.append(_digits(m.group()).rstrip(".,"))
    for m in _TOKEN.finditer(text):
        word = re.sub(r"'s$", "", m.group()).rstrip(".'-")  # MoDOT's -> MoDOT
        if not word or not (word[0].isupper()):
            continue
        if _SENTENCE_START.search(text[: m.start()]) and not any(ch.isupper() for ch in word[1:]):
            continue  # "The", "Proposals" at a sentence start; "MHTC", "MoDOT" still count
        if word.lower() in STOPWORDS:
            continue
        found.append(word)
    return list(dict.fromkeys(found))


def missing_entities(text: str, source: str) -> list[str]:
    """The entities of ``text`` that do not occur in ``source``. Numbers must occur as a
    whole number (``175000`` matches ``$175,000.00``, not ``1750000``); names must occur
    as a whole word after ``normalise``."""
    src = normalise(_digits(source))
    out = []
    for e in entities(text):
        if e[0].isdigit():
            ok = re.search(rf"(?<![\d.]){re.escape(e)}(?!\d)", src) is not None
        else:
            ok = re.search(rf"\b{re.escape(normalise(e))}\b", src) is not None
        if not ok:
            out.append(e)
    return out


# --------------------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------------------


def _claim_items(
    output: str, prefix: str, claims: Iterable[Claim], kind: str | None = None
) -> list[GroundingItem]:
    return [
        GroundingItem(
            where=f"{prefix}[{n}]",
            output=output,  # type: ignore[arg-type]
            text=c.text,
            kind=kind or c.kind.value,
            cited=list(c.chunk_ids),
        )
        for n, c in enumerate(claims)
    ]


def collect_items(run: EvalRun) -> list[GroundingItem]:
    s = run.summary
    items: list[GroundingItem] = []
    for name in CLAIM_LISTS:
        items += _claim_items("problem", f"problem.{name}", getattr(s.problem_statement, name))
    for comp in s.solution.components:
        items += _claim_items("solution", f"solution.{comp.id}.claims", comp.claims)
    # Assumptions are positions the bidder takes where the RFP is silent or ambiguous;
    # they are judged on the facts they state and on whether the gap is real.
    items += _claim_items(
        "solution", "solution.assumptions", s.solution.assumptions, kind="assumption"
    )
    for k in s.risks.risks:
        items.append(
            GroundingItem(
                where=f"risks.{k.id}",
                output="risks",
                text=f"{k.title}. {k.description} {k.justification}",
                kind="risk",
                cited=[*k.requirement_ids, *k.chunk_ids],
            )
        )
    for item in items:
        known = [i for i, _ in run.source_blocks(item.cited)]
        item.dangling = [i for i in item.cited if i not in known]
        source = "\n".join(t for _, t in run.source_blocks(item.cited))
        item.missing_entities = missing_entities(item.text, source) if source else []
    return items


# --------------------------------------------------------------------------------------
# Judge
# --------------------------------------------------------------------------------------


class ClaimVerdict(BaseModel):
    id: str
    verdict: str = Field(description="supported | partially | unsupported")
    reasonable_inference: bool | None = Field(
        default=None, description="Only for inference items: does it follow from the text?"
    )
    reason: str = Field(description="At most 20 words; name what is not supported")


class ClaimVerdicts(BaseModel):
    verdicts: list[ClaimVerdict]


VERDICTS = ("supported", "partially", "unsupported")


def _with_verdict_check(base: type[ClaimVerdicts], ids: list[str]) -> type[ClaimVerdicts]:
    schema = exact_ids(base, "verdicts", "id", ids)

    def check(self: ClaimVerdicts) -> ClaimVerdicts:
        bad = [v.id for v in self.verdicts if v.verdict not in VERDICTS]
        if bad:
            raise ValueError(f"verdict must be one of {list(VERDICTS)}; wrong for {bad}")
        return self

    return create_model(
        base.__name__,
        __base__=schema,
        __module__=base.__module__,
        __validators__={"verdict_values": model_validator(mode="after")(check)},
    )


def judge_grounding(run: EvalRun, items: list[GroundingItem], judge: Judge) -> None:
    """Fill ``verdict``, ``reasonable_inference`` and ``reason`` in place for every item
    that cites something that exists. Items are batched in document order so claims that
    share chunks share a batch."""
    todo = [(f"I{n:03d}", it) for n, it in enumerate(items) if run.source_blocks(it.cited)]
    batches = [todo[i : i + GROUNDING_BATCH] for i in range(0, len(todo), GROUNDING_BATCH)]

    def one(batch: list[tuple[str, GroundingItem]]) -> list[ClaimVerdict]:
        cited = list(dict.fromkeys(c for _, it in batch for c in it.cited))
        sources = "\n".join(
            f'<source id="{sid}">\n{text}\n</source>' for sid, text in run.source_blocks(cited)
        )
        listing = "\n".join(
            f"{iid} ({it.kind}) cites {', '.join(i for i in it.cited if i not in it.dangling)}:"
            f"\n    {it.text}"
            for iid, it in batch
        )
        schema = _with_verdict_check(ClaimVerdicts, [iid for iid, _ in batch])
        return judge.call(
            schema, "judge_grounding", "judge_grounding", sources=sources, items=listing
        ).verdicts

    by_id = dict(todo)
    for answer in judge.map(one, batches):
        for v in answer or []:
            it = by_id[v.id]
            it.verdict = v.verdict  # type: ignore[assignment]
            it.reasonable_inference = (
                v.reasonable_inference if it.kind in ("inference", "assumption") else None
            )
            it.reason = v.reason


def tally(items: list[GroundingItem]) -> dict[str, GroundingTally]:
    out = {o: GroundingTally() for o in OUTPUTS}
    for it in items:
        t = out[it.output]
        t.items += 1
        t.uncited += not it.cited
        t.dangling_ids += len(it.dangling)
        t.entity_misses += bool(it.missing_entities)
        if it.verdict is not None:
            t.judged += 1
            setattr(t, it.verdict, getattr(t, it.verdict) + 1)
        if it.reasonable_inference is False:
            t.unreasonable_inferences += 1
    return out


def score_grounding(run: EvalRun, judge: Judge | None) -> GroundingScores:
    items = collect_items(run)
    if judge is not None:
        judge_grounding(run, items, judge)
    return GroundingScores(by_output=tally(items), items=items)
