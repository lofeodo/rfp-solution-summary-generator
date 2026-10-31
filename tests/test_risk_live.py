"""Live risk assessment on Missouri. Paid: run with ``pytest -m llm``.

Runs the quality pass, the requirements extractor, the problem statement and the
solution generator first (about 10 cents on DeepSeek Flash), then the risk assessor.
Checks the contract, not the wording: every cited ID exists, every uncovered mandatory
requirement is cited by a risk, the count is within the band, and the output assembles
and renders.
"""

import pytest

from rfp_agent.agents.problem import build_problem_statement
from rfp_agent.agents.requirements import extract_requirements
from rfp_agent.agents.risk import MAX_RISKS, MIN_RISKS, NODE, build_risks
from rfp_agent.agents.solution import build_solution
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.quality import run_quality_pass
from rfp_agent.render import assemble, render_markdown
from rfp_agent.splitting import split_document

pytestmark = pytest.mark.llm

SETTINGS = Settings()


@pytest.mark.skipif(
    SETTINGS.generator[0] != "deepseek" or not SETTINGS.deepseek_api_key,
    reason="needs the DeepSeek generator and DEEPSEEK_API_KEY",
)
def test_missouri_risks(tmp_path):
    pdf = DATA_DIR / "rfps" / "missouri.pdf"
    rec = RunRecorder("missouri.pdf", SETTINGS.model, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        parsed, _ = run_quality_pass(parse_pdf(pdf), settings=SETTINGS)
        split = split_document(parsed)
        reqs, _ = extract_requirements(split, title=parsed.title, settings=SETTINGS)
        problem = build_problem_statement(split, title=parsed.title, settings=SETTINGS).statement
        solution = build_solution(reqs, problem, title=parsed.title, settings=SETTINGS).solution
        result = build_risks(
            reqs,
            problem,
            solution,
            title=parsed.title,
            referenced_documents=parsed.referenced_documents,
            flags=parsed.flags,
            settings=SETTINGS,
        )

    risks = result.assessment.risks
    known_reqs = set(reqs.requirement_ids())
    known_chunks = set(split.chunk_ids())
    assert MIN_RISKS <= len(risks) <= MAX_RISKS
    assert [k.id for k in risks] == [f"K{i:02d}" for i in range(1, len(risks) + 1)]
    cited: set[str] = set()
    for k in risks:
        print(f"\n{k.id}. {k.title} [{k.severity.value}/{k.likelihood.value}, {k.source.value}]")
        assert set(k.requirement_ids) <= known_reqs
        assert set(k.chunk_ids) <= known_chunks
        cited |= set(k.requirement_ids)
    assert set(result.findings.uncovered_requirement_ids) <= cited

    summary = assemble(
        run_id=rec.run_id,
        model=SETTINGS.model,
        parsed=parsed,
        split=split,
        requirements=reqs,
        problem_statement=problem,
        solution=solution,
        risks=result.assessment,
    )
    md = render_markdown(summary)
    assert "## Risks" in md and "| K01 |" in md
    assert NODE in rec.per_node()
    print(f"\nrisks {len(risks)}, cost ${rec.totals().cost_usd:.4f}")
