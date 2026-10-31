"""Score one run directory: ``score_run(run, judge=None) -> RunScores``.

With ``judge=None`` only the code metrics are computed (recall by code match, cited
coverage, entity and ID checks, counts, cost); this is what the unit tests and
``score --no-judge`` use. With a judge every judged metric is filled in.

``only`` names the sections to (re)compute; the others are copied from ``previous``
(the run's existing score file) or computed code-only. This is what lets one judge
prompt be re-run for a prompt change without paying for the other five (S13).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from evals.harness.grounding import score_grounding
from evals.harness.judge import Judge
from evals.harness.load import EvalRun
from evals.harness.match import score_requirements
from evals.harness.schemas import RunScores
from evals.harness.sections import score_cost, score_problem, score_risks, score_solution

SECTIONS = ("match", "precision", "problem", "solution", "risks", "grounding", "cost")
# Section -> the judge node it records; ``cost`` has none.
JUDGE_NODES = {
    "match": "judge_match",
    "precision": "judge_requirements",
    "problem": "judge_checklist",
    "solution": "judge_solution",
    "risks": "judge_risks",
    "grounding": "judge_grounding",
}


def parse_sections(spec: Iterable[str] | None) -> set[str] | None:
    """``["match,precision", "cost"]`` -> ``{"match", "precision", "cost"}``; ``None``
    (every section) when nothing is given. Raises ``ValueError`` on an unknown name."""
    if spec is None:
        return None
    out: set[str] = set()
    for entry in spec:
        for part in entry.split(","):
            name = part.strip()
            if not name:
                continue
            if name not in SECTIONS:
                raise ValueError(f"unknown section {name!r}; choose from {', '.join(SECTIONS)}")
            out.add(name)
    return out or None


def score_run(
    run: EvalRun,
    judge: Judge | None = None,
    *,
    key: str | None = None,
    only: Iterable[str] | None = None,
    previous: RunScores | None = None,
) -> RunScores:
    if previous is not None and previous.run_id != run.log.run_id:
        raise ValueError(
            f"previous scores are for run {previous.run_id}, not {run.log.run_id}; "
            "rescore without --only"
        )
    want = set(SECTIONS) if only is None else set(only)
    gold = run.gold()

    def section(name, compute):
        if name in want:
            return compute(judge)
        if previous is not None:
            return getattr(previous, name)
        return compute(None)

    requirements = score_requirements(
        run,
        gold,
        judge,
        match="match" in want,
        precision="precision" in want,
        previous=previous.requirements if previous is not None else None,
    )
    problem = section("problem", lambda j: score_problem(run, gold, j))
    solution = section("solution", lambda j: score_solution(run, j))
    risks = section("risks", lambda j: score_risks(run, j))
    grounding = section("grounding", lambda j: score_grounding(run, j))

    judged_now = judge is not None and bool(want & set(JUDGE_NODES))
    if judged_now:
        judge_cost = judge.cost()  # type: ignore[union-attr]
    else:
        judge_cost = previous.judge if previous is not None else None
    return RunScores(
        rfp=run.rfp,
        run=key or run.run_dir.name,
        run_dir=Path(run.run_dir).as_posix(),
        run_id=run.log.run_id,
        model=run.summary.model,
        scored_at=datetime.now(UTC),
        judged=judged_now or (previous.judged if previous is not None else False),
        requirements=requirements,
        problem=problem,
        solution=solution,
        risks=risks,
        grounding=grounding,
        cost=score_cost(run),
        judge=judge_cost,
    )


def load_scores(path: str | Path) -> RunScores:
    return RunScores.model_validate_json(Path(path).read_text(encoding="utf-8"))
