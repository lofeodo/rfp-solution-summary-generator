"""Live parse-quality pass on Federal Way. Paid: run with ``pytest -m llm``.

Federal Way has three flagged pages: p2 (contents, low word count, a false alarm), p5
(ERP module table as an image, real missing content) and p14 (pricing table with merged
cells). Costs a fraction of a cent on DeepSeek Flash.
"""

import pytest

from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.quality import run_quality_pass

pytestmark = pytest.mark.llm

SETTINGS = Settings()


@pytest.mark.skipif(
    SETTINGS.generator[0] != "deepseek" or not SETTINGS.deepseek_api_key,
    reason="needs the DeepSeek generator and DEEPSEEK_API_KEY",
)
def test_federal_way_quality_pass(tmp_path):
    parsed = parse_pdf(DATA_DIR / "rfps" / "federal_way.pdf")
    rec = RunRecorder("federal_way.pdf", SETTINGS.model, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        out, report = run_quality_pass(parsed, settings=SETTINGS)
    for esc in report.escalations:
        print(f"\np{esc.page}: {report.judgements.get(esc.page)}\n  -> {esc}")

    assert report.judged_pages == [2, 5, 14]
    by_page = {e.page: e for e in report.escalations}
    assert by_page[5].confirmed_bad
    assert not by_page[2].confirmed_bad
    assert 2 not in {f.page for f in out.flags}
    assert 5 in {f.page for f in out.flags}
    assert len(rec.log.escalations) == 3
    assert rec.totals().cost_usd > 0
