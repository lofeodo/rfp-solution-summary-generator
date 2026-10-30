"""Score one run directory: ``score_run(run, judge=None) -> RunScores``.

With ``judge=None`` only the code metrics are computed (recall by code match, cited
coverage, entity and ID checks, counts, cost); this is what the unit tests and
``score --no-judge`` use. With a judge every judged metric is filled in.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from evals.harness.grounding import score_grounding
from evals.harness.judge import Judge
from evals.harness.load import EvalRun
from evals.harness.match import score_requirements
from evals.harness.schemas import RunScores
from evals.harness.sections import score_cost, score_problem, score_risks, score_solution


def score_run(run: EvalRun, judge: Judge | None = None, *, key: str | None = None) -> RunScores:
    gold = run.gold()
    return RunScores(
        rfp=run.rfp,
        run=key or run.run_dir.name,
        run_dir=Path(run.run_dir).as_posix(),
        run_id=run.log.run_id,
        model=run.summary.model,
        scored_at=datetime.now(UTC),
        judged=judge is not None,
        requirements=score_requirements(run, gold, judge),
        problem=score_problem(run, gold, judge),
        solution=score_solution(run, judge),
        risks=score_risks(run, judge),
        grounding=score_grounding(run, judge),
        cost=score_cost(run),
        judge=judge.cost() if judge is not None else None,
    )


def load_scores(path: str | Path) -> RunScores:
    return RunScores.model_validate_json(Path(path).read_text(encoding="utf-8"))
