"""Live end-to-end run of the pipeline on Missouri (S10). Paid; run with ``-m llm``."""

from __future__ import annotations

import pytest

from rfp_agent.config import DATA_DIR, get_settings
from rfp_agent.graph import STAGES, run_pipeline
from rfp_agent.schemas import RunLog, StageStatus

pytestmark = pytest.mark.llm


def test_missouri_end_to_end(tmp_path):
    settings = get_settings()
    if not settings.deepseek_api_key and settings.model.startswith("deepseek:"):
        pytest.skip("DEEPSEEK_API_KEY not set")
    result = run_pipeline(DATA_DIR / "rfps" / "missouri.pdf", runs_dir=tmp_path, run_id="live")
    log = RunLog.model_validate_json((result.run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert [s.stage for s in log.stages if s.status == StageStatus.FINISHED] and sorted(
        s.stage for s in log.stages
    ) == sorted(STAGES)
    assert all(s.status == StageStatus.FINISHED for s in log.stages)
    assert log.totals().cost_usd > 0
    summary = result.summary
    assert len(summary.requirements.requirements) > 20
    assert summary.solution.components
    assert len(summary.risks.risks) >= 3
    assert (result.run_dir / "summary.md").read_text(encoding="utf-8").startswith("# ")
