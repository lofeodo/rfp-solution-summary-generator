"""Pairwise judge for ablations (S13): which of two outputs is better, asked twice with
the order swapped.

A side wins only when both orders prefer it; anything else is a tie, and an answer that
follows the position rather than the content is recorded as order bias. Context is
run-independent (the gold checklist for problem statements, the gold requirements for
solutions) because the two runs' requirement IDs differ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from evals.gold.schema import GoldSet
from evals.harness.judge import Judge
from rfp_agent.agents.problem import CLAIM_LISTS, ProblemResult
from rfp_agent.agents.solution import SolutionResult
from rfp_agent.schemas import ProblemStatement, Solution, SolutionSummary

What = Literal["problem", "solution"]


class Preference(BaseModel):
    preferred: Literal["A", "B", "tie"]
    reason: str = Field(description="At most 40 words: the decisive difference")


class PairwiseResult(BaseModel):
    what: str
    a: str
    b: str
    winner: Literal["a", "b", "tie"]
    order_bias: bool = Field(description="Each order preferred whichever came first (or second)")
    first: Preference = Field(description="a shown as A")
    second: Preference = Field(description="b shown as A")


def load_output(path: str | Path, what: What) -> ProblemStatement | Solution:
    """A problem statement or solution from a run directory, a stage JSON
    (``problem.json``, ``solution.json``) or a ``summary.json``."""
    path = Path(path)
    if path.is_dir():
        path = path / ("problem.json" if what == "problem" else "solution.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "problem_statement" in data:  # summary.json
        summary = SolutionSummary.model_validate(data)
        return summary.problem_statement if what == "problem" else summary.solution
    if what == "problem":
        return ProblemResult.model_validate(data).statement
    return SolutionResult.model_validate(data).solution


def render(output: ProblemStatement | Solution) -> str:
    if isinstance(output, ProblemStatement):
        parts = []
        for name in CLAIM_LISTS:
            lines = "\n".join(
                f"- {c.text}{' (inference)' if c.kind.value == 'inference' else ''}"
                for c in getattr(output, name)
            )
            parts.append(f"{name.replace('_', ' ').capitalize()}:\n{lines}")
        return "\n\n".join(parts)
    comps = "\n".join(f"- {c.title}: {c.description}" for c in output.components)
    assumptions = "\n".join(f"- {a.text}" for a in output.assumptions) or "(none)"
    return f"Summary: {output.summary}\n\nComponents:\n{comps}\n\nAssumptions:\n{assumptions}"


def context_for(gold: GoldSet, what: What) -> str:
    if what == "problem":
        return "\n".join(f"- {g.fact}" for g in gold.checklist)
    return "\n".join(
        f"- [{g.strictness.value}, {g.type.value}] {g.text}" for g in gold.requirements
    )


def compare(
    a: ProblemStatement | Solution,
    b: ProblemStatement | Solution,
    *,
    what: What,
    gold: GoldSet,
    judge: Judge,
    a_name: str = "a",
    b_name: str = "b",
) -> PairwiseResult:
    ctx = context_for(gold, what)
    ra, rb = render(a), render(b)

    def ask(first: str, second: str) -> Preference:
        return judge.call(
            Preference,
            "judge_pairwise",
            "judge_pairwise",
            what="problem statement" if what == "problem" else "solution approach",
            context=ctx,
            output_a=first,
            output_b=second,
        )

    p1, p2 = ask(ra, rb), ask(rb, ra)
    # Map both answers onto a/b: in the second call, "A" is b.
    v1 = {"A": "a", "B": "b", "tie": "tie"}[p1.preferred]
    v2 = {"A": "b", "B": "a", "tie": "tie"}[p2.preferred]
    winner = v1 if v1 == v2 else "tie"
    bias = p1.preferred == p2.preferred and p1.preferred != "tie"
    return PairwiseResult(
        what=what, a=a_name, b=b_name, winner=winner, order_bias=bias, first=p1, second=p2
    )
