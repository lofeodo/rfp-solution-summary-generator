"""Judge agreement: export a sample of verdicts for hand labelling, then compare.

``sample`` draws a seeded sample from the scored runs (four verdict kinds: requirement
precision, grounding, checklist coverage, component/requirement coverage) and writes each
item with its evidence and an empty ``human`` field. The judge's answer is not in the
file, so the labeller cannot anchor on it. Within each kind up to half the items are
drawn from the judge's negative verdicts, because a uniform sample would be almost all
"supported" and say little about the judge's rejections; the rate is therefore over a
negative-enriched sample, and the README says so.

``agree`` joins a labelled file back to the score files by item ID.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from evals.harness.load import EvalRun
from evals.harness.schemas import RunScores

Kind = Literal["precision", "grounding", "checklist", "coverage"]
DEFAULT_COUNTS: dict[str, int] = {"precision": 12, "grounding": 12, "checklist": 8, "coverage": 8}
SEED = 12
ANSWERS: dict[str, str] = {
    "precision": "true if the source states this requirement AND it is a real obligation, "
    "constraint, deadline, limit or deliverable; else false",
    "grounding": "supported | partially | unsupported, judged only against the cited text",
    "checklist": "covered | partial | missing: does the problem statement state this fact?",
    "coverage": "true if the component's description actually meets the requirement; else false",
}


class SampleItem(BaseModel):
    id: str
    kind: str
    question: str
    item: str
    evidence: str
    human: Any = None
    note: str | None = None


def _judge_value(s: RunScores, kind: str, ref: str) -> Any:
    if kind == "precision":
        v = next(v for v in s.requirements.verdicts if v.id == ref)
        return v.correct
    if kind == "grounding":
        return next(i for i in s.grounding.items if i.where == ref).verdict
    if kind == "checklist":
        return next(c for c in s.problem.checklist if c.gold_id == ref).status
    comp, req = ref.split(":")
    return next(
        p for p in s.solution.pairs if p.component_id == comp and p.requirement_id == req
    ).addressed


def _negative(kind: str, value: Any) -> bool:
    return value in (False, "partially", "unsupported", "partial", "missing")


def _candidates(s: RunScores, kind: str) -> list[str]:
    if kind == "precision":
        return [v.id for v in s.requirements.verdicts if v.correct is not None]
    if kind == "grounding":
        return [i.where for i in s.grounding.items if i.verdict is not None]
    if kind == "checklist":
        return [c.gold_id for c in s.problem.checklist if c.status is not None]
    return [
        f"{p.component_id}:{p.requirement_id}"
        for p in s.solution.pairs
        if p.addressed is not None and p.in_scope
    ]


def _render(run: EvalRun, s: RunScores, kind: str, ref: str) -> tuple[str, str]:
    """``(item, evidence)`` text for one sampled verdict."""
    if kind == "precision":
        r = run.requirements[ref]
        item = f"{r.id} [{r.strictness.value}, {r.type.value}] {r.text}\nquote: {r.quote}"
        evidence = "\n\n".join(f"[{cid}]\n{t}" for cid, t in run.source_blocks(r.chunk_ids))
        return item, evidence
    if kind == "grounding":
        it = next(i for i in s.grounding.items if i.where == ref)
        evidence = "\n\n".join(f"[{cid}]\n{t}" for cid, t in run.source_blocks(it.cited))
        return f"{it.where} ({it.kind}): {it.text}", evidence
    if kind == "checklist":
        c = next(c for c in s.problem.checklist if c.gold_id == ref)
        ps = run.summary.problem_statement
        lines = [
            f"{name}[{n}] {cl.text}"
            for name in ("client_situation", "goal", "success_criteria", "constraints")
            for n, cl in enumerate(getattr(ps, name))
        ]
        return f"{c.gold_id} {c.fact}", "\n".join(lines)
    comp_id, req_id = ref.split(":")
    comp = next(c for c in s.solution.component_records if c.id == comp_id)
    r = run.requirements[req_id]
    return (
        f"{r.id} [{r.strictness.value}, {r.type.value}] {r.text}",
        f"{comp.id} {comp.title}\n{comp.description}",
    )


def sample(
    scores: Sequence[RunScores],
    counts: dict[str, int] | None = None,
    seed: int = SEED,
) -> list[SampleItem]:
    """Spread each kind's count over the runs round-robin; within a run, take negatives
    first up to half the run's share."""
    counts = counts or DEFAULT_COUNTS
    rng = random.Random(seed)
    runs = sorted(scores, key=lambda s: s.key)
    loaded = {s.key: EvalRun.load(s.run_dir) for s in runs}
    out: list[SampleItem] = []
    for kind, total in counts.items():
        shares = [total // len(runs) + (i < total % len(runs)) for i in range(len(runs))]
        for s, share in zip(runs, shares, strict=True):
            cands = _candidates(s, kind)
            neg = [c for c in cands if _negative(kind, _judge_value(s, kind, c))]
            pos = [c for c in cands if c not in neg]
            rng.shuffle(neg)
            rng.shuffle(pos)
            take = neg[: share // 2]
            take += pos[: share - len(take)]
            if len(take) < share:
                take += [c for c in neg if c not in take][: share - len(take)]
            for ref in take:
                item, evidence = _render(loaded[s.key], s, kind, ref)
                out.append(
                    SampleItem(
                        id=f"{s.key}|{kind}|{ref}",
                        kind=kind,
                        question=ANSWERS[kind],
                        item=item,
                        evidence=evidence,
                    )
                )
    return out


def write_sample(items: Sequence[SampleItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([i.model_dump() for i in items], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_sample(path: Path) -> list[SampleItem]:
    return [SampleItem.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8"))]


def _same(kind: str, human: Any, judge: Any) -> bool:
    return human == judge


def agree(labels: Sequence[SampleItem], scores: Sequence[RunScores]) -> dict:
    """Agreement per kind and overall, plus grounding collapsed to supported vs not.
    Items without a human label are skipped and counted."""
    by_key = {s.key: s for s in scores}
    by_kind: dict[str, dict[str, Any]] = {}
    disagreements = []
    binary = {"items": 0, "agree": 0}
    unlabelled = 0
    for item in labels:
        if item.human is None:
            unlabelled += 1
            continue
        key, kind, ref = item.id.split("|", 2)
        judge = _judge_value(by_key[key], kind, ref)
        ok = _same(kind, item.human, judge)
        k = by_kind.setdefault(kind, {"items": 0, "agree": 0})
        k["items"] += 1
        k["agree"] += ok
        if kind == "grounding":
            binary["items"] += 1
            binary["agree"] += (item.human == "supported") == (judge == "supported")
        if not ok:
            disagreements.append({"id": item.id, "human": item.human, "judge": judge})
    for k in by_kind.values():
        k["rate"] = k["agree"] / k["items"] if k["items"] else None
    if binary["items"]:
        by_kind["grounding (supported vs not)"] = {
            **binary,
            "rate": binary["agree"] / binary["items"],
        }
    exact = [v for name, v in by_kind.items() if "(" not in name]
    items = sum(v["items"] for v in exact)
    agreed = sum(v["agree"] for v in exact)
    return {
        "items": items,
        "agree": agreed,
        "rate": agreed / items if items else None,
        "unlabelled": unlabelled,
        "by_kind": by_kind,
        "disagreements": disagreements,
    }
