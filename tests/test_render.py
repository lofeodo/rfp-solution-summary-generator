"""S9: assembly, citation checks and markdown rendering. No LLM calls."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rfp_agent.render import (
    CitationError,
    assemble,
    chunk_refs,
    dangling_citations,
    render_markdown,
    write_summary,
)
from rfp_agent.render.markdown import cite, sorted_risks
from rfp_agent.schemas import (
    Chunk,
    ChunkRef,
    Claim,
    Coverage,
    FlagReason,
    Likelihood,
    Page,
    PageFlag,
    ParsedDocument,
    ProblemStatement,
    ReferencedDocument,
    ReferenceKind,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Risk,
    RiskAssessment,
    RiskSource,
    Section,
    SectionKind,
    Severity,
    Solution,
    SolutionSummary,
    SplitDocument,
    Strictness,
)

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_JSON = FIXTURES / "summary_sample.json"
GOLDEN_MD = FIXTURES / "summary_sample.md"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def summary() -> SolutionSummary:
    return SolutionSummary.model_validate_json(FIXTURE_JSON.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# Renderer
# --------------------------------------------------------------------------------------


def test_golden_markdown(summary, request):
    rendered = render_markdown(summary)
    if request.config.getoption("--update-golden"):
        GOLDEN_MD.write_text(rendered, encoding="utf-8", newline="\n")
    assert rendered == GOLDEN_MD.read_text(encoding="utf-8")


def test_render_is_deterministic(summary):
    assert render_markdown(summary) == render_markdown(summary.model_copy(deep=True))


def test_render_sections_in_order(summary):
    md = render_markdown(summary)
    headings = [line for line in md.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Problem statement",
        "## Requirements",
        "## Proposed solution",
        "## Risks",
        "## Referenced documents",
        "## Parse flags",
    ]
    assert md.endswith("\n") and not md.endswith("\n\n")


def test_cite_groups_by_section_and_pages():
    index = {
        "S3.2": ChunkRef(id="S3.2", section_title="Scope", page_start=4, page_end=4),
        "S7.1": ChunkRef(id="S7.1", section_title="IT", page_start=13, page_end=18),
        "S7.3": ChunkRef(id="S7.3", section_title="IT", page_start=13, page_end=18),
    }
    assert cite([], index) == ""
    assert cite(["S3.2"], index) == "(Scope, p. 4 [S3.2])"
    assert cite(["S7.1", "S7.3"], index) == "(IT, pp. 13-18 [S7.1, S7.3])"
    assert cite(["S3.2", "S7.1", "S3.2"], index) == "(Scope, p. 4 [S3.2]; IT, pp. 13-18 [S7.1])"


def test_unknown_chunk_falls_back_to_id():
    index = {"S3.2": ChunkRef(id="S3.2", section_title="Scope", page_start=4, page_end=4)}
    assert cite(["S3.2", "S9.9"], index) == "(Scope, p. 4 [S3.2]; [S9.9])"


def test_sorted_risks_order(summary):
    assert [k.id for k in sorted_risks(summary)] == ["K03", "K02", "K01"]


def test_table_cells_escaped(summary):
    md = render_markdown(summary)
    assert "| K02 | Budget \\| scope mismatch | high | medium | RFP |" in md


def test_empty_summary_renders_none_placeholders():
    empty = SolutionSummary(
        run_id="r",
        source_path="data/rfps/colfax.pdf",
        generated_at=NOW,
        model="m:x",
        requirements=RequirementsOutput(),
        problem_statement=ProblemStatement(),
        solution=Solution(summary="", coverage=Coverage(mandatory_total=0, mandatory_covered=0)),
        risks=RiskAssessment(),
    )
    md = render_markdown(empty)
    assert md.startswith("# Solution summary: colfax.pdf\n")
    assert "0 requirements: 0 mandatory, 0 desired, 0 optional." in md
    assert "No mandatory requirements to cover." in md
    assert md.count("None.") == 12


# --------------------------------------------------------------------------------------
# Assembler
# --------------------------------------------------------------------------------------


def _inputs(risk_chunk: str = "S1.2"):
    parsed = ParsedDocument(
        source_path="data/rfps/x.pdf",
        title="X RFP",
        pages=[Page(number=n, markdown="text", word_count=1) for n in (1, 2, 3)],
        referenced_documents=[
            ReferencedDocument(name="Appendix A", kind=ReferenceKind.APPENDIX, page=2)
        ],
        flags=[PageFlag(page=3, reason=FlagReason.LOW_WORD_COUNT)],
    )

    def chunk(cid: str, sid: str, title: str, p0: int, p1: int) -> Chunk:
        return Chunk(
            id=cid, section_id=sid, section_path=[title], page_start=p0, page_end=p1, text="t"
        )

    split = SplitDocument(
        sections=[
            Section(
                id="S1",
                title="Intro",
                level=1,
                path=["Intro"],
                page_start=1,
                page_end=2,
                kind=SectionKind.NARRATIVE,
                chunks=[chunk("S1.1", "S1", "Intro", 1, 1), chunk("S1.2", "S1", "Intro", 1, 2)],
            ),
            Section(
                id="S2",
                title="Scope",
                level=1,
                path=["Scope"],
                page_start=3,
                page_end=3,
                kind=SectionKind.REQUIREMENT_BEARING,
                chunks=[chunk("S2.1", "S2", "Scope", 3, 3)],
            ),
        ]
    )
    reqs = RequirementsOutput(
        requirements=[
            Requirement(
                id="R001",
                text="Do X.",
                type=RequirementType.FUNCTIONAL,
                strictness=Strictness.MANDATORY,
                quote="shall do X",
                chunk_ids=["S2.1"],
                merged_from=["R007"],  # pre-merge ID, must not count as dangling
            )
        ]
    )
    problem = ProblemStatement(goal=[Claim(text="X", chunk_ids=["S1.1"])])
    solution = Solution(summary="s", coverage=Coverage(mandatory_total=1, mandatory_covered=1))
    risks = RiskAssessment(
        risks=[
            Risk(
                id="K01",
                title="t",
                description="d",
                severity=Severity.LOW,
                likelihood=Likelihood.LOW,
                justification="j",
                source=RiskSource.RFP,
                requirement_ids=["R001"],
                chunk_ids=[risk_chunk],
            )
        ]
    )
    return dict(
        parsed=parsed,
        split=split,
        requirements=reqs,
        problem_statement=problem,
        solution=solution,
        risks=risks,
    )


def test_assemble_builds_chunk_refs_and_copies_metadata():
    inputs = _inputs()
    s = assemble(run_id="r1", model="deepseek:deepseek-flash", generated_at=NOW, **inputs)
    assert [(c.id, c.section_title, c.page_start, c.page_end) for c in s.chunks] == [
        ("S1.1", "Intro", 1, 1),
        ("S1.2", "Intro", 1, 2),
        ("S2.1", "Scope", 3, 3),
    ]
    assert s.chunks == chunk_refs(inputs["split"])
    assert s.source_path == "data/rfps/x.pdf"
    assert s.document_title == "X RFP"
    assert s.referenced_documents[0].name == "Appendix A"
    assert s.flags[0].page == 3
    assert s.generated_at == NOW
    assert dangling_citations(s) == []


def test_assemble_defaults_generated_at_to_now():
    s = assemble(run_id="r1", model="m:x", **_inputs())
    assert s.generated_at.tzinfo is not None


def test_assemble_raises_on_dangling_citation():
    with pytest.raises(CitationError) as exc:
        assemble(run_id="r1", model="m:x", **_inputs(risk_chunk="S9.9"))
    assert exc.value.dangling == [("risks.K01.chunk_ids", "S9.9")]
    assert "risks.K01.chunk_ids -> S9.9" in str(exc.value)


def test_assemble_non_strict_keeps_dangling_citation():
    s = assemble(run_id="r1", model="m:x", strict=False, **_inputs(risk_chunk="S9.9"))
    assert dangling_citations(s) == [("risks.K01.chunk_ids", "S9.9")]
    assert "[S9.9]" in render_markdown(s)


def test_dangling_citations_covers_requirement_ids(summary):
    summary.solution.components[0].requirement_ids.append("R999")
    summary.risks.risks[0].requirement_ids.append("R998")
    summary.problem_statement.goal[0].chunk_ids.append("S8.8")
    assert dangling_citations(summary) == [
        ("problem_statement.goal[0]", "S8.8"),
        ("requirements.R005.chunk_ids", "S9.9"),
        ("solution.C01.requirement_ids", "R999"),
        ("risks.K01.requirement_ids", "R998"),
    ]


# --------------------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------------------


def test_write_summary(summary, tmp_path):
    json_path, md_path = write_summary(summary, tmp_path / "runs" / "r1")
    assert json_path.name == "summary.json" and md_path.name == "summary.md"
    restored = SolutionSummary.model_validate_json(json_path.read_text(encoding="utf-8"))
    assert restored == summary
    assert md_path.read_text(encoding="utf-8") == render_markdown(summary)
