"""Refinement of a run (ST12b): revise, regenerate, sign off, on a real run directory.

Parsing and splitting run for real on Federal Way; the pipeline's LLM stages are the
shared stubs; revisions go through the real revise agents with a scripted model. No
network."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from fakes import ScriptedChatModel, tool_call_msg
from pipeline_stubs import PDF, SETTINGS, Stubs
from rfp_agent import graph as graph_mod
from rfp_agent import refine as refine_mod
from rfp_agent import versions
from rfp_agent.cli import app
from rfp_agent.graph import (
    ASSEMBLE,
    REVISE,
    RISK,
    SOLUTION,
    build_pipeline,
    load_state,
    resume_pipeline,
    run_pipeline,
    stage_totals,
    waiting_checkpoint,
)
from rfp_agent.observability import RunRecorder
from rfp_agent.refine import RefineError, RevisionFailed, regenerate, revise, sign_off
from rfp_agent.schemas import (
    Artefact,
    CheckpointRecord,
    RequirementDecision,
    RevisionKind,
    RevisionStatus,
    RunLog,
    SolutionSummary,
    StageStatus,
)


def record(**overrides) -> CheckpointRecord:
    base = dict(reviewer="Dana", confirmed_at=datetime.now(UTC), decisions=[])
    return CheckpointRecord(**{**base, **overrides})


def paused(tmp_path, monkeypatch, chunk_id, run_id: str = "p1"):
    stubs = Stubs(chunk_id).install(monkeypatch)
    run_pipeline(
        PDF,
        settings=SETTINGS,
        model=ScriptedChatModel(),
        runs_dir=tmp_path,
        run_id=run_id,
        pause_at_checkpoint=True,
    )
    return tmp_path / run_id, stubs


def drafted(tmp_path, monkeypatch, chunk_id, run_id: str = "p1"):
    run_dir, stubs = paused(tmp_path, monkeypatch, chunk_id, run_id)
    resume_pipeline(run_dir, record(), settings=SETTINGS, model=ScriptedChatModel())
    return run_dir, stubs


def log_of(run_dir) -> RunLog:
    return RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))


def summary_of(run_dir) -> SolutionSummary:
    return SolutionSummary.model_validate_json(
        (run_dir / "summary.json").read_text(encoding="utf-8")
    )


def solution_reply(cid: str, *, extra: bool = True) -> dict:
    components = [
        {
            "id": "C01",
            "title": "Portal",
            "description": "Delivers the hosted portal (R001).",
            "requirement_ids": ["R001"],
            "claims": [{"text": "Paper today.", "kind": "fact", "chunk_ids": [cid]}],
        }
    ]
    if extra:
        components.append(
            {
                "title": "Training",
                "description": "Trains staff on the portal (R001).",
                "requirement_ids": ["R001"],
                "claims": [],
            }
        )
    return {"summary": "An approach.", "components": components, "assumptions": []}


def risks_reply(cid: str) -> dict:
    def risk(rid, title, severity):
        out = {
            "title": title,
            "description": "Could happen.",
            "severity": severity,
            "likelihood": "medium",
            "justification": "Because.",
            "source": "rfp",
            "requirement_ids": ["R001"],
            "chunk_ids": [cid],
            "mitigation": "Ask.",
        }
        return {**out, "id": rid} if rid else out

    return {
        "risks": [
            risk("K01", "Slip", "high"),
            risk(None, "Budget", "medium"),
            risk(None, "Staff", "low"),
        ]
    }


def scripted(name: str, args: dict, n: int = 1) -> ScriptedChatModel:
    return ScriptedChatModel(responses=[tool_call_msg(name, args) for _ in range(n)])


# --------------------------------------------------------------------------------------
# Graph pieces
# --------------------------------------------------------------------------------------


def test_build_pipeline_with_an_end_stage_holds_only_the_band():
    recorder = RunRecorder.from_settings("x.pdf", SETTINGS, run_id="g")
    kwargs = dict(settings=SETTINGS, recorder=recorder, model=ScriptedChatModel())
    one = build_pipeline(start_stage=SOLUTION, end_stage=SOLUTION, **kwargs).get_graph()
    assert set(one.nodes) == {"__start__", SOLUTION, "__end__"}
    two = build_pipeline(start_stage=SOLUTION, end_stage=RISK, **kwargs).get_graph()
    assert set(two.nodes) == {"__start__", SOLUTION, RISK, "__end__"}
    alone = build_pipeline(start_stage=ASSEMBLE, end_stage=ASSEMBLE, **kwargs).get_graph()
    assert set(alone.nodes) == {"__start__", ASSEMBLE, "__end__"}
    with pytest.raises(ValueError, match="end_stage"):
        build_pipeline(start_stage=RISK, end_stage=SOLUTION, **kwargs)


def test_load_state_confirmed_prefers_the_confirmed_list(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = paused(tmp_path, monkeypatch, chunk_id)
    resume_pipeline(
        run_dir,
        record(decisions=[RequirementDecision(requirement_id="R002", action="reject")]),
        settings=SETTINGS,
        model=ScriptedChatModel(),
    )
    assert load_state(run_dir)["requirements"].requirement_ids() == ["R001", "R002"]
    assert load_state(run_dir, confirmed=True)["requirements"].requirement_ids() == ["R001"]


# --------------------------------------------------------------------------------------
# Revise
# --------------------------------------------------------------------------------------


def test_revise_solution_versions_it_marks_risks_stale_and_reassembles(
    tmp_path, monkeypatch, chunk_id
):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id)
    original = (run_dir / "solution.json").read_bytes()
    events: list = []
    result = revise(
        run_dir,
        Artefact.SOLUTION,
        reviewer="Dana",
        instruction="Add a training component.",
        settings=SETTINGS,
        model=scripted("SolutionDraft", solution_reply(chunk_id)),
        on_event=events.append,
    )
    rec = result.record
    assert (rec.id, rec.kind, rec.from_version, rec.to_version) == (
        "V01",
        RevisionKind.REVISE,
        1,
        2,
    )
    assert rec.diff.added == ["components[C02]"]
    assert rec.made_stale == [Artefact.RISKS]
    assert rec.calls == 1 and rec.cost_usd >= 0
    assert (run_dir / "solution.v1.json").read_bytes() == original
    assert (run_dir / "solution.v2.json").read_bytes() == (run_dir / "solution.json").read_bytes()
    state = versions.load_version_state(run_dir)
    assert state.artefacts[Artefact.SOLUTION].version == 2
    assert state.artefacts[Artefact.RISKS].stale
    summary = summary_of(run_dir)
    assert [c.id for c in summary.solution.components] == ["C01", "C02"]
    assert [r.id for r in summary.review.revisions] == ["V01"]
    md = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "### Revisions" in md and "**V01** revise solution by Dana" in md
    log = log_of(run_dir)
    assert [s.stage for s in log.stages[-2:]] == [REVISE, ASSEMBLE]
    assert log.finished_at is not None
    assert log.nodes[-1].node == "revise_solution"
    assert stage_totals(log, REVISE)[0] == 1
    assert [(e.stage, e.status) for e in events][:2] == [
        (REVISE, StageStatus.STARTED),
        (REVISE, StageStatus.FINISHED),
    ]


def test_revise_requirements_while_waiting_edits_the_confirmed_copy_only(
    tmp_path, monkeypatch, chunk_id
):
    run_dir, _ = paused(tmp_path, monkeypatch, chunk_id)
    extracted = (run_dir / "requirements.json").read_bytes()
    patch = {"edits": [{"id": "R001", "text": "Provide a hosted, accessible portal."}]}
    result = revise(
        run_dir,
        Artefact.REQUIREMENTS,
        reviewer="Dana",
        instruction="Say the portal must be accessible.",
        settings=SETTINGS,
        model=scripted("RequirementsPatch", patch),
    )
    assert result.summary is None
    assert (run_dir / "requirements.json").read_bytes() == extracted
    assert (run_dir / "requirements_confirmed.v1.json").read_bytes() == extracted
    assert not (run_dir / "summary.json").exists()
    log = log_of(run_dir)
    assert log.finished_at is None and waiting_checkpoint(log) is not None
    # Nothing is drafted yet, so nothing can be stale (seen live on Missouri: the risks
    # drafted after the checkpoint were flagged stale by a revision made before them).
    assert result.record.made_stale == []
    assert versions.stale_artefacts(versions.load_version_state(run_dir)) == []

    # The checkpoint applies its decisions on top of the revised list, and versions it.
    resumed = resume_pipeline(
        run_dir,
        record(decisions=[RequirementDecision(requirement_id="R002", strictness="desired")]),
        settings=SETTINGS,
        model=ScriptedChatModel(),
    )
    reqs = {r.id: r for r in resumed.summary.requirements.requirements}
    assert reqs["R001"].text == "Provide a hosted, accessible portal."
    assert reqs["R002"].strictness.value == "desired"
    assert versions.load_version_state(run_dir).artefacts[Artefact.REQUIREMENTS].version == 3
    assert [r.id for r in resumed.summary.review.revisions] == ["V01"]


def test_requirement_removal_strips_downstream_and_keeps_citations_valid(
    tmp_path, monkeypatch, chunk_id
):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id)
    result = revise(
        run_dir,
        Artefact.REQUIREMENTS,
        reviewer="Dana",
        instruction="R001 is not an obligation; remove it.",
        settings=SETTINGS,
        model=scripted("RequirementsPatch", {"removals": ["R001"]}),
    )
    summary = result.summary
    assert summary.requirements.requirement_ids() == ["R002"]
    assert summary.solution.components[0].requirement_ids == []
    assert summary.solution.coverage.mandatory_total == 0
    assert summary.risks.risks[0].requirement_ids == []
    state = versions.load_version_state(run_dir)
    assert state.artefacts[Artefact.SOLUTION].stale and state.artefacts[Artefact.RISKS].stale
    assert result.record.made_stale == [Artefact.SOLUTION, Artefact.RISKS]


def test_failed_revision_is_recorded_and_changes_nothing(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id)
    before = (run_dir / "solution.json").read_bytes()
    stages_before = len(log_of(run_dir).stages)
    bad = solution_reply(chunk_id) | {"components": []}
    with pytest.raises(RevisionFailed) as err:
        revise(
            run_dir,
            Artefact.SOLUTION,
            reviewer="Dana",
            instruction="Remove everything.",
            settings=SETTINGS,
            model=scripted("SolutionDraft", bad, n=2),
        )
    assert err.value.record.status is RevisionStatus.FAILED
    assert (run_dir / "solution.json").read_bytes() == before
    assert not (run_dir / "current.json").exists()
    assert [r.status for r in versions.load_revisions(run_dir).revisions] == [RevisionStatus.FAILED]
    log = log_of(run_dir)
    assert len(log.stages) == stages_before  # no failed stage on the run
    assert log.nodes[-1].node == "revise_solution"


def test_no_change_records_a_revision_without_a_version(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id)
    result = revise(
        run_dir,
        Artefact.REQUIREMENTS,
        reviewer="Dana",
        instruction="Add a requirement for something the RFP never says.",
        settings=SETTINGS,
        model=scripted("RequirementsPatch", {}),
    )
    assert result.record.diff.empty
    assert result.record.from_version == result.record.to_version == 1
    assert not (run_dir / "requirements_confirmed.v2.json").exists()


def test_solution_cannot_be_revised_while_waiting(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = paused(tmp_path, monkeypatch, chunk_id)
    with pytest.raises(RefineError, match="waiting at the checkpoint"):
        revise(
            run_dir,
            Artefact.SOLUTION,
            reviewer="Dana",
            instruction="x",
            settings=SETTINGS,
            model=ScriptedChatModel(),
        )


# --------------------------------------------------------------------------------------
# Regenerate and sign off
# --------------------------------------------------------------------------------------


def test_regenerate_risk_runs_the_risk_stage_alone(tmp_path, monkeypatch, chunk_id):
    run_dir, stubs = drafted(tmp_path, monkeypatch, chunk_id)
    stubs.calls.clear()
    result = regenerate(
        run_dir, RISK, reviewer="Dana", settings=SETTINGS, model=ScriptedChatModel()
    )
    assert set(stubs.calls) == {RISK}
    assert result.record.kind is RevisionKind.REGENERATE
    assert (result.record.from_version, result.record.to_version) == (1, 2)
    assert (run_dir / "risks.v2.json").is_file()
    assert result.summary is not None


def test_regenerate_solution_keeps_a_prior_risk_revision(tmp_path, monkeypatch, chunk_id):
    run_dir, stubs = drafted(tmp_path, monkeypatch, chunk_id)
    revise(
        run_dir,
        Artefact.RISKS,
        reviewer="Dana",
        instruction="Add budget and staffing risks.",
        settings=SETTINGS,
        model=scripted("RiskAssessmentDraft", risks_reply(chunk_id)),
    )
    revised = (run_dir / "risks.json").read_bytes()
    stubs.calls.clear()
    regenerate(run_dir, SOLUTION, reviewer="Dana", settings=SETTINGS, model=ScriptedChatModel())
    assert set(stubs.calls) == {SOLUTION}
    assert (run_dir / "risks.json").read_bytes() == revised
    state = versions.load_version_state(run_dir)
    assert state.artefacts[Artefact.RISKS].stale
    assert len(summary_of(run_dir).risks.risks) == 3


def test_sign_off_refuses_while_stale_then_freezes(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id)
    revise(
        run_dir,
        Artefact.SOLUTION,
        reviewer="Dana",
        instruction="Add training.",
        settings=SETTINGS,
        model=scripted("SolutionDraft", solution_reply(chunk_id)),
    )
    with pytest.raises(RefineError, match=r"stale artefacts: risks \(solution changed in V01"):
        sign_off(run_dir, reviewer="Lee", settings=SETTINGS)
    regenerate(run_dir, RISK, reviewer="Dana", settings=SETTINGS, model=ScriptedChatModel())
    result = sign_off(run_dir, reviewer="Lee", note="Gold team done.", settings=SETTINGS)
    so = result.versions.signed_off
    assert so.reviewer == "Lee" and so.versions[Artefact.SOLUTION] == 2
    md = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "- **Signed off:** by Lee" in md and "### Sign-off" in md
    assert [r.kind for r in summary_of(run_dir).review.revisions] == [
        RevisionKind.REVISE,
        RevisionKind.REGENERATE,
        RevisionKind.SIGN_OFF,
    ]
    with pytest.raises(RefineError, match="signed off"):
        revise(
            run_dir,
            Artefact.PROBLEM,
            reviewer="Dana",
            instruction="x",
            settings=SETTINGS,
            model=ScriptedChatModel(),
        )
    with pytest.raises(RefineError, match="signed off"):
        regenerate(run_dir, RISK, reviewer="Dana", settings=SETTINGS, model=ScriptedChatModel())


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def plain(output: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", output)
    text = re.sub(r"[─-╿]", " ", text)
    return " ".join(text.split())


def test_cli_revise_regenerate_sign_off_history_round_trip(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id, run_id="c1")
    model = scripted("SolutionDraft", solution_reply(chunk_id))
    monkeypatch.setattr(refine_mod, "get_chat_model", lambda **kw: model)
    monkeypatch.setattr(refine_mod, "get_settings", lambda: SETTINGS)
    runner = CliRunner()
    runs = ["--runs-dir", str(tmp_path)]
    instruction = tmp_path / "ask.md"
    instruction.write_text("Add a training component.", encoding="utf-8")

    out = runner.invoke(
        app,
        [
            "revise",
            "c1",
            "solution",
            "--reviewer",
            "Dana",
            "--instruction-file",
            str(instruction),
            *runs,
        ],
    )
    assert out.exit_code == 0, out.output
    text = plain(out.output)
    assert "+ components[C02]" in text and "solution v1 -> v2" in text and "stale: risks" in text

    out = runner.invoke(app, ["sign-off", "c1", "--reviewer", "Lee", *runs])
    assert out.exit_code == 2 and "stale artefacts" in plain(out.output)

    monkeypatch.setattr(refine_mod, "get_chat_model", lambda **kw: ScriptedChatModel())
    out = runner.invoke(app, ["regenerate", "c1", "risk", "--reviewer", "Dana", *runs])
    assert out.exit_code == 0, out.output
    out = runner.invoke(app, ["sign-off", "c1", "--reviewer", "Lee", *runs])
    assert out.exit_code == 0, out.output
    assert "signed off by Lee" in plain(out.output)

    out = runner.invoke(app, ["history", "c1", *runs])
    assert out.exit_code == 0, out.output
    text = plain(out.output)
    assert all(v in text for v in ("V01", "V02", "V03", "sign_off", "Add a training component."))
    revisions = json.loads((run_dir / "revisions.json").read_text(encoding="utf-8"))
    assert len(revisions["revisions"]) == 3


def test_cli_refine_exit_codes(tmp_path, monkeypatch, chunk_id):
    run_dir, _ = drafted(tmp_path, monkeypatch, chunk_id, run_id="c2")
    bad = solution_reply(chunk_id) | {"components": []}
    monkeypatch.setattr(
        refine_mod, "get_chat_model", lambda **kw: scripted("SolutionDraft", bad, n=2)
    )
    monkeypatch.setattr(refine_mod, "get_settings", lambda: SETTINGS)
    runner = CliRunner()
    runs = ["--runs-dir", str(tmp_path)]
    base = ["revise", "c2", "solution", "--reviewer", "Dana", *runs]

    both = runner.invoke(app, [*base, "--instruction", "x", "--instruction-file", str(PDF)])
    assert both.exit_code == 2 and "exactly one of" in plain(both.output)
    neither = runner.invoke(app, base)
    assert neither.exit_code == 2
    wrong = runner.invoke(
        app, ["revise", "c2", "budget", "--reviewer", "Dana", "--instruction", "x", *runs]
    )
    assert wrong.exit_code == 2 and "artefact must be one of" in plain(wrong.output)
    missing = runner.invoke(
        app, ["revise", "nope", "solution", "--reviewer", "D", "--instruction", "x", *runs]
    )
    assert missing.exit_code == 2 and "has no run log" in plain(missing.output)
    failed = runner.invoke(app, [*base, "--instruction", "Remove everything."])
    assert failed.exit_code == 1 and "V01 failed" in plain(failed.output)
    regen = runner.invoke(app, ["regenerate", "c2", "problem", "--reviewer", "Dana", *runs])
    assert regen.exit_code == 2 and "can be regenerated" in plain(regen.output)
    assert graph_mod.CHECKPOINT  # the graph module stays imported for the stubs
