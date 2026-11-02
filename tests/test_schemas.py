"""Schema round-trip and validation tests. No LLM calls."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from rfp_agent.schemas import (
    Ambiguity,
    Chunk,
    ChunkRef,
    Claim,
    ClaimKind,
    Coverage,
    Escalation,
    EscalationTrigger,
    FlagReason,
    Gap,
    Likelihood,
    NodeMetrics,
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
    RunLog,
    Section,
    SectionKind,
    Severity,
    Solution,
    SolutionComponent,
    SolutionSummary,
    SplitDocument,
    Strictness,
    validate_ids_exist,
)

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def make_summary() -> SolutionSummary:
    req = Requirement(
        id="R001",
        text="The system must produce legal land descriptions.",
        type=RequirementType.FUNCTIONAL,
        strictness=Strictness.MANDATORY,
        quote="shall produce legal land descriptions",
        chunk_ids=["S3.2"],
        quote_verified=True,
        merged_from=["R004"],
    )
    return SolutionSummary(
        run_id="run-0001",
        source_path="inputs/rfp_brief.pdf",
        document_title="TR202504",
        generated_at=NOW,
        model="deepseek:deepseek-flash",
        chunks=[ChunkRef(id="S3.2", section_title="Scope of Work", page_start=4, page_end=4)],
        requirements=RequirementsOutput(
            requirements=[req],
            ambiguities=[Ambiguity(id="A01", description="Format unspecified", chunk_ids=["S3.2"])],
            gaps=[Gap(id="G01", description="Attachment F absent", referenced_document="F")],
        ),
        problem_statement=ProblemStatement(
            goal=[Claim(text="Automate land descriptions", chunk_ids=["S3.2"])],
            constraints=[
                Claim(
                    text="Budget is tight",
                    kind=ClaimKind.INFERENCE,
                    chunk_ids=["S3.2", "S5.1"],
                )
            ],
        ),
        solution=Solution(
            summary="An LLM pipeline with human review.",
            components=[
                SolutionComponent(
                    id="C01",
                    title="Extractor",
                    description="Reads deeds.",
                    requirement_ids=["R001"],
                )
            ],
            coverage=Coverage(mandatory_total=1, mandatory_covered=1),
        ),
        risks=RiskAssessment(
            risks=[
                Risk(
                    id="K01",
                    title="Short timeline",
                    description="Fifteen months end to end.",
                    severity=Severity.HIGH,
                    likelihood=Likelihood.MEDIUM,
                    justification="Milestone table is dense.",
                    source=RiskSource.RFP,
                    chunk_ids=["S5.1"],
                )
            ]
        ),
        referenced_documents=[
            ReferencedDocument(name="Attachment F", kind=ReferenceKind.ATTACHMENT, page=2)
        ],
        flags=[PageFlag(page=19, reason=FlagReason.LOW_WORD_COUNT)],
    )


def test_solution_summary_round_trip():
    original = make_summary()
    restored = SolutionSummary.model_validate_json(original.model_dump_json())
    assert restored == original
    assert restored.requirements.mandatory()[0].id == "R001"
    assert len(restored.problem_statement.claims()) == 2


def test_enums_serialise_as_strings():
    data = make_summary().model_dump(mode="json")
    assert data["requirements"]["requirements"][0]["type"] == "functional"
    assert data["risks"]["risks"][0]["severity"] == "high"


def test_parsed_and_split_documents_round_trip():
    parsed = ParsedDocument(
        source_path="x.pdf",
        pages=[Page(number=1, markdown="# A\n\ntext", word_count=2)],
    )
    assert parsed.page_count == 1
    assert "text" in parsed.full_markdown
    chunk = Chunk(
        id="S1.1", section_id="S1", section_path=["A"], page_start=1, page_end=1, text="text"
    )
    split = SplitDocument(
        sections=[
            Section(
                id="S1",
                title="A",
                level=1,
                path=["A"],
                page_start=1,
                page_end=1,
                kind=SectionKind.NARRATIVE,
                chunks=[chunk],
            )
        ]
    )
    assert split.chunk_ids() == ["S1.1"]
    assert split.chunk_by_id("S1.1") == chunk
    assert split.chunk_by_id("S9.9") is None
    assert SplitDocument.model_validate_json(split.model_dump_json()) == split


@pytest.mark.parametrize(
    ("model", "field", "bad"),
    [
        (Chunk, "id", "3.2"),
        (Chunk, "id", "S3"),
        (Chunk, "section_id", "S3.2"),
        (Requirement, "id", "R1"),
        (Ambiguity, "id", "A1"),
        (Gap, "id", "G1"),
        (SolutionComponent, "id", "C1"),
        (Risk, "id", "K1"),
        (ChunkRef, "id", "S3"),
    ],
)
def test_bad_ids_rejected(model, field, bad):
    with pytest.raises(ValidationError) as exc:
        model.model_validate({field: bad})
    assert any(field in str(e["loc"]) for e in exc.value.errors())


def test_claim_requires_a_citation():
    with pytest.raises(ValidationError):
        Claim(text="unsupported", chunk_ids=[])


def test_requirement_requires_a_citation():
    with pytest.raises(ValidationError):
        Requirement(
            id="R001",
            text="t",
            type=RequirementType.OTHER,
            strictness=Strictness.OPTIONAL,
            quote="q",
            chunk_ids=[],
        )


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        Claim(text="x", chunk_ids=["S1.1"], confidence=0.9)


def test_validate_ids_exist():
    assert validate_ids_exist(["S1.1", "S2.9", "S1.1", "S3.1"], ["S1.1", "S3.1"]) == ["S2.9"]
    assert validate_ids_exist([], []) == []


def test_run_log_totals_and_round_trip():
    log = RunLog(
        run_id="run-0001",
        source_path="inputs/rfp_brief.pdf",
        started_at=NOW,
        model="deepseek:deepseek-flash",
        temperature=0.0,
        prompt_hashes={"requirements_extract.md": "abc"},
        nodes=[
            NodeMetrics(
                node="requirements",
                model="deepseek-flash",
                input_tokens=1000,
                output_tokens=200,
                cost_usd=0.001,
                latency_s=2.5,
                retries=1,
                started_at=NOW,
            ),
            NodeMetrics(
                node="problem",
                model="deepseek-flash",
                input_tokens=500,
                output_tokens=100,
                cached_input_tokens=400,
                cost_usd=0.0005,
                latency_s=1.5,
                started_at=NOW,
            ),
        ],
        escalations=[
            Escalation(
                page=19,
                triggered_by=EscalationTrigger.CODE,
                confirmed_bad=True,
                action="would escalate to VLM",
            )
        ],
    )
    totals = log.totals()
    assert totals.input_tokens == 1500
    assert totals.output_tokens == 300
    assert totals.cached_input_tokens == 400
    assert totals.cost_usd == pytest.approx(0.0015)
    assert totals.latency_s == pytest.approx(4.0)
    assert totals.retries == 1
    assert RunLog.model_validate_json(log.model_dump_json()) == log
