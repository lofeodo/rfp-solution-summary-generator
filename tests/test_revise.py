"""Revise agents (ST12b): contracts, validators, re-keying. Scripted model, no network."""

from __future__ import annotations

import pytest

from fakes import ScriptedChatModel, tool_call_msg
from pipeline_stubs import PDF, fixtures
from rfp_agent.agents.revise import (
    PROMPTS,
    apply_patch,
    rekey_risks,
    requirements_patch_schema,
    revise_problem,
    revise_requirements,
    revise_risks,
    revise_solution,
)
from rfp_agent.brief import parse_brief
from rfp_agent.config import Settings
from rfp_agent.llm import StructuredOutputError, load_prompt
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.schemas import (
    Ambiguity,
    Artefact,
    Requirement,
    RequirementOrigin,
    RequirementsPatch,
    RequirementType,
    RiskAssessmentRevision,
    Strictness,
)
from rfp_agent.splitting import split_document

SETTINGS = Settings(_env_file=None, max_structured_retries=1)


@pytest.fixture(scope="module")
def split():
    return split_document(parse_pdf(PDF))


@pytest.fixture(scope="module")
def chunk(split):
    return split.chunks()[0]


@pytest.fixture
def fx(chunk):
    return fixtures(chunk.id)


def quote_of(chunk) -> str:
    """A verbatim span of the chunk (a few words from its middle)."""
    words = chunk.text.split()
    return " ".join(words[len(words) // 2 : len(words) // 2 + 6])


def recorder(tmp_path) -> RunRecorder:
    return RunRecorder("x.pdf", "scripted", 0.0, run_id="r1", runs_dir=tmp_path)


def three_requirements(fx, chunk):
    reqs = fx["requirements"]
    extra = Requirement(
        id="R003",
        text="Host in the US.",
        type=RequirementType.TECHNICAL,
        strictness=Strictness.MANDATORY,
        quote=quote_of(chunk),
        chunk_ids=[chunk.id],
        conflicts_with=["R001"],
    )
    first = reqs.requirements[0].model_copy(update={"conflicts_with": ["R003"]})
    return reqs.model_copy(
        update={
            "requirements": [first, reqs.requirements[1], extra],
            "ambiguities": [
                Ambiguity(
                    id="A01",
                    description="Which cloud?",
                    chunk_ids=[chunk.id],
                    requirement_ids=["R003"],
                )
            ],
        }
    )


# --------------------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------------------


def test_revise_prompt_placeholders():
    expected = {
        Artefact.REQUIREMENTS: {"title", "instruction", "requirements", "chunks"},
        Artefact.PROBLEM: {"title", "instruction", "problem", "evidence_kind", "evidence", "brief"},
        Artefact.SOLUTION: {
            "title",
            "instruction",
            "solution",
            "problem",
            "requirements",
            "ambiguities",
            "gaps",
            "brief",
        },
        Artefact.RISKS: {
            "title",
            "instruction",
            "risks",
            "findings",
            "solution",
            "problem",
            "requirements",
            "ambiguities",
            "gaps",
            "brief",
        },
    }
    for artefact, names in expected.items():
        assert load_prompt(PROMPTS[artefact]).variables == names


# --------------------------------------------------------------------------------------
# Requirements patch
# --------------------------------------------------------------------------------------


def test_patch_schema_refuses_unknown_duplicate_and_empty_operations(fx, chunk):
    schema = requirements_patch_schema(["R001", "R002"], {chunk.id: chunk})
    with pytest.raises(ValueError) as err:
        schema.model_validate(
            {
                "edits": [{"id": "R009", "text": "x"}, {"id": "R001"}],
                "removals": ["R001", "R007"],
            }
        )
    text = str(err.value)
    assert "edits[0] (R009): no such requirement" in text
    assert "edits[1] (R001): changes nothing" in text
    assert "removals[0] (R001): R001 appears in more than one operation" in text
    assert "removals[1] (R007): no such requirement" in text
    assert schema.model_validate({}).model_dump() == RequirementsPatch().model_dump()


def test_patch_schema_verifies_quotes_against_the_named_chunk(chunk):
    schema = requirements_patch_schema(["R001"], {chunk.id: chunk})
    good = {
        "text": "New.",
        "type": "technical",
        "strictness": "mandatory",
        "quote": quote_of(chunk),
        "chunk_id": chunk.id,
    }
    schema.model_validate({"additions": [good]})
    with pytest.raises(ValueError, match="was not found verbatim in chunk"):
        schema.model_validate({"additions": [{**good, "quote": "words that are not there"}]})
    with pytest.raises(ValueError, match="does not exist"):
        schema.model_validate({"additions": [{**good, "chunk_id": "S999.1"}]})
    with pytest.raises(ValueError, match="without its chunk_id"):
        schema.model_validate({"edits": [{"id": "R001", "quote": quote_of(chunk)}]})


def test_apply_patch_edits_adds_and_removes_with_stable_ids(fx, chunk):
    current = three_requirements(fx, chunk)
    patch = RequirementsPatch.model_validate(
        {
            "edits": [{"id": "R001", "text": "Provide a hosted, accessible portal."}],
            "additions": [
                {
                    "text": "Train staff.",
                    "type": "functional",
                    "strictness": "desired",
                    "quote": quote_of(chunk),
                    "chunk_id": chunk.id,
                }
            ],
            "removals": ["R003"],
        }
    )
    out, removed = apply_patch(current, patch)
    assert removed == ["R003"]
    by_id = {r.id: r for r in out.requirements}
    assert list(by_id) == ["R001", "R002", "R004"]  # R003 is never reused
    assert by_id["R001"].text == "Provide a hosted, accessible portal."
    assert by_id["R001"].origin is RequirementOrigin.REVIEWED
    assert by_id["R001"].conflicts_with == []  # the reference to R003 is stripped
    assert by_id["R002"].origin is RequirementOrigin.GENERATED
    assert by_id["R004"].quote_verified and by_id["R004"].chunk_ids == [chunk.id]
    assert out.ambiguities[0].requirement_ids == []


def test_revise_requirements_retries_on_a_bad_quote_then_applies(fx, chunk, split, tmp_path):
    bad = {"edits": [{"id": "R001", "quote": "not in the chunk at all", "chunk_id": chunk.id}]}
    good = {"edits": [{"id": "R001", "quote": quote_of(chunk), "chunk_id": chunk.id}]}
    model = ScriptedChatModel(
        responses=[
            tool_call_msg("RequirementsPatch", bad),
            tool_call_msg("RequirementsPatch", good),
        ]
    )
    rec = recorder(tmp_path)
    out, removed = revise_requirements(
        fx["requirements"],
        split,
        instruction="Quote the right span for R001.",
        title="T",
        model=model,
        settings=SETTINGS,
        recorder=rec,
    )
    assert removed == []
    assert out.requirements[0].quote == quote_of(chunk)
    assert len(model.calls) == 2
    assert "was not found verbatim" in str(model.calls[1][-1].content)
    assert rec.log.nodes[-1].node == "revise_requirements"
    assert rec.log.nodes[-1].retries == 1
    assert "Quote the right span for R001." in str(model.calls[0][0].content)


# --------------------------------------------------------------------------------------
# Problem statement
# --------------------------------------------------------------------------------------


def statement_args(cid: str, extra: str | None = None) -> dict:
    claims = {"text": "Paper process.", "kind": "fact", "chunk_ids": [cid]}
    goal = [{"text": "A portal.", "kind": "fact", "chunk_ids": [cid]}]
    if extra:
        goal.append({"text": "Win with Azure.", "kind": "inference", "chunk_ids": [extra]})
    return {
        "client_situation": [claims],
        "goal": goal,
        "success_criteria": [{"text": "Go-live.", "kind": "fact", "chunk_ids": [cid]}],
        "constraints": [{"text": "Budget.", "kind": "fact", "chunk_ids": [cid]}],
    }


def test_revise_problem_cites_brief_ids_only_with_a_brief(fx, chunk, split, tmp_path):
    current = fx["problem"].model_copy(update={"mode": "full_text"})
    brief = parse_brief("We prefer Azure.")
    model = ScriptedChatModel(
        responses=[tool_call_msg("ProblemStatement", statement_args(chunk.id, "H1"))]
    )
    out = revise_problem(
        current,
        split,
        instruction="Add the Azure preference.",
        title="T",
        brief=brief,
        model=model,
        settings=SETTINGS,
        recorder=recorder(tmp_path),
    )
    assert out.mode == "full_text"
    assert [c.chunk_ids for c in out.statement.goal] == [[chunk.id], ["H1"]]

    refused = ScriptedChatModel(
        responses=[tool_call_msg("ProblemStatement", statement_args(chunk.id, "H1"))] * 2
    )
    with pytest.raises(StructuredOutputError):
        revise_problem(
            current,
            split,
            instruction="Add it.",
            title="T",
            brief=None,
            model=refused,
            settings=SETTINGS,
            recorder=recorder(tmp_path),
        )


# --------------------------------------------------------------------------------------
# Solution
# --------------------------------------------------------------------------------------


def component(cid: str | None, title: str, reqs: list[str], chunk_id: str) -> dict:
    out = {
        "title": title,
        "description": f"{title} meets {', '.join(reqs)}.",
        "requirement_ids": reqs,
        "claims": [{"text": "Paper today.", "kind": "fact", "chunk_ids": [chunk_id]}],
    }
    if cid is not None:
        out["id"] = cid
    return out


def test_revise_solution_keeps_ids_assigns_next_free_and_recomputes_coverage(fx, chunk, tmp_path):
    reply = {
        "summary": "A hosted portal.",
        "components": [
            component("C01", "Portal", ["R001"], chunk.id),
            component(None, "Training", ["R001"], chunk.id),
        ],
        "assumptions": [],
    }
    model = ScriptedChatModel(responses=[tool_call_msg("SolutionDraft", reply)])
    out = revise_solution(
        fx["solution"],
        fx["requirements"],
        fx["problem"].statement,
        instruction="Add training.",
        title="T",
        model=model,
        settings=SETTINGS,
        recorder=recorder(tmp_path),
    )
    assert [c.id for c in out.solution.components] == ["C01", "C02"]
    assert out.solution.coverage.mandatory_covered == 1
    assert out.rounds == fx["solution"].rounds


def test_revise_solution_refuses_unknown_ids_and_coverage_regressions(fx, chunk, tmp_path):
    unknown = {
        "summary": "S.",
        "components": [component("C09", "Portal", ["R001"], chunk.id)],
        "assumptions": [],
    }
    model = ScriptedChatModel(responses=[tool_call_msg("SolutionDraft", unknown)] * 2)
    with pytest.raises(StructuredOutputError):
        revise_solution(
            fx["solution"],
            fx["requirements"],
            fx["problem"].statement,
            instruction="x",
            title="T",
            model=model,
            settings=SETTINGS,
            recorder=recorder(tmp_path),
        )
    assert "'C09' is not in the current components" in str(model.calls[1][-1].content)

    lost = {
        "summary": "S.",
        "components": [component("C01", "Portal", ["R002"], chunk.id)],  # R001 dropped
        "assumptions": [],
    }
    model = ScriptedChatModel(responses=[tool_call_msg("SolutionDraft", lost)] * 2)
    with pytest.raises(StructuredOutputError):
        revise_solution(
            fx["solution"],
            fx["requirements"],
            fx["problem"].statement,
            instruction="Drop the portal.",
            title="T",
            model=model,
            settings=SETTINGS,
            recorder=recorder(tmp_path),
        )
    assert "R001: Provide a hosted portal." in str(model.calls[1][-1].content)


# --------------------------------------------------------------------------------------
# Risks
# --------------------------------------------------------------------------------------


def risk(rid: str | None, title: str, severity: str, chunk_id: str) -> dict:
    out = {
        "title": title,
        "description": "Could happen.",
        "severity": severity,
        "likelihood": "medium",
        "justification": "Because.",
        "source": "rfp",
        "requirement_ids": ["R001"],
        "chunk_ids": [chunk_id],
        "mitigation": "Ask.",
    }
    if rid is not None:
        out["id"] = rid
    return out


def test_rekey_risks_keeps_ids_and_sorts_without_renumbering(fx, chunk):
    draft = RiskAssessmentRevision.model_validate(
        {
            "risks": [
                risk("K01", "Slip", "low", chunk.id),
                risk(None, "Budget", "high", chunk.id),
            ]
        }
    )
    out = rekey_risks(draft, fx["risks"].assessment)
    assert [(k.id, k.title) for k in out.risks] == [("K02", "Budget"), ("K01", "Slip")]


def test_revise_risks_keeps_the_count_band_and_ids(fx, chunk, tmp_path):
    two = {"risks": [risk("K01", "Slip", "high", chunk.id), risk(None, "B", "low", chunk.id)]}
    three = {
        "risks": [
            risk("K01", "Slip", "high", chunk.id),
            risk(None, "Budget", "medium", chunk.id),
            risk(None, "Staff", "low", chunk.id),
        ]
    }
    model = ScriptedChatModel(
        responses=[
            tool_call_msg("RiskAssessmentDraft", two),
            tool_call_msg("RiskAssessmentDraft", three),
        ]
    )
    out = revise_risks(
        fx["risks"],
        fx["requirements"],
        fx["problem"].statement,
        fx["solution"].solution,
        instruction="Add budget and staffing risks.",
        title="T",
        model=model,
        settings=SETTINGS,
        recorder=recorder(tmp_path),
    )
    assert "risks has 2 entries" in str(model.calls[1][-1].content)
    assert [k.id for k in out.assessment.risks] == ["K01", "K02", "K03"]
