"""Live problem statement on Missouri. Paid: run with ``pytest -m llm``.

Hierarchical mode: about 70 chunk summaries plus one synthesis, roughly 2 cents on
DeepSeek Flash. Checks the contract, not the wording: every citation resolves to a chunk
and every list has at least one claim.
"""

import pytest

from rfp_agent.agents.problem import build_problem_statement
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
def test_missouri_problem_statement(tmp_path):
    pdf = DATA_DIR / "rfps" / "missouri.pdf"
    parsed = parse_pdf(pdf)
    split = split_document(parsed)
    rec = RunRecorder("missouri.pdf", SETTINGS.model, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        result = build_problem_statement(split, title=parsed.title, settings=SETTINGS)

    known = set(split.chunk_ids())
    for claim in result.statement.claims():
        print(f"\n- {claim.text} [{', '.join(claim.chunk_ids)}] ({claim.kind.value})")
        assert set(claim.chunk_ids) <= known
    assert result.mode == "hierarchical"
    assert len(result.chunk_summaries) == len(split.chunks())
    assert all(s.error is None for s in result.chunk_summaries)
    assert 10 < sum(s.relevant for s in result.chunk_summaries) < len(split.chunks())
    for name in ("client_situation", "goal", "success_criteria", "constraints"):
        assert getattr(result.statement, name)
    per_node = rec.per_node()
    assert set(per_node) == {"problem_chunk", "problem_synthesis"}
    assert rec.totals().cost_usd > 0
    print(f"\ncost ${rec.totals().cost_usd:.4f}, retries {rec.totals().retries}")
