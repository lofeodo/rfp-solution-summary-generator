"""Run-to-run consistency for one RFP: spread of the headline numbers and overlap of
what was found.

DeepSeek is not deterministic at temperature 0 (S5, S6), so one run is an anecdote. Each
metric is summarised as n, mean, sample standard deviation, min and max; the overlap of
the matched gold requirements and of the covered checklist facts between every pair of
runs is a Jaccard mean.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from itertools import combinations

from pydantic import BaseModel

from evals.harness.schemas import RunScores

Metric = Callable[[RunScores], float | None]


def _unsupported(output: str) -> Metric:
    return lambda s: (
        s.grounding.by_output[output].unsupported_claims
        if s.grounding.by_output[output].judged
        else None
    )


def _rubric(name: str) -> Metric:
    return lambda s: s.solution.rubric[name].score if name in s.solution.rubric else None


METRICS: dict[str, Metric] = {
    "requirements": lambda s: s.requirements.extracted,
    "recall": lambda s: s.requirements.recall,
    "recall_code": lambda s: (
        s.requirements.matched_by_code / s.requirements.gold if s.requirements.gold else None
    ),
    "recall_reachable": lambda s: s.requirements.recall_reachable,
    "precision": lambda s: s.requirements.precision,
    "in_scope_share": lambda s: s.requirements.in_scope_share,
    "type_accuracy": lambda s: s.requirements.type_accuracy,
    "strictness_accuracy": lambda s: s.requirements.strictness_accuracy,
    "checklist_coverage": lambda s: s.problem.checklist_coverage,
    "unsupported_problem": _unsupported("problem"),
    "unsupported_solution": _unsupported("solution"),
    "unsupported_risks": _unsupported("risks"),
    "entity_misses": lambda s: sum(t.entity_misses for t in s.grounding.by_output.values()),
    "components": lambda s: s.solution.components,
    "judged_coverage": lambda s: s.solution.judged_coverage,
    "specificity": _rubric("specificity"),
    "feasibility": _rubric("feasibility"),
    "consistency": _rubric("consistency"),
    "risks": lambda s: s.risks.risks,
    "severity_agreement": lambda s: s.risks.severity_agreement,
    "cost_usd": lambda s: s.cost.cost_usd,
    "wall_s": lambda s: s.cost.wall_s,
}


class Stats(BaseModel):
    n: int
    mean: float
    sd: float
    min: float
    max: float


def stats(values: Sequence[float | None]) -> Stats | None:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    return Stats(
        n=len(vals),
        mean=statistics.fmean(vals),
        sd=statistics.stdev(vals) if len(vals) > 1 else 0.0,
        min=min(vals),
        max=max(vals),
    )


def jaccard_mean(sets: Sequence[set[str]]) -> float | None:
    pairs = list(combinations(sets, 2))
    if not pairs:
        return None
    vals = [len(a & b) / len(a | b) if (a | b) else 1.0 for a, b in pairs]
    return statistics.fmean(vals)


class Consistency(BaseModel):
    rfp: str
    runs: list[str]
    metrics: dict[str, Stats]
    matched_gold_jaccard: float | None = None
    checklist_jaccard: float | None = None


def consistency(rfp: str, scores: Sequence[RunScores]) -> Consistency:
    metrics = {}
    for name, fn in METRICS.items():
        s = stats([fn(x) for x in scores])
        if s is not None:
            metrics[name] = s
    matched = [{m.gold_id for m in x.requirements.matches if m.tier != "none"} for x in scores]
    judged_checklists = [x for x in scores if x.problem.checklist_coverage is not None]
    covered = [
        {c.gold_id for c in x.problem.checklist if c.status == "covered"} for x in judged_checklists
    ]
    return Consistency(
        rfp=rfp,
        runs=[x.run for x in scores],
        metrics=metrics,
        matched_gold_jaccard=jaccard_mean(matched),
        checklist_jaccard=jaccard_mean(covered) if len(covered) > 1 else None,
    )
