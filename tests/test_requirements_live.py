"""Live requirements extraction on Missouri. Paid: run with ``pytest -m llm``.

Missouri has 67 chunks, so this is about 70 DeepSeek Flash calls (a few cents). The
assertions are loose on purpose: they catch a broken prompt or a wiring bug, not
extraction quality, which S12 measures against gold.
"""

import pytest

from rfp_agent.agents.requirements import NODE_DEDUPE, NODE_EXTRACT, extract_requirements
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.splitting import split_document

pytestmark = pytest.mark.llm

SETTINGS = Settings()


@pytest.mark.skipif(
    SETTINGS.generator[0] != "deepseek" or not SETTINGS.deepseek_api_key,
    reason="needs the DeepSeek generator and DEEPSEEK_API_KEY",
)
def test_missouri_extraction(tmp_path):
    parsed = parse_pdf(DATA_DIR / "rfps" / "missouri.pdf")
    split = split_document(parsed)
    rec = RunRecorder("missouri.pdf", SETTINGS.model, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        out, report = extract_requirements(split, title=parsed.title, settings=SETTINGS)
    print(f"\n{report}\n{rec.totals()}")

    ids = out.requirement_ids()
    assert len(ids) > 20 and len(ids) == len(set(ids))
    known = set(split.chunk_ids())
    assert all(set(r.chunk_ids) <= known for r in out.requirements)
    assert all(set(a.chunk_ids) <= known for a in out.ambiguities)
    assert all(set(a.requirement_ids) <= set(ids) for a in out.ambiguities)
    verified = sum(r.quote_verified for r in out.requirements)
    assert verified / len(ids) > 0.8
    assert any("175,000" in r.text for r in out.requirements)  # the budget cap
    nodes = {n.node for n in rec.log.nodes}
    assert NODE_EXTRACT in nodes and NODE_DEDUPE in nodes
    assert rec.totals().cost_usd > 0
