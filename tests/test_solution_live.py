"""Live solution generation on Missouri. Paid: run with ``pytest -m llm``.

Runs the requirements extractor and the problem statement first (about 6 cents on
DeepSeek Flash), then the generator with its revision loop. Checks the contract, not the
wording: every component cites existing requirements, every claim cites an existing
chunk, coverage is computed from the components, and the output assembles and renders.
"""

import pytest

from rfp_agent.agents.problem import build_problem_statement
from rfp_agent.agents.requirements import extract_requirements
from rfp_agent.agents.solution import build_solution, compute_coverage
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.render import assemble, render_markdown
from rfp_agent.schemas import RiskAssessment
from rfp_agent.splitting import split_document

pytestmark = pytest.mark.llm

SETTINGS = Settings()


@pytest.mark.skipif(
    SETTINGS.generator[0] != "deepseek" or not SETTINGS.deepseek_api_key,
    reason="needs the DeepSeek generator and DEEPSEEK_API_KEY",
)
def test_missouri_solution(tmp_path):
    pdf = DATA_DIR / "rfps" / "missouri.pdf"
    parsed = parse_pdf(pdf)
    split = split_document(parsed)
    rec = RunRecorder("missouri.pdf", SETTINGS.model, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        reqs, _ = extract_requirements(split, title=parsed.title, settings=SETTINGS)
        problem = build_problem_statement(split, title=parsed.title, settings=SETTINGS).statement
        result = build_solution(reqs, problem, title=parsed.title, settings=SETTINGS)

    sol = result.solution
    known_reqs = set(reqs.requirement_ids())
    known_chunks = set(split.chunk_ids())
    assert 3 <= len(sol.components) <= 12
    for comp in sol.components:
        print(f"\n{comp.id}. {comp.title} ({', '.join(comp.requirement_ids)})")
        assert comp.requirement_ids and set(comp.requirement_ids) <= known_reqs
        for claim in comp.claims:
            assert set(claim.chunk_ids) <= known_chunks
    for claim in sol.assumptions:
        assert set(claim.chunk_ids) <= known_chunks
    assert sol.coverage == compute_coverage(sol.components, reqs.requirements)
    assert sol.coverage.mandatory_covered >= sol.coverage.mandatory_total * 0.8
    assert 1 <= result.iterations <= SETTINGS.solution_max_iterations

    summary = assemble(
        run_id=rec.run_id,
        model=SETTINGS.model,
        parsed=parsed,
        split=split,
        requirements=reqs,
        problem_statement=problem,
        solution=sol,
        risks=RiskAssessment(),
    )
    assert "## Proposed solution" in render_markdown(summary)
    per_node = rec.per_node()
    assert "solution_generate" in per_node
    print(
        f"\nrounds {result.iterations}, coverage {sol.coverage.mandatory_covered}/"
        f"{sol.coverage.mandatory_total}, cost ${rec.totals().cost_usd:.4f}"
    )
