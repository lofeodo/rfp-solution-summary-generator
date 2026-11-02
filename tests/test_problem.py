"""Problem statement (S6) with a scripted fake model. No network."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from fakes import ScriptedChatModel, text_msg, tool_call_msg
from rfp_agent.agents.problem import (
    CHUNK_NODE,
    FULL_TEXT_EVIDENCE,
    FULL_TEXT_NODE,
    HIERARCHICAL_EVIDENCE,
    SYNTHESIS_NODE,
    NoEvidenceError,
    ProblemResult,
    build_problem_statement,
    evidence_ids,
    format_evidence,
    format_full_text,
    problem_schema,
    render_chunk_prompt,
    summarise_chunks,
    synthesise,
)
from rfp_agent.config import Settings
from rfp_agent.llm import StructuredOutputError, load_prompt
from rfp_agent.observability import RunRecorder
from rfp_agent.schemas import (
    Chunk,
    ChunkSummary,
    ClaimKind,
    ProblemStatement,
    Section,
    SectionKind,
    SplitDocument,
)

SETTINGS = Settings(_env_file=None, max_structured_retries=1, llm_concurrency=1)
TITLE = "Example RFP"


def chunk(cid: str, sid: str, path: list[str], text: str, page: int = 1) -> Chunk:
    return Chunk(
        id=cid, section_id=sid, section_path=path, page_start=page, page_end=page, text=text
    )


# S2.2 repeats the last sentence of S2.1, as the splitter does within a section.
SPLIT = SplitDocument(
    sections=[
        Section(
            id="S1",
            title="Front matter",
            level=1,
            path=["Front matter"],
            page_start=1,
            page_end=1,
            kind=SectionKind.NARRATIVE,
            chunks=[chunk("S1.1", "S1", ["Front matter"], "Issued: August 8, 2025.")],
        ),
        Section(
            id="S2",
            title="Scope",
            level=2,
            path=["RFP", "Scope"],
            page_start=2,
            page_end=3,
            kind=SectionKind.REQUIREMENT_BEARING,
            chunks=[
                chunk("S2.1", "S2", ["RFP", "Scope"], "Alpha one. Alpha two.", page=2),
                chunk("S2.2", "S2", ["RFP", "Scope"], "Alpha two.\n\nBeta budget $5.", page=3),
            ],
        ),
    ]
)
ALL_IDS = ["S1.1", "S2.1", "S2.2"]


def draft(relevant: bool = True, summary: str = "A fact.") -> dict:
    return tool_call_msg("ChunkSummaryDraft", {"relevant": relevant, "summary": summary})


def claim(text: str, *ids: str, kind: str = "fact") -> dict:
    return {"text": text, "kind": kind, "chunk_ids": list(ids)}


def statement(**lists) -> dict:
    base = {
        "client_situation": [claim("Who.", "S1.1")],
        "goal": [claim("What.", "S2.1")],
        "success_criteria": [claim("How judged.", "S2.2")],
        "constraints": [claim("Budget $5.", "S2.2")],
    }
    return tool_call_msg("ProblemStatement", base | lists)


def recorder(tmp_path) -> RunRecorder:
    return RunRecorder("example.pdf", "fake:scripted", 0.0, runs_dir=tmp_path / "runs")


# --------------------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------------------


def test_prompt_placeholders():
    assert load_prompt("problem_chunk").variables == {
        "title",
        "chunk_id",
        "section_path",
        "pages",
        "text",
    }
    assert load_prompt("problem_synthesis").variables == {"title", "evidence_kind", "evidence"}


def test_chunk_prompt_content():
    text = render_chunk_prompt(SPLIT.chunks()[1], title=TITLE)
    assert "Title: Example RFP" in text
    assert "Chunk: S2.1" in text
    assert "Section: RFP > Scope" in text
    assert "Pages: 2" in text
    assert "<chunk>\nAlpha one. Alpha two.\n</chunk>" in text


# --------------------------------------------------------------------------------------
# Stage one
# --------------------------------------------------------------------------------------


def test_chunk_ids_set_by_code_in_document_order():
    model = ScriptedChatModel(responses=[draft(), draft(False, ""), draft(summary="Budget $5.")])
    out = summarise_chunks(SPLIT, title=TITLE, model=model, settings=SETTINGS)
    assert [s.chunk_id for s in out] == ALL_IDS
    assert [s.relevant for s in out] == [True, False, True]
    assert out[2].summary == "Budget $5."
    assert all(s.error is None for s in out)
    assert len(model.calls) == 3
    assert isinstance(model.calls[0][0], HumanMessage)
    assert "Chunk: S1.1" in model.calls[0][0].content


def test_irrelevant_or_empty_summary_is_not_evidence():
    # Not relevant with text anyway; relevant with nothing to say.
    model = ScriptedChatModel(responses=[draft(False, "ignored"), draft(True, "  "), draft()])
    out = summarise_chunks(SPLIT, title=TITLE, model=model, settings=SETTINGS)
    assert (out[0].relevant, out[0].summary) == (False, "")
    assert (out[1].relevant, out[1].summary) == (False, "")
    assert evidence_ids(out) == ["S2.2"]


def test_failed_chunk_kept_with_error(tmp_path):
    # First chunk: two replies without a tool call exhaust the budget (1 retry).
    model = ScriptedChatModel(responses=[text_msg("no"), text_msg("no"), draft(), draft()])
    rec = recorder(tmp_path)
    out = summarise_chunks(SPLIT, title=TITLE, model=model, settings=SETTINGS, recorder=rec)
    assert [s.chunk_id for s in out] == ALL_IDS
    assert out[0].relevant is False and out[0].summary == ""
    assert out[0].error and "after 2 attempts" in out[0].error
    assert out[1].error is None and out[1].relevant
    nodes = [n.node for n in rec.log.nodes]
    assert nodes == [CHUNK_NODE] * 3  # the failed call is recorded too
    assert rec.log.nodes[0].retries == 1


def test_concurrent_calls_keep_document_order():
    settings = Settings(_env_file=None, max_structured_retries=0, llm_concurrency=3)
    model = ScriptedChatModel(responses=[draft(summary=f"fact {i}") for i in range(3)])
    out = summarise_chunks(SPLIT, title=TITLE, model=model, settings=settings)
    assert [s.chunk_id for s in out] == ALL_IDS
    assert len(model.calls) == 3
    # Every chunk was sent exactly once, whichever thread took it.
    sent = sorted(m[0].content.split("Chunk: ")[1].split("\n")[0] for m in model.calls)
    assert sent == ALL_IDS


# --------------------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------------------


def test_evidence_lists_relevant_summaries_in_order_with_context():
    summaries = [
        ChunkSummary(chunk_id="S1.1", summary="Issued August 8, 2025.", relevant=True),
        ChunkSummary(chunk_id="S2.1", summary="", relevant=False),
        ChunkSummary(chunk_id="S2.2", summary="Budget $5.", relevant=True),
    ]
    evidence = format_evidence(summaries, SPLIT)
    assert evidence == (
        "[S1.1] Front matter (pages 1)\nIssued August 8, 2025.\n\n"
        "[S2.2] RFP > Scope (pages 3)\nBudget $5."
    )
    assert evidence_ids(summaries) == ["S1.1", "S2.2"]


def test_full_text_has_every_chunk_once_without_overlap():
    evidence, ids = format_full_text(SPLIT)
    assert ids == ALL_IDS
    assert evidence.count("Alpha two.") == 1
    assert "[S2.2] RFP > Scope (pages 3)\nBeta budget $5." in evidence
    assert "[S2.1] RFP > Scope (pages 2)\nAlpha one. Alpha two." in evidence


# --------------------------------------------------------------------------------------
# Synthesis
# --------------------------------------------------------------------------------------


def test_problem_schema_accepts_known_ids_and_is_named_like_the_contract():
    schema = problem_schema(ALL_IDS)
    assert schema.__name__ == "ProblemStatement"
    value = schema.model_validate(statement().tool_calls[0]["args"])
    assert isinstance(value, ProblemStatement)


def test_unknown_citation_is_fed_back_then_accepted(tmp_path):
    bad = statement(goal=[claim("What.", "S2.1", "S9.9")])
    model = ScriptedChatModel(responses=[bad, statement()])
    rec = recorder(tmp_path)
    out = synthesise(
        "[S1.1] x",
        ALL_IDS,
        evidence_kind=HIERARCHICAL_EVIDENCE,
        title=TITLE,
        model=model,
        settings=SETTINGS,
        recorder=rec,
    )
    assert type(out) is ProblemStatement
    assert out.goal[0].chunk_ids == ["S2.1"]
    assert rec.log.nodes[-1].retries == 1
    feedback = model.calls[1][-1]
    assert isinstance(feedback, ToolMessage)
    assert "S9.9" in feedback.content and "not in the evidence" in feedback.content


def test_empty_list_is_fed_back(tmp_path):
    model = ScriptedChatModel(responses=[statement(constraints=[]), statement()])
    out = synthesise(
        "[S1.1] x",
        ALL_IDS,
        evidence_kind=HIERARCHICAL_EVIDENCE,
        title=TITLE,
        model=model,
        settings=SETTINGS,
    )
    assert len(out.constraints) == 1
    assert "constraints is empty" in model.calls[1][-1].content


def test_synthesis_exhaustion_raises():
    bad = statement(goal=[claim("What.", "S9.9")])
    model = ScriptedChatModel(responses=[bad, bad])
    with pytest.raises(StructuredOutputError, match="S9.9"):
        synthesise(
            "[S1.1] x",
            ALL_IDS,
            evidence_kind=HIERARCHICAL_EVIDENCE,
            title=TITLE,
            model=model,
            settings=SETTINGS,
        )


def test_synthesis_prompt_carries_evidence_and_kind():
    model = ScriptedChatModel(responses=[statement()])
    synthesise(
        "[S1.1] the evidence",
        ALL_IDS,
        evidence_kind=FULL_TEXT_EVIDENCE,
        title=TITLE,
        model=model,
        settings=SETTINGS,
    )
    text = model.calls[0][0].content
    assert "Title: Example RFP" in text
    assert FULL_TEXT_EVIDENCE in text
    assert "<evidence>\n[S1.1] the evidence\n</evidence>" in text


# --------------------------------------------------------------------------------------
# The step
# --------------------------------------------------------------------------------------


def test_hierarchical_end_to_end(tmp_path):
    # S2.1 is irrelevant, so the statement may cite S1.1 and S2.2 only.
    final = statement(goal=[claim("What.", "S2.2")])
    model = ScriptedChatModel(responses=[draft(), draft(False, ""), draft(), final])
    rec = recorder(tmp_path)
    with rec.activate(write=False):
        result = build_problem_statement(SPLIT, title=TITLE, model=model, settings=SETTINGS)
    assert result.mode == "hierarchical"
    assert [s.chunk_id for s in result.chunk_summaries] == ALL_IDS
    assert result.statement.constraints[0].text == "Budget $5."
    assert result.statement.goal[0].kind is ClaimKind.FACT
    assert [n.node for n in rec.log.nodes] == [CHUNK_NODE] * 3 + [SYNTHESIS_NODE]
    assert set(rec.log.prompt_hashes) == {"problem_chunk", "problem_synthesis"}
    synthesis_prompt = model.calls[3][0].content
    assert HIERARCHICAL_EVIDENCE in synthesis_prompt
    assert "[S1.1]" in synthesis_prompt and "[S2.1]" not in synthesis_prompt


def test_full_text_mode_from_settings_flag(tmp_path):
    settings = Settings(_env_file=None, max_structured_retries=1, full_text_problem=True)
    model = ScriptedChatModel(responses=[statement()])
    rec = recorder(tmp_path)
    result = build_problem_statement(
        SPLIT, title=TITLE, model=model, settings=settings, recorder=rec
    )
    assert result.mode == "full_text"
    assert result.chunk_summaries == []
    assert [n.node for n in rec.log.nodes] == [FULL_TEXT_NODE]
    text = model.calls[0][0].content
    assert FULL_TEXT_EVIDENCE in text
    assert all(f"[{i}]" in text for i in ALL_IDS)
    assert "Beta budget $5." in text


def test_full_text_argument_overrides_settings():
    model = ScriptedChatModel(responses=[statement()])
    result = build_problem_statement(
        SPLIT, title=TITLE, model=model, settings=SETTINGS, full_text=True
    )
    assert result.mode == "full_text" and len(model.calls) == 1


def test_no_relevant_chunk_raises_before_synthesis():
    model = ScriptedChatModel(responses=[draft(False, "")] * 3)
    with pytest.raises(NoEvidenceError, match="none of the 3 chunks"):
        build_problem_statement(SPLIT, title=TITLE, model=model, settings=SETTINGS)
    assert len(model.calls) == 3


def test_result_round_trips_as_json():
    result = ProblemResult(
        mode="hierarchical",
        statement=ProblemStatement(goal=[{"text": "x", "chunk_ids": ["S1.1"]}]),
        chunk_summaries=[ChunkSummary(chunk_id="S1.1", summary="x", error=None)],
    )
    assert ProblemResult.model_validate_json(result.model_dump_json()) == result
