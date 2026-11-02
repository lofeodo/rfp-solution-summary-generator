"""Risk assessor (S8) with a scripted fake model. No network."""

from __future__ import annotations

import re

import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.agents.risk import (
    MAX_RISKS,
    MIN_RISKS,
    NODE,
    SUBMISSION_HEADING,
    RiskResult,
    allowed_chunk_ids,
    build_risks,
    detect_findings,
    format_findings,
    render_prompt,
    risk_schema,
    to_assessment,
)
from rfp_agent.config import Settings
from rfp_agent.llm import StructuredOutputError, load_prompt
from rfp_agent.observability import RunRecorder
from rfp_agent.render import assemble, dangling_citations, render_markdown
from rfp_agent.schemas import (
    Ambiguity,
    Chunk,
    Claim,
    ClaimKind,
    Coverage,
    FlagReason,
    Gap,
    Page,
    PageFlag,
    ParsedDocument,
    ProblemStatement,
    ReferencedDocument,
    ReferenceKind,
    Requirement,
    RequirementsOutput,
    RequirementType,
    RiskAssessmentDraft,
    Section,
    SectionKind,
    Solution,
    SolutionComponent,
    SplitDocument,
    Strictness,
)

SETTINGS = Settings(_env_file=None, max_structured_retries=1)
TITLE = "Example RFP"


def req(
    rid: str,
    text: str,
    chunk: str,
    strictness: Strictness = Strictness.MANDATORY,
    type_: RequirementType = RequirementType.FUNCTIONAL,
    conflicts: tuple[str, ...] = (),
) -> Requirement:
    return Requirement(
        id=rid,
        text=text,
        type=type_,
        strictness=strictness,
        quote=text,
        chunk_ids=[chunk],
        conflicts_with=list(conflicts),
    )


REQS = RequirementsOutput(
    requirements=[
        req("R001", "Provide a hosted portal.", "S2.1"),
        req(
            "R002",
            "Migrate legacy records.",
            "S2.2",
            type_=RequirementType.TECHNICAL,
            conflicts=("R003",),
        ),
        req(
            "R003",
            "Meet WCAG 2.1 AA.",
            "S3.1",
            type_=RequirementType.SECURITY_COMPLIANCE,
            conflicts=("R002",),
        ),
        req("R004", "Offer mobile access.", "S2.1", Strictness.DESIRED),
        req("R005", "Submit five printed copies.", "S4.1", type_=RequirementType.SUBMISSION),
        req("R006", "Budget not to exceed $5.", "S1.2", type_=RequirementType.BUDGET_PRICING),
        req("R007", "Go live by June 2026.", "S1.2", type_=RequirementType.TIMELINE),
    ],
    ambiguities=[
        Ambiguity(
            id="A01", description="Volume unknown.", chunk_ids=["S2.2"], requirement_ids=["R002"]
        )
    ],
    gaps=[
        Gap(
            id="G01",
            description="Attachment F missing.",
            chunk_ids=["S5.1"],
            referenced_document="Attachment F",
        )
    ],
)
PROBLEM = ProblemStatement(
    client_situation=[Claim(text="The county runs a paper process.", chunk_ids=["S1.1"])],
    goal=[Claim(text="Replace it with a portal.", chunk_ids=["S2.1"])],
    success_criteria=[
        Claim(text="Go-live by June 2026.", chunk_ids=["S1.2"], kind=ClaimKind.INFERENCE)
    ],
    constraints=[Claim(text="Budget $5.", chunk_ids=["S1.2"])],
)
SOLUTION = Solution(
    summary="An approach.",
    components=[
        SolutionComponent(
            id="C01",
            title="Portal",
            description="Delivers the portal.",
            requirement_ids=["R001", "R004", "R006", "R007"],
            claims=[Claim(text="Paper today.", chunk_ids=["S1.1"])],
        ),
        SolutionComponent(
            id="C02",
            title="Migration",
            description="Moves the records.",
            requirement_ids=["R002"],
            claims=[Claim(text="The legacy database is Oracle.", chunk_ids=["S6.1"])],
        ),
    ],
    assumptions=[Claim(text="Volume is small.", kind=ClaimKind.INFERENCE, chunk_ids=["S7.1"])],
    coverage=Coverage(mandatory_total=5, mandatory_covered=4, uncovered_requirement_ids=["R003"]),
)
DOCS = [
    ReferencedDocument(name="Attachment F", kind=ReferenceKind.ATTACHMENT, page=12, section="3.1"),
    ReferencedDocument(name="Attachment A", kind=ReferenceKind.ATTACHMENT, page=2, present=True),
    ReferencedDocument(
        name="https://example.org/forms",
        kind=ReferenceKind.HYPERLINK,
        url="https://example.org/forms",
        page=3,
    ),
]
FLAGS = [PageFlag(page=19, reason=FlagReason.LOW_WORD_COUNT, detail="12 words")]
FINDINGS = detect_findings(REQS, SOLUTION, referenced_documents=DOCS, flags=FLAGS)


def risk(
    title: str,
    severity: str = "medium",
    likelihood: str = "medium",
    *,
    reqs: list[str] | None = None,
    chunks: list[str] | None = None,
    source: str = "rfp",
    mitigation: str | None = "Ask the client.",
) -> dict:
    return {
        "title": title,
        "description": f"{title} could happen.",
        "severity": severity,
        "likelihood": likelihood,
        "justification": "Because.",
        "source": source,
        "requirement_ids": reqs or [],
        "chunk_ids": chunks or [],
        "mitigation": mitigation,
    }


def reply(*risks: dict):
    return tool_call_msg("RiskAssessmentDraft", {"risks": list(risks)})


WCAG = risk("WCAG remediation", "high", "high", reqs=["R003"], source="solution")
BUDGET = risk("Budget cap", "high", "medium", reqs=["R006"], chunks=["S1.2"])
ATTACHMENT = risk("Attachment F not available", "medium", "high")
TIMELINE = risk("Go-live date", "low", "high", reqs=["R007"], chunks=["S1.2"])
GOOD = reply(WCAG, BUDGET, ATTACHMENT, TIMELINE)


def recorder(tmp_path) -> RunRecorder:
    return RunRecorder("example.pdf", "fake:scripted", 0.0, runs_dir=tmp_path / "runs")


def build(model, **kwargs) -> RiskResult:
    return build_risks(
        REQS,
        PROBLEM,
        SOLUTION,
        title=TITLE,
        referenced_documents=DOCS,
        flags=FLAGS,
        model=model,
        settings=SETTINGS,
        **kwargs,
    )


# --------------------------------------------------------------------------------------
# Findings and prompt
# --------------------------------------------------------------------------------------


def test_prompt_placeholders():
    assert load_prompt("risk").variables == {
        "title",
        "findings",
        "solution",
        "problem",
        "requirements",
        "ambiguities",
        "gaps",
    }


def test_findings_detected_from_inputs():
    assert FINDINGS.uncovered_requirement_ids == ["R003"]
    assert FINDINGS.conflicts == [["R002", "R003"]]
    assert [d.name for d in FINDINGS.absent_documents] == ["Attachment F"]
    assert FINDINGS.flags == FLAGS
    assert FINDINGS.budget_requirement_count == 1


def test_findings_placeholders_when_nothing_detected():
    reqs = RequirementsOutput(requirements=[req("R001", "Portal.", "S2.1")])
    sol = SOLUTION.model_copy(update={"coverage": Coverage(mandatory_total=1, mandatory_covered=1)})
    text = format_findings(detect_findings(reqs, sol), reqs.requirements)
    assert text.count("(none)") == 4
    assert "no budget or pricing requirement was extracted" in text


def test_prompt_content():
    text = render_prompt(REQS, PROBLEM, SOLUTION, FINDINGS, title=TITLE)
    assert f"Title: {TITLE}" in text
    assert text.index("## Rules") < text.index("<findings>")
    assert "R003 Meet WCAG 2.1 AA." in text
    assert "R002 <-> R003: R002 Migrate legacy records. | R003 Meet WCAG 2.1 AA." in text
    assert "Attachment F (attachment, p. 12, 3.1)" in text
    assert "Attachment A" not in text and "example.org" not in text
    assert "p. 19: low_word_count (12 words)" in text
    assert "1 budget or pricing requirement(s) extracted" in text
    assert "C01 Portal (R001, R004, R006, R007)" in text
    assert "- The legacy database is Oracle. [S6.1]" in text
    assert "- Volume is small. [S7.1] (inference)" in text
    assert "addressed by at least one component: 4 of 5. Not addressed: R003." in text
    assert f"### {SUBMISSION_HEADING}" in text and "do not address" not in text
    assert "R005 [mandatory, submission] Submit five printed copies. (S4.1)" in text
    assert "A01 (S2.2; R002) Volume unknown." in text
    assert "G01 [Attachment F] Attachment F missing. (S5.1)" in text
    assert "handled in normal delivery" in text and "needs an unusual event" in text


def test_allowed_chunk_ids_include_the_solution():
    ids = allowed_chunk_ids(REQS, PROBLEM, SOLUTION)
    assert ids == ["S1.1", "S2.1", "S1.2", "S2.2", "S3.1", "S4.1", "S5.1", "S6.1", "S7.1"]


# --------------------------------------------------------------------------------------
# Per-call schema
# --------------------------------------------------------------------------------------


def schema():
    return risk_schema(REQS.requirement_ids(), allowed_chunk_ids(REQS, PROBLEM, SOLUTION), ["R003"])


def test_schema_name_and_acceptance():
    s = schema()
    assert s.__name__ == "RiskAssessmentDraft"
    draft = s.model_validate({"risks": [WCAG, BUDGET, ATTACHMENT, TIMELINE]})
    assert isinstance(draft, RiskAssessmentDraft) and len(draft.risks) == 4


@pytest.mark.parametrize(
    ("risks", "expected"),
    [
        ([WCAG, BUDGET], f"risks has 2 entries; return at least {MIN_RISKS}"),
        ([WCAG] + [BUDGET] * MAX_RISKS, f"risks has {MAX_RISKS + 1} entries; return at most"),
        (
            [risk("X", reqs=["R003", "R999"]), BUDGET, ATTACHMENT],
            "risks[0] ('X').requirement_ids cites IDs that are not in the requirement list: "
            "['R999']",
        ),
        (
            [WCAG, risk("Y", chunks=["A01", "S9.9"]), ATTACHMENT],
            "risks[1] ('Y').chunk_ids cites chunk IDs that are not shown in the inputs: "
            "['A01', 'S9.9']",
        ),
        (
            [BUDGET, ATTACHMENT, TIMELINE],
            "no risk cites them: ['R003']; add a risk for each",
        ),
    ],
    ids=["too_few", "too_many", "unknown_requirement", "unknown_chunk", "must_cite_missing"],
)
def test_schema_rejects(risks, expected):
    with pytest.raises(ValueError, match=re.escape(expected)):
        schema().model_validate({"risks": risks})


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------


def test_sort_then_number_is_stable_and_folds_ids():
    draft = RiskAssessmentDraft.model_validate(
        {
            "risks": [
                risk("D", "low", "low", mitigation="   "),
                risk("B", "high", "medium", reqs=["R001", "R001", "R002"]),
                risk("A", "high", "high"),
                risk("C", "high", "medium"),
                risk("E", "medium", "high", mitigation=None),
            ]
        }
    )
    out = to_assessment(draft)
    assert [(k.id, k.title) for k in out.risks] == [
        ("K01", "A"),
        ("K02", "B"),
        ("K03", "C"),
        ("K04", "E"),
        ("K05", "D"),
    ]
    assert out.risks[1].requirement_ids == ["R001", "R002"]
    assert out.risks[4].mitigation is None and out.risks[3].mitigation is None
    assert out.risks[0].mitigation == "Ask the client."


# --------------------------------------------------------------------------------------
# The call
# --------------------------------------------------------------------------------------


def test_one_call_records_node_and_prompt_hash(tmp_path):
    model = ScriptedChatModel(responses=[GOOD])
    rec = recorder(tmp_path)
    with rec.activate(write=False):
        result = build(model)
    assert type(result) is RiskResult
    assert len(model.calls) == 1
    first = model.calls[0]
    assert len(first) == 1 and isinstance(first[0], HumanMessage) and TITLE in first[0].content
    assert [k.id for k in result.assessment.risks] == ["K01", "K02", "K03", "K04"]
    assert result.assessment.risks[0].title == "WCAG remediation"
    assert result.assessment.risks[3].title == "Go-live date"
    assert result.findings == FINDINGS
    assert [n.node for n in rec.log.nodes] == [NODE]
    assert rec.log.nodes[0].retries == 0
    assert set(rec.log.prompt_hashes) == {"risk"}


def test_missing_must_cite_is_fed_back_then_accepted(tmp_path):
    model = ScriptedChatModel(responses=[reply(BUDGET, ATTACHMENT, TIMELINE), GOOD])
    rec = recorder(tmp_path)
    result = build(model, recorder=rec)
    assert len(model.calls) == 2 and len(result.assessment.risks) == 4
    assert rec.log.nodes[-1].retries == 1
    feedback = model.calls[1][-1]
    assert isinstance(feedback, ToolMessage)
    assert "R003" in feedback.content and "no risk cites them" in feedback.content


def test_exhaustion_raises(tmp_path):
    bad = reply(BUDGET, ATTACHMENT)
    model = ScriptedChatModel(responses=[bad, bad])
    with pytest.raises(StructuredOutputError) as info:
        build(model, recorder=recorder(tmp_path))
    assert info.value.node == NODE and len(model.calls) == 2


def test_uncovered_id_outside_the_requirement_list_is_not_enforced(tmp_path, caplog):
    sol = SOLUTION.model_copy(
        update={
            "coverage": Coverage(
                mandatory_total=5, mandatory_covered=4, uncovered_requirement_ids=["R999"]
            )
        }
    )
    model = ScriptedChatModel(responses=[reply(BUDGET, ATTACHMENT, TIMELINE)])
    with caplog.at_level("WARNING", logger="rfp_agent.agents.risk"):
        result = build_risks(
            REQS,
            PROBLEM,
            sol,
            title=TITLE,
            model=model,
            settings=SETTINGS,
            recorder=recorder(tmp_path),
        )
    assert len(result.assessment.risks) == 3
    assert "R999" in caplog.text


def test_json_round_trip(tmp_path):
    result = build(ScriptedChatModel(responses=[GOOD]), recorder=recorder(tmp_path))
    assert RiskResult.model_validate_json(result.model_dump_json()) == result


# --------------------------------------------------------------------------------------
# Downstream: assembles and renders through S9
# --------------------------------------------------------------------------------------


def _split() -> SplitDocument:
    def chunk(cid: str, sid: str) -> Chunk:
        return Chunk(id=cid, section_id=sid, section_path=["x"], page_start=1, page_end=1, text="t")

    def section(sid: str, chunks: list[str]) -> Section:
        return Section(
            id=sid,
            title=f"Section {sid}",
            level=1,
            path=["x"],
            page_start=1,
            page_end=1,
            kind=SectionKind.NARRATIVE,
            chunks=[chunk(c, sid) for c in chunks],
        )

    return SplitDocument(
        sections=[
            section("S1", ["S1.1", "S1.2"]),
            section("S2", ["S2.1", "S2.2"]),
            section("S3", ["S3.1"]),
            section("S4", ["S4.1"]),
            section("S5", ["S5.1"]),
            section("S6", ["S6.1"]),
            section("S7", ["S7.1"]),
        ]
    )


def test_output_assembles_without_dangling_citations_and_renders(tmp_path):
    result = build(ScriptedChatModel(responses=[GOOD]), recorder=recorder(tmp_path))
    parsed = ParsedDocument(
        source_path="x.pdf",
        title=TITLE,
        pages=[Page(number=1, markdown="t", word_count=1)],
        referenced_documents=DOCS,
        flags=FLAGS,
    )
    summary = assemble(
        run_id="r1",
        model="fake:scripted",
        parsed=parsed,
        split=_split(),
        requirements=REQS,
        problem_statement=PROBLEM,
        solution=SOLUTION,
        risks=result.assessment,
    )
    assert dangling_citations(summary) == []
    md = render_markdown(summary)
    assert "| K01 | WCAG remediation | high | high | Solution |" in md
    assert md.index("### K01.") < md.index("### K02.") < md.index("### K04.")
    assert "**Mitigation:** Ask the client." in md
    assert "**Related requirements:** R003." in md
