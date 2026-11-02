"""The checkpoint's pure parts (ST12a): the pursuit brief, the reviewer's decisions, the
brief as citable evidence in the agents' validators, the assembler and the renderer.
No network, no graph."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pipeline_stubs import PDF, fixtures
from rfp_agent.agents import risk as risk_mod
from rfp_agent.agents import solution as solution_mod
from rfp_agent.agents.solution import solution_schema
from rfp_agent.brief import (
    BRIEF_SECTION_TITLE,
    NONE_PROVIDED,
    brief_chunk_ids,
    brief_chunk_refs,
    format_brief,
    parse_brief,
)
from rfp_agent.checkpoint import CheckpointError, apply_checkpoint, validate_checkpoint
from rfp_agent.parsing import parse_pdf
from rfp_agent.render import CitationError, assemble
from rfp_agent.render.markdown import NONE, render_markdown
from rfp_agent.schemas import (
    Ambiguity,
    CheckpointRecord,
    Claim,
    DecisionAction,
    EvidenceSource,
    Requirement,
    RequirementDecision,
    RequirementOrigin,
    RequirementsOutput,
    RequirementType,
    ReviewHistory,
    Strictness,
)
from rfp_agent.splitting import split_document

CID = "S1.1"


def req(rid: str, **overrides) -> Requirement:
    base = dict(
        id=rid,
        text=f"Requirement {rid}.",
        type=RequirementType.FUNCTIONAL,
        strictness=Strictness.MANDATORY,
        quote=f"Requirement {rid}.",
        chunk_ids=[CID],
    )
    return Requirement(**{**base, **overrides})


REQS = RequirementsOutput(
    requirements=[
        req("R001"),
        req("R002", conflicts_with=["R003"]),
        req("R003", conflicts_with=["R002"], type=RequirementType.SUBMISSION),
    ],
    ambiguities=[
        Ambiguity(
            id="A01", description="Unclear.", chunk_ids=[CID], requirement_ids=["R002", "R003"]
        )
    ],
)


def record(*decisions: RequirementDecision, brief: str | None = None) -> CheckpointRecord:
    return CheckpointRecord(
        reviewer="Dana",
        confirmed_at=datetime.now(UTC),
        decisions=list(decisions),
        brief=parse_brief(brief),
    )


# --------------------------------------------------------------------------------------
# Brief
# --------------------------------------------------------------------------------------


def test_parse_brief_splits_paragraphs_into_h_chunks():
    brief = parse_brief("Win theme: speed.\n\nWe have delivered this twice.\r\n\r\n\nAvoid Oracle.")
    assert brief is not None
    assert brief.chunk_ids() == ["H1", "H2", "H3"]
    assert [c.text for c in brief.chunks] == [
        "Win theme: speed.",
        "We have delivered this twice.",
        "Avoid Oracle.",
    ]
    assert "\r" not in brief.text


def test_parse_brief_attaches_headings_to_the_next_paragraph():
    text = "# Win themes\n\n- speed\n- price\n\nConstraints:\n\nNo offshore team.\n\n## Trailing"
    brief = parse_brief(text)
    assert brief is not None
    assert [c.text for c in brief.chunks] == [
        "# Win themes\n- speed\n- price",
        "Constraints:\nNo offshore team.",
        "## Trailing",
    ]


@pytest.mark.parametrize("text", [None, "", "   \n\n  "])
def test_parse_brief_blank_is_none(text):
    assert parse_brief(text) is None
    assert brief_chunk_ids(None) == []
    assert brief_chunk_refs(None) == []
    assert format_brief(None) == NONE_PROVIDED


def test_brief_refs_and_prompt_lines():
    brief = parse_brief("# Themes\n\nspeed and\nprice\n\nAzure only.")
    refs = brief_chunk_refs(brief)
    assert [r.id for r in refs] == ["H1", "H2"]
    assert all(r.source is EvidenceSource.BRIEF for r in refs)
    assert all(r.page_start is None and r.page_end is None for r in refs)
    assert all(r.section_title == BRIEF_SECTION_TITLE for r in refs)
    assert format_brief(brief) == "H1: # Themes speed and price\nH2: Azure only."


# --------------------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------------------


def test_accept_all_is_identity():
    out = apply_checkpoint(REQS, record())
    assert out == REQS
    assert validate_checkpoint(REQS, record(RequirementDecision(requirement_id="R001"))) == []


def test_reject_removes_requirement_and_every_reference_to_it():
    out = apply_checkpoint(
        REQS, record(RequirementDecision(requirement_id="R003", action=DecisionAction.REJECT))
    )
    assert out.requirement_ids() == ["R001", "R002"]
    assert out.requirements[1].conflicts_with == []
    assert out.ambiguities[0].requirement_ids == ["R002"]
    # Untouched requirements keep their origin; nothing else changed.
    assert all(r.origin is RequirementOrigin.GENERATED for r in out.requirements)
    assert out.gaps == REQS.gaps


def test_strictness_and_type_changes_mark_origin_reviewed():
    out = apply_checkpoint(
        REQS,
        record(
            RequirementDecision(requirement_id="R001", strictness=Strictness.DESIRED),
            RequirementDecision(requirement_id="R002", type=RequirementType.TECHNICAL),
            RequirementDecision(requirement_id="R003", strictness=Strictness.MANDATORY),  # same
        ),
    )
    r1, r2, r3 = out.requirements
    assert r1.strictness is Strictness.DESIRED and r1.origin is RequirementOrigin.REVIEWED
    assert r2.type is RequirementType.TECHNICAL and r2.origin is RequirementOrigin.REVIEWED
    assert r3 == REQS.requirements[2]  # a no-op edit leaves the requirement as generated


def test_record_helpers_list_rejected_and_edited_ids():
    rec = record(
        RequirementDecision(requirement_id="R001", action=DecisionAction.REJECT),
        RequirementDecision(requirement_id="R002", strictness=Strictness.OPTIONAL),
        RequirementDecision(requirement_id="R003"),
    )
    assert rec.rejected_ids() == ["R001"]
    assert rec.edited_ids() == ["R002"]


def test_bad_records_are_refused_with_every_problem_named():
    rec = record(
        RequirementDecision(requirement_id="R009", action=DecisionAction.REJECT),
        RequirementDecision(requirement_id="R001", strictness=Strictness.DESIRED),
        RequirementDecision(requirement_id="R001", type=RequirementType.OTHER),
        RequirementDecision(
            requirement_id="R002", action=DecisionAction.REJECT, strictness=Strictness.OPTIONAL
        ),
    )
    problems = validate_checkpoint(REQS, rec)
    assert problems == [
        "R009: no such requirement",
        "R001: more than one decision",
        "R002: a rejected requirement cannot also be edited",
    ]
    with pytest.raises(CheckpointError, match="R009: no such requirement; R001: more than one"):
        apply_checkpoint(REQS, rec)


def test_schema_rejects_malformed_decisions():
    with pytest.raises(ValueError):
        RequirementDecision(requirement_id="X1")
    with pytest.raises(ValueError):
        CheckpointRecord(reviewer="", confirmed_at=datetime.now(UTC))


# --------------------------------------------------------------------------------------
# The brief as evidence in the agents, the assembler and the renderer
# --------------------------------------------------------------------------------------


def test_brief_chunks_join_the_allowed_ids_of_both_agents(chunk_id):
    fx = fixtures(chunk_id)
    reqs, problem, solution = fx["requirements"], fx["problem"].statement, fx["solution"].solution
    brief = parse_brief("We prefer Azure.\n\nTeam of four.")
    assert solution_mod.allowed_chunk_ids(reqs, problem) == [chunk_id]
    assert solution_mod.allowed_chunk_ids(reqs, problem, brief) == [chunk_id, "H1", "H2"]
    assert risk_mod.allowed_chunk_ids(reqs, problem, solution, brief)[-2:] == ["H1", "H2"]
    assert "H2: Team of four." in solution_mod.render_prompt(reqs, problem, title="t", brief=brief)
    assert NONE_PROVIDED in solution_mod.render_prompt(reqs, problem, title="t")


def test_solution_validator_accepts_h_citations_only_with_a_brief(chunk_id):
    fx = fixtures(chunk_id)
    reqs, problem = fx["requirements"], fx["problem"].statement
    brief = parse_brief("We prefer Azure.")
    draft = {
        "summary": "Azure build.",
        "components": [
            {
                "title": "Portal",
                "description": "Delivers R001 on Azure.",
                "requirement_ids": ["R001"],
                "claims": [{"text": "The team prefers Azure.", "chunk_ids": ["H1"]}],
            }
        ],
        "assumptions": [],
    }
    with_brief = solution_schema(
        reqs.requirement_ids(), solution_mod.allowed_chunk_ids(reqs, problem, brief)
    )
    assert with_brief.model_validate(draft).components[0].claims[0].chunk_ids == ["H1"]
    without = solution_schema(reqs.requirement_ids(), solution_mod.allowed_chunk_ids(reqs, problem))
    with pytest.raises(ValueError, match="H1"):
        without.model_validate(draft)


def test_assembler_resolves_h_citations_and_renders_the_review_history(chunk_id):
    fx = fixtures(chunk_id)
    parsed = parse_pdf(PDF)
    split = split_document(parsed)
    brief = parse_brief("We prefer Azure.")
    solution = fx["solution"].solution.model_copy(
        update={
            "assumptions": [Claim(text="Azure is assumed.", kind="inference", chunk_ids=["H1"])]
        }
    )
    rec = CheckpointRecord(
        reviewer="Dana",
        confirmed_at=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        waited_s=42.0,
        decisions=[
            RequirementDecision(requirement_id="R002", strictness=Strictness.DESIRED, note="Soft"),
        ],
        brief=brief,
        note="Confirmed after the pre-bid call.",
    )
    kwargs = dict(
        run_id="r",
        model="m",
        parsed=parsed,
        split=split,
        requirements=apply_checkpoint(fx["requirements"], rec),
        problem_statement=fx["problem"].statement,
        solution=solution,
        risks=fx["risks"].assessment,
    )
    with pytest.raises(CitationError, match="H1"):
        assemble(**kwargs)
    summary = assemble(**kwargs, brief=brief, review=ReviewHistory(checkpoint=rec))
    assert summary.chunks[-1].id == "H1" and summary.chunks[-1].source is EvidenceSource.BRIEF
    md = render_markdown(summary)
    assert "- **Checkpoint:** confirmed by Dana on 2026-11-02T12:00:00+00:00" in md
    assert "(Pursuit brief [H1])" in md
    assert "## Review history" in md and "after 42 s" in md
    assert "- **Note:** Confirmed after the pre-bid call." in md
    assert f"- **Rejected requirements:** {NONE}" in md
    assert "  - **R002:** strictness set to desired (Soft)" in md
    assert "### Pursuit brief\n\n- **H1** We prefer Azure." in md
    # An unattended summary renders no history at all.
    unattended = {**kwargs, "requirements": fx["requirements"], "solution": fx["solution"].solution}
    plain = render_markdown(assemble(**unattended))
    assert "Review history" not in plain and "Checkpoint" not in plain
