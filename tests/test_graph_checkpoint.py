"""The checkpoint in the pipeline (ST12a): pause, state reload, resume on the same run
log, and the CLI round trip. LLM stages stubbed as in ``test_graph``; no network."""

from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from fakes import ScriptedChatModel
from pipeline_stubs import PDF, SETTINGS, Stubs
from rfp_agent import graph as graph_mod
from rfp_agent.brief import parse_brief
from rfp_agent.checkpoint import CheckpointError
from rfp_agent.cli import app
from rfp_agent.graph import (
    ASSEMBLE,
    CHECKPOINT,
    PARSE,
    PARSE_QUALITY,
    PROBLEM,
    REQUIREMENTS,
    RISK,
    SOLUTION,
    SPLIT,
    STAGES,
    PipelineStateError,
    StageEvent,
    build_pipeline,
    load_state,
    resume_pipeline,
    run_pipeline,
    waiting_checkpoint,
)
from rfp_agent.schemas import (
    CheckpointRecord,
    DecisionAction,
    RequirementDecision,
    RequirementOrigin,
    RunLog,
    StageStatus,
    Strictness,
)

READ_FILES = ("parsed.json", "quality.json", "split.json", "requirements.json", "problem.json")
DRAFT_FILES = ("solution.json", "risks.json", "summary.json", "summary.md")


def collect():
    events: list[StageEvent] = []
    lock = threading.Lock()

    def on_event(e: StageEvent) -> None:
        with lock:
            events.append(e)

    return events, on_event


def record(**overrides) -> CheckpointRecord:
    base = dict(
        reviewer="Dana",
        confirmed_at=datetime.now(UTC),
        decisions=[
            RequirementDecision(requirement_id="R002", strictness=Strictness.DESIRED),
        ],
        brief=parse_brief("We prefer Azure.\n\nTeam of four."),
    )
    return CheckpointRecord(**{**base, **overrides})


def pause(tmp_path, monkeypatch, chunk_id, **kwargs):
    stubs = Stubs(chunk_id).install(monkeypatch)
    events, on_event = collect()
    result = run_pipeline(
        PDF,
        settings=SETTINGS,
        model=ScriptedChatModel(),
        runs_dir=tmp_path,
        run_id="p1",
        on_event=on_event,
        pause_at_checkpoint=True,
        **kwargs,
    )
    return stubs, events, result


# --------------------------------------------------------------------------------------
# Pause
# --------------------------------------------------------------------------------------


def test_run_pauses_after_the_read_stages(tmp_path, monkeypatch, chunk_id):
    stubs, events, result = pause(tmp_path, monkeypatch, chunk_id)

    assert result.paused and result.paused_at == CHECKPOINT
    assert result.summary is None
    assert SOLUTION not in stubs.calls and RISK not in stubs.calls
    stages = [(s.stage, s.status) for s in result.run_log.stages]
    assert [s for s, _ in stages[:3]] == [PARSE, PARSE_QUALITY, SPLIT]
    assert {s for s, _ in stages[3:5]} == {REQUIREMENTS, PROBLEM}
    assert stages[5] == (CHECKPOINT, StageStatus.WAITING)
    assert len(stages) == 6
    assert [e.stage for e in events if e.status == StageStatus.WAITING] == [CHECKPOINT]

    run_dir = tmp_path / "p1"
    assert all((run_dir / f).exists() for f in READ_FILES)
    assert not any((run_dir / f).exists() for f in DRAFT_FILES)
    log = RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert log.finished_at is None, "a paused run is not finished"
    assert waiting_checkpoint(log) is not None
    assert waiting_checkpoint(result.run_log) is not None


def test_unattended_run_records_no_checkpoint(tmp_path, monkeypatch, chunk_id):
    Stubs(chunk_id).install(monkeypatch)
    result = run_pipeline(
        PDF, settings=SETTINGS, model=ScriptedChatModel(), runs_dir=tmp_path, run_id="u1"
    )
    assert not result.paused and result.summary is not None
    assert [s.stage for s in result.run_log.stages] == list(STAGES) or set(
        s.stage for s in result.run_log.stages
    ) == set(STAGES)
    assert CHECKPOINT not in {s.stage for s in result.run_log.stages}
    assert result.summary.review is None
    assert waiting_checkpoint(result.run_log) is None
    assert not (tmp_path / "u1" / "checkpoint.json").exists()


def test_load_state_reads_every_stage_file_back(tmp_path, monkeypatch, chunk_id):
    Stubs(chunk_id).install(monkeypatch)
    result = run_pipeline(
        PDF, settings=SETTINGS, model=ScriptedChatModel(), runs_dir=tmp_path, run_id="u2"
    )
    state = load_state(tmp_path / "u2")
    for key in (
        "parsed",
        "quality_report",
        "split",
        "requirements",
        "problem",
        "solution",
        "risks",
    ):
        assert state[key] == result.state[key], key
    assert state["requirements_report"] == result.state["requirements_report"]
    assert state["pdf_path"] == result.state["pdf_path"]
    assert "checkpoint" not in state and "summary" not in state
    assert set(state["output_paths"]) >= set(READ_FILES) | {"solution.json", "risks.json"}


def test_build_pipeline_from_a_later_stage_holds_only_those_nodes(monkeypatch, chunk_id):
    from pipeline_stubs import metric  # noqa: F401  (keeps the stub module imported)
    from rfp_agent.observability import RunRecorder

    recorder = RunRecorder.from_settings("x.pdf", SETTINGS, run_id="g")
    kwargs = dict(settings=SETTINGS, recorder=recorder, model=ScriptedChatModel())
    full = build_pipeline(**kwargs).get_graph()
    assert {CHECKPOINT, PARSE, ASSEMBLE} <= set(full.nodes)
    tail = build_pipeline(start_stage=SOLUTION, **kwargs).get_graph()
    assert set(tail.nodes) == {"__start__", SOLUTION, RISK, ASSEMBLE, "__end__"}
    with pytest.raises(ValueError, match="start_stage"):
        build_pipeline(start_stage=CHECKPOINT, **kwargs)


# --------------------------------------------------------------------------------------
# Resume
# --------------------------------------------------------------------------------------


def test_resume_applies_the_record_and_drafts_on_the_same_log(tmp_path, monkeypatch, chunk_id):
    stubs, events, paused = pause(tmp_path, monkeypatch, chunk_id)
    run_dir = tmp_path / "p1"
    first_nodes = len(paused.run_log.nodes)

    result = resume_pipeline(
        run_dir, record(), settings=SETTINGS, model=ScriptedChatModel(), on_event=events.append
    )

    assert not result.paused and result.summary is not None
    # The stubs saw the confirmed requirements and the brief.
    seen = stubs.calls[SOLUTION]
    assert seen["brief"].chunk_ids() == ["H1", "H2"]
    assert stubs.calls[RISK]["brief"] is seen["brief"]
    confirmed = seen["requirements"]
    r2 = next(r for r in confirmed.requirements if r.id == "R002")
    assert r2.strictness is Strictness.DESIRED and r2.origin is RequirementOrigin.REVIEWED
    # One run log across the pause: the read-stage calls are still there, the waiting
    # record closed with the time waited, and the draft stages appended.
    log = result.run_log
    assert log.run_id == "p1" and len(log.nodes) > first_nodes
    assert {n.node for n in log.nodes} >= {"parse_quality", "solution_generate", "risk_assess"}
    stages = [(s.stage, s.status) for s in log.stages]
    assert stages[5] == (CHECKPOINT, StageStatus.FINISHED)
    assert [s for s, _ in stages[6:]] == [SOLUTION, RISK, ASSEMBLE]
    checkpoint = log.stages[5]
    assert checkpoint.latency_s >= 0 and log.finished_at is not None
    assert checkpoint.started_at == paused.run_log.stages[5].started_at
    closed = [e for e in events if e.stage == CHECKPOINT and e.status == StageStatus.FINISHED]
    assert len(closed) == 1 and closed[0].latency_s == pytest.approx(checkpoint.latency_s)
    # Files: the extractor's output is untouched, the confirmed list and the record are new.
    assert all((run_dir / f).exists() for f in DRAFT_FILES + ("checkpoint.json",))
    original = json.loads((run_dir / "requirements.json").read_text(encoding="utf-8"))
    assert original["requirements"][1]["strictness"] == "mandatory"
    saved = json.loads((run_dir / "requirements_confirmed.json").read_text(encoding="utf-8"))
    assert saved["requirements"][1]["strictness"] == "desired"
    rec = CheckpointRecord.model_validate_json(
        (run_dir / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert rec.reviewer == "Dana" and rec.waited_s == pytest.approx(checkpoint.latency_s)
    # The summary carries the history and the brief chunks.
    summary = result.summary
    assert summary.review is not None and summary.review.checkpoint.reviewer == "Dana"
    assert [c.id for c in summary.chunks[-2:]] == ["H1", "H2"]
    md = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "## Review history" in md and "**H2** Team of four." in md
    written = RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert written.finished_at is not None and len(written.stages) == 9
    # A second resume is refused: the run is no longer waiting.
    with pytest.raises(PipelineStateError, match="not waiting"):
        resume_pipeline(run_dir, record(), settings=SETTINGS, model=ScriptedChatModel())


def test_resume_with_a_rejection_drops_the_requirement_everywhere(tmp_path, monkeypatch, chunk_id):
    stubs, _, _ = pause(tmp_path, monkeypatch, chunk_id)
    rec = record(
        decisions=[RequirementDecision(requirement_id="R002", action=DecisionAction.REJECT)],
        brief=None,
    )
    result = resume_pipeline(tmp_path / "p1", rec, settings=SETTINGS, model=ScriptedChatModel())
    assert stubs.calls[SOLUTION]["brief"] is None
    assert result.summary.requirements.requirement_ids() == ["R001"]
    assert result.summary.review.checkpoint.rejected_ids() == ["R002"]
    assert all(c.id.startswith("S") for c in result.summary.chunks)


def test_resume_refuses_bad_records_before_writing_anything(tmp_path, monkeypatch, chunk_id):
    pause(tmp_path, monkeypatch, chunk_id)
    run_dir = tmp_path / "p1"
    bad = record(
        decisions=[RequirementDecision(requirement_id="R999", action=DecisionAction.REJECT)]
    )
    with pytest.raises(CheckpointError, match="R999: no such requirement"):
        resume_pipeline(run_dir, bad, settings=SETTINGS, model=ScriptedChatModel())
    assert not (run_dir / "checkpoint.json").exists()
    assert not (run_dir / "requirements_confirmed.json").exists()
    log = RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert waiting_checkpoint(log) is not None, "still waiting"


def test_resume_refuses_directories_that_are_not_waiting(tmp_path, monkeypatch, chunk_id):
    with pytest.raises(PipelineStateError, match="no run log"):
        resume_pipeline(
            tmp_path / "missing", record(), settings=SETTINGS, model=ScriptedChatModel()
        )
    Stubs(chunk_id).install(monkeypatch)
    run_pipeline(PDF, settings=SETTINGS, model=ScriptedChatModel(), runs_dir=tmp_path, run_id="u3")
    with pytest.raises(PipelineStateError, match="not waiting"):
        resume_pipeline(tmp_path / "u3", record(), settings=SETTINGS, model=ScriptedChatModel())


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def test_cli_run_pauses_by_default_and_checkpoint_drafts(tmp_path, monkeypatch, chunk_id):
    stubs = Stubs(chunk_id).install(monkeypatch)
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda **kw: ScriptedChatModel())
    monkeypatch.setattr(graph_mod, "get_settings", lambda: SETTINGS)
    runner = CliRunner()
    runs = ["--runs-dir", str(tmp_path)]

    result = runner.invoke(app, ["run", str(PDF), *runs, "--run-id", "c1"])
    assert result.exit_code == 0, result.output
    assert "checkpoint: waiting for a reviewer" in result.output
    assert "paused at the checkpoint with 2 requirements" in result.output
    assert "python -m rfp_agent checkpoint c1 --reviewer" in result.output
    assert not (tmp_path / "c1" / "summary.md").exists()

    brief = tmp_path / "brief.md"
    brief.write_text("We prefer Azure.\n\nTeam of four.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "checkpoint",
            "c1",
            *runs,
            "--reviewer",
            "Dana",
            "--brief",
            str(brief),
            "--strictness",
            "R002=desired",
            "--type",
            "R002=other",
            "--note",
            "After the pre-bid call",
            "--max-iterations",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "checkpoint: finished" in result.output and "assemble" in result.output
    assert "coverage 1/1 mandatory" in result.output and "summary.md" in result.output
    assert stubs.calls[SOLUTION]["max_iterations"] == 1
    assert stubs.calls[SOLUTION]["brief"].chunk_ids() == ["H1", "H2"]
    rec = CheckpointRecord.model_validate_json(
        (tmp_path / "c1" / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert rec.reviewer == "Dana" and rec.note == "After the pre-bid call"
    assert [d.model_dump(exclude_none=True) for d in rec.decisions] == [
        {"requirement_id": "R002", "action": "accept", "strictness": "desired", "type": "other"}
    ]
    md = (tmp_path / "c1" / "summary.md").read_text(encoding="utf-8")
    assert "confirmed by Dana" in md


def test_cli_checkpoint_rejects_bad_arguments_and_states(tmp_path, monkeypatch, chunk_id):
    Stubs(chunk_id).install(monkeypatch)
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda **kw: ScriptedChatModel())
    monkeypatch.setattr(graph_mod, "get_settings", lambda: SETTINGS)
    runner = CliRunner()
    runs = ["--runs-dir", str(tmp_path)]
    assert runner.invoke(app, ["run", str(PDF), *runs, "--run-id", "c2"]).exit_code == 0

    def plain(output: str) -> str:
        # Typer draws usage errors in a box and wraps them at 80 columns; strip the
        # box and the wrapping so a message can be matched as one line.
        return " ".join(re.sub(r"[│┌┐└┘─]", " ", output).split())

    bad_level = runner.invoke(
        app, ["checkpoint", "c2", *runs, "--reviewer", "Dana", "--strictness", "R002=huge"]
    )
    assert bad_level.exit_code == 2
    assert "not one of mandatory, desired, optional" in plain(bad_level.output)
    bad_form = runner.invoke(
        app, ["checkpoint", "c2", *runs, "--reviewer", "Dana", "--type", "R002"]
    )
    assert bad_form.exit_code == 2 and "takes ID=value" in plain(bad_form.output)
    unknown = runner.invoke(
        app, ["checkpoint", "c2", *runs, "--reviewer", "Dana", "--reject", "R777"]
    )
    assert unknown.exit_code == 2 and "R777: no such requirement" in plain(unknown.output)
    assert not (tmp_path / "c2" / "checkpoint.json").exists()
    missing = runner.invoke(app, ["checkpoint", "nope", *runs, "--reviewer", "Dana"])
    assert missing.exit_code == 2 and "no run log" in plain(missing.output)
