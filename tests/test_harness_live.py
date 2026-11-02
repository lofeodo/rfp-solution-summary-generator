"""Live: score the committed Federal Way sample with the real judge (about $0.40)."""

from pathlib import Path

import pytest

from evals.harness.judge import Judge, build_judge_model
from evals.harness.load import EvalRun
from evals.harness.score import score_run
from rfp_agent.config import get_settings

pytestmark = pytest.mark.llm
SAMPLE = Path(__file__).resolve().parents[1] / "runs" / "samples" / "federal_way"


@pytest.mark.skipif(not get_settings().anthropic_api_key, reason="ANTHROPIC_API_KEY not set")
def test_score_federal_way_sample_with_the_judge():
    judge = Judge(build_judge_model())
    s = score_run(EvalRun.load(SAMPLE), judge, key="1")
    assert s.judge.failures == 0 and s.judge.totals.cost_usd > 0
    assert (
        s.requirements.precision is not None and s.requirements.judged == s.requirements.extracted
    )
    assert s.problem.checklist_coverage is not None
    assert set(s.solution.rubric) == {"specificity", "feasibility", "consistency"}
    assert s.risks.severity_agreement is not None
    assert sum(t.judged for t in s.grounding.by_output.values()) > 0
