"""Solution generator (S7) with a scripted fake model. No network."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.agents.solution import (
    GENERATE_NODE,
    REVISE_NODE,
    SUBMISSION_HEADING,
    SolutionResult,
    allowed_chunk_ids,
    build_solution,
    compute_coverage,
    coverage_feedback,
    format_requirements,
    in_scope,
    render_prompt,
    solution_schema,
    to_solution,
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
    ComponentDraft,
    Gap,
    Page,
    ParsedDocument,
    ProblemStatement,
    Requirement,
    RequirementsOutput,
    RequirementType,
    RiskAssessment,
    Section,
    SectionKind,
    Solution,
    SolutionDraft,
    SplitDocument,
    Strictness,
)

SETTINGS = Settings(_env_file=None, max_structured_retries=1, solution_max_iterations=3)
TITLE = "Example RFP"


def req(
    rid: str,
    text: str,
    chunk: str,
    strictness: Strictness = Strictness.MANDATORY,
    type_: RequirementType = RequirementType.FUNCTIONAL,
) -> Requirement:
    return Requirement(
        id=rid, text=text, type=type_, strictness=strictness, quote=text, chunk_ids=[chunk]
    )


REQS = RequirementsOutput(
    requirements=[
        req("R001", "Provide a hosted portal.", "S2.1"),
        req("R002", "Migrate legacy records.", "S2.2", type_=RequirementType.TECHNICAL),
        req("R003", "Meet WCAG 2.1 AA.", "S3.1", type_=RequirementType.SECURITY_COMPLIANCE),
        req("R004", "Offer mobile access.", "S2.1", Strictness.DESIRED),
        req("R005", "Submit five printed copies.", "S4.1", type_=RequirementType.SUBMISSION),
        req("R006", "Provide dashboards.", "S2.2", Strictness.OPTIONAL),
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
IN_SCOPE = ["R001", "R002", "R003"]


def component(title: str, *rids: str, claims: list[dict] | None = None) -> dict:
    return {
        "title": title,
        "description": f"Delivers {title.lower()}.",
        "requirement_ids": list(rids),
        "claims": claims or [],
    }


def reply(*components: dict, assumptions: list[dict] | None = None) -> AIMessage:
    return tool_call_msg(
        "SolutionDraft",
        {
            "summary": "An approach.",
            "components": list(components),
            "assumptions": assumptions or [],
        },
    )


FULL = reply(
    component("Portal", "R001", "R004"),
    component("Migration", "R002"),
    component("Compliance", "R003"),
)
PARTIAL = reply(component("Portal", "R001"), component("Migration", "R002"))


def recorder(tmp_path) -> RunRecorder:
    return RunRecorder("example.pdf", "fake:scripted", 0.0, runs_dir=tmp_path / "runs")


def build(model: ScriptedChatModel, **kwargs) -> SolutionResult:
    return build_solution(REQS, PROBLEM, title=TITLE, model=model, settings=SETTINGS, **kwargs)


# --------------------------------------------------------------------------------------
# Prompt and evidence
# --------------------------------------------------------------------------------------


def test_prompt_placeholders():
    assert load_prompt("solution").variables == {
        "title",
        "problem",
        "requirements",
        "ambiguities",
        "gaps",
    }


def test_prompt_content_labels_every_input():
    text = render_prompt(REQS, PROBLEM, title=TITLE)
    assert TITLE in text
    assert "- The county runs a paper process. [S1.1]" in text
    assert "- Go-live by June 2026. [S1.2] (inference)" in text
    assert "R001 [mandatory, functional] Provide a hosted portal. (S2.1)" in text
    assert "R004 [desired, functional] Offer mobile access. (S2.1)" in text
    assert "A01 (S2.2; R002) Volume unknown." in text
    assert "G01 [Attachment F] Attachment F missing. (S5.1)" in text


def test_submission_items_sit_in_the_context_block():
    text = format_requirements(REQS.requirements)
    blocks = text.split("### ")
    submission = next(b for b in blocks if b.startswith(SUBMISSION_HEADING))
    mandatory = next(b for b in blocks if b.startswith("Mandatory"))
    assert "R005" in submission and "R005" not in mandatory
    assert "R001" in mandatory and "R002" in mandatory and "R003" in mandatory
    assert blocks[-1].startswith(SUBMISSION_HEADING)


def test_allowed_chunk_ids_is_the_union_of_every_label():
    assert allowed_chunk_ids(REQS, PROBLEM) == [
        "S1.1",
        "S2.1",
        "S1.2",
        "S2.2",
        "S3.1",
        "S4.1",
        "S5.1",
    ]


# --------------------------------------------------------------------------------------
# Coverage (pure)
# --------------------------------------------------------------------------------------


def test_in_scope_excludes_submission_and_non_mandatory():
    assert [r.id for r in in_scope(REQS.requirements)] == IN_SCOPE


def test_compute_coverage_counts_only_in_scope_and_keeps_order():
    comps = [
        ComponentDraft(title="t", description="d", requirement_ids=["R003", "R004", "R005", "R006"])
    ]
    cov = compute_coverage(comps, REQS.requirements)
    assert (cov.mandatory_total, cov.mandatory_covered) == (3, 1)
    assert cov.uncovered_requirement_ids == ["R001", "R002"]


def test_compute_coverage_with_no_mandatory_requirements():
    cov = compute_coverage([], [req("R001", "x", "S1.1", Strictness.DESIRED)])
    assert cov.mandatory_total == 0 and cov.uncovered_requirement_ids == []


def test_coverage_feedback_names_each_requirement():
    text = coverage_feedback([REQS.requirements[2]])
    assert "- R003: Meet WCAG 2.1 AA." in text and "1 mandatory" in text


# --------------------------------------------------------------------------------------
# Per-call schema
# --------------------------------------------------------------------------------------


def test_schema_is_named_like_the_contract_and_accepts_known_ids():
    schema = solution_schema(REQS.requirement_ids(), ["S1.1"])
    assert schema.__name__ == "SolutionDraft"
    draft = schema(
        summary="s",
        components=[ComponentDraft(title="t", description="d", requirement_ids=["R001"])],
    )
    assert draft.components[0].requirement_ids == ["R001"]


@pytest.mark.parametrize(
    ("components", "assumptions", "expected"),
    [
        ([], [], "components is empty"),
        ([component("t")], [], "components[0] ('t') cites no requirement"),
        (
            [component("t", "R999")],
            [],
            "components[0].requirement_ids cites IDs that are not in the requirement list: "
            "['R999']",
        ),
        (
            [component("t", "R001", claims=[{"text": "x", "chunk_ids": ["S9.9"]}])],
            [],
            "components[0].claims cites chunk IDs that are not shown in the inputs: ['S9.9']",
        ),
        (
            [component("t", "R001")],
            [{"text": "x", "chunk_ids": ["S9.9"]}],
            "assumptions cites chunk IDs that are not shown in the inputs: ['S9.9']",
        ),
    ],
)
def test_schema_rejects_bad_citations(components, assumptions, expected):
    schema = solution_schema(REQS.requirement_ids(), ["S1.1"])
    with pytest.raises(ValueError, match=__import__("re").escape(expected)):
        schema.model_validate(
            {"summary": "s", "components": components, "assumptions": assumptions}
        )


def test_unknown_requirement_id_is_fed_back_then_accepted(tmp_path):
    bad = reply(component("Portal", "R001", "R999"), component("Rest", "R002", "R003"))
    model = ScriptedChatModel(responses=[bad, FULL])
    rec = recorder(tmp_path)
    result = build(model, recorder=rec)
    assert result.solution.coverage.uncovered_requirement_ids == []
    assert rec.log.nodes[-1].retries == 1
    feedback = model.calls[1][-1]
    assert isinstance(feedback, ToolMessage)
    assert "R999" in feedback.content and "not in the requirement list" in feedback.content


def test_retry_exhaustion_raises():
    bad = reply(component("Portal", "R999"))
    model = ScriptedChatModel(responses=[bad, bad])
    with pytest.raises(StructuredOutputError, match="R999"):
        build(model)


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------


def test_components_numbered_in_reply_order_and_duplicates_folded():
    draft = SolutionDraft(
        summary=" s ",
        components=[
            ComponentDraft(title=" A ", description="d", requirement_ids=["R001", "R001", "R002"]),
            ComponentDraft(title="B", description="d", requirement_ids=["R003"]),
        ],
    )
    sol = to_solution(draft, compute_coverage(draft.components, REQS.requirements))
    assert [c.id for c in sol.components] == ["C01", "C02"]
    assert sol.components[0].title == "A" and sol.summary == "s"
    assert sol.components[0].requirement_ids == ["R001", "R002"]
    assert sol.coverage.mandatory_covered == 3


# --------------------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------------------


def test_full_coverage_in_round_one_makes_one_call(tmp_path):
    model = ScriptedChatModel(responses=[FULL])
    rec = recorder(tmp_path)
    with rec.activate(write=False):
        result = build(model)
    assert type(result.solution) is Solution
    assert len(model.calls) == 1 and result.iterations == 1
    assert result.solution.coverage.model_dump() == {
        "mandatory_total": 3,
        "mandatory_covered": 3,
        "uncovered_requirement_ids": [],
    }
    assert [c.id for c in result.solution.components] == ["C01", "C02", "C03"]
    assert [n.node for n in rec.log.nodes] == [GENERATE_NODE]
    assert set(rec.log.prompt_hashes) == {"solution"}
    assert isinstance(model.calls[0][0], HumanMessage) and TITLE in model.calls[0][0].content


def test_uncovered_requirement_triggers_a_revision_in_the_same_conversation(tmp_path):
    model = ScriptedChatModel(responses=[PARTIAL, FULL])
    rec = recorder(tmp_path)
    result = build(model, recorder=rec)
    assert len(model.calls) == 2 and result.iterations == 2
    assert [r.coverage.uncovered_requirement_ids for r in result.rounds] == [["R003"], []]
    assert result.solution.coverage.uncovered_requirement_ids == []
    assert [n.node for n in rec.log.nodes] == [GENERATE_NODE, REVISE_NODE]
    history = model.calls[1]
    assert [type(m) for m in history] == [HumanMessage, AIMessage, HumanMessage]
    assert "R003: Meet WCAG 2.1 AA." in history[-1].content
    assert '"Portal"' in history[1].content  # the model sees its own previous answer


def test_worse_revision_is_discarded_and_best_kept():
    worse = reply(component("Portal", "R001"))
    model = ScriptedChatModel(responses=[PARTIAL, worse, worse])
    result = build(model)
    assert len(model.calls) == 3 and result.iterations == 3
    assert [len(r.coverage.uncovered_requirement_ids) for r in result.rounds] == [1, 2, 2]
    assert result.solution.coverage.uncovered_requirement_ids == ["R003"]
    assert [c.title for c in result.solution.components] == ["Portal", "Migration"]


def test_cap_from_settings_and_from_argument():
    model = ScriptedChatModel(responses=[PARTIAL, PARTIAL, PARTIAL])
    result = build(model)
    assert len(model.calls) == 3 and result.solution.coverage.uncovered_requirement_ids == ["R003"]

    model = ScriptedChatModel(responses=[PARTIAL])
    result = build(model, max_iterations=1)
    assert len(model.calls) == 1 and result.iterations == 1

    settings = Settings(_env_file=None, solution_max_iterations=2)
    model = ScriptedChatModel(responses=[PARTIAL, PARTIAL])
    result = build_solution(REQS, PROBLEM, title=TITLE, model=model, settings=settings)
    assert len(model.calls) == 2


def test_result_round_trips_as_json():
    result = build(ScriptedChatModel(responses=[FULL]))
    again = SolutionResult.model_validate_json(result.model_dump_json())
    assert again == result


# --------------------------------------------------------------------------------------
# Downstream: the output assembles and renders (S9)
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
        ]
    )


def test_output_assembles_without_dangling_citations_and_renders():
    with_claims = reply(
        component(
            "Portal", "R001", "R004", claims=[{"text": "Paper today.", "chunk_ids": ["S1.1"]}]
        ),
        component("Migration", "R002"),
        assumptions=[{"text": "Volume is small.", "kind": "inference", "chunk_ids": ["S2.2"]}],
    )
    result = build(ScriptedChatModel(responses=[with_claims]), max_iterations=1)
    parsed = ParsedDocument(
        source_path="x.pdf", title=TITLE, pages=[Page(number=1, markdown="t", word_count=1)]
    )
    summary = assemble(
        run_id="r1",
        model="fake:scripted",
        parsed=parsed,
        split=_split(),
        requirements=REQS,
        problem_statement=PROBLEM,
        solution=result.solution,
        risks=RiskAssessment(),
    )
    assert dangling_citations(summary) == []
    md = render_markdown(summary)
    assert "Covers 2 of 3 mandatory requirements. Uncovered: R003." in md
    assert "#### C01. Portal" in md and "Addresses: R001, R004." in md
    assert "Volume is small." in md
