"""Pipeline graph and CLI (S10) with the five LLM stages stubbed. No network.

Parsing and splitting run for real on Federal Way (the smallest RFP); the stubs return
fixture objects that cite real chunk IDs, so the assembler's citation check passes.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fakes import ScriptedChatModel
from rfp_agent import graph as graph_mod
from rfp_agent.agents.problem import ProblemResult
from rfp_agent.agents.requirements import RequirementsReport
from rfp_agent.agents.risk import Findings, RiskResult
from rfp_agent.agents.solution import CoverageRound, SolutionResult
from rfp_agent.cli import app
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.graph import (
    ASSEMBLE,
    PARSE,
    PARSE_QUALITY,
    PROBLEM,
    REQUIREMENTS,
    RISK,
    SOLUTION,
    SPLIT,
    STAGES,
    PipelineError,
    StageEvent,
    apply_overrides,
    run_pipeline,
    stage_totals,
)
from rfp_agent.llm import MissingApiKeyError
from rfp_agent.parsing import parse_pdf
from rfp_agent.schemas import (
    Claim,
    Coverage,
    Likelihood,
    NodeMetrics,
    ParseQualityReport,
    ProblemStatement,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Risk,
    RiskAssessment,
    RiskSource,
    RunLog,
    Severity,
    Solution,
    SolutionComponent,
    StageRecord,
    StageStatus,
    Strictness,
)
from rfp_agent.splitting import split_document

PDF = DATA_DIR / "rfps" / "federal_way.pdf"
SETTINGS = Settings(_env_file=None, max_structured_retries=1)


@pytest.fixture(scope="module")
def chunk_id() -> str:
    """A real chunk ID of Federal Way, so stub outputs pass the citation check."""
    return split_document(parse_pdf(PDF)).chunks()[0].id


def fixtures(cid: str) -> dict[str, object]:
    reqs = RequirementsOutput(
        requirements=[
            Requirement(
                id="R001",
                text="Provide a hosted portal.",
                type=RequirementType.FUNCTIONAL,
                strictness=Strictness.MANDATORY,
                quote="Provide a hosted portal.",
                chunk_ids=[cid],
            ),
            Requirement(
                id="R002",
                text="Submit five copies.",
                type=RequirementType.SUBMISSION,
                strictness=Strictness.MANDATORY,
                quote="Submit five copies.",
                chunk_ids=[cid],
            ),
        ]
    )
    statement = ProblemStatement(
        client_situation=[Claim(text="Paper process.", chunk_ids=[cid])],
        goal=[Claim(text="A portal.", chunk_ids=[cid])],
        success_criteria=[Claim(text="Go-live.", chunk_ids=[cid])],
        constraints=[Claim(text="Budget.", chunk_ids=[cid])],
    )
    coverage = Coverage(mandatory_total=1, mandatory_covered=1)
    solution = Solution(
        summary="An approach.",
        components=[
            SolutionComponent(
                id="C01",
                title="Portal",
                description="Delivers it.",
                requirement_ids=["R001"],
                claims=[Claim(text="Paper today.", chunk_ids=[cid])],
            )
        ],
        coverage=coverage,
    )
    risks = RiskAssessment(
        risks=[
            Risk(
                id="K01",
                title="Slip",
                description="Could slip.",
                severity=Severity.HIGH,
                likelihood=Likelihood.MEDIUM,
                justification="Tight.",
                source=RiskSource.RFP,
                requirement_ids=["R001"],
                chunk_ids=[cid],
            )
        ]
    )
    return {
        "requirements": reqs,
        "problem": ProblemResult(mode="hierarchical", statement=statement),
        "solution": SolutionResult(
            solution=solution, rounds=[CoverageRound(iteration=1, coverage=coverage)]
        ),
        "risks": RiskResult(assessment=risks, findings=Findings()),
    }


def metric(node: str, cost: float = 0.01) -> NodeMetrics:
    return NodeMetrics(
        node=node,
        model="scripted",
        input_tokens=100,
        output_tokens=10,
        cost_usd=cost,
        latency_s=0.5,
        started_at=datetime.now(UTC),
    )


class Stubs:
    """Replacements for the five LLM stages; records what each received."""

    def __init__(self, cid: str, *, fail_at: str | None = None, barrier: bool = False):
        self.fx = fixtures(cid)
        self.calls: dict[str, dict] = {}
        self.fail_at = fail_at
        self.barrier = threading.Barrier(2, timeout=5) if barrier else None

    def _enter(self, stage: str, **kwargs) -> None:
        self.calls[stage] = kwargs
        if self.fail_at == stage:
            raise RuntimeError(f"{stage} boom")
        if self.barrier is not None and stage in (REQUIREMENTS, PROBLEM):
            self.barrier.wait()  # both branches must be inside at once

    def run_quality_pass(self, parsed, *, model, settings, recorder, config):
        self._enter(PARSE_QUALITY, model=model, settings=settings)
        recorder.record(metric("parse_quality"))
        return parsed.model_copy(update={"flags": []}), ParseQualityReport(judged_pages=[5])

    def extract_requirements(self, split, *, title, model, settings, recorder, config, single_call):
        self._enter(REQUIREMENTS, split=split, title=title, single_call=single_call)
        recorder.record(metric("requirements_extract"))
        recorder.record(metric("requirements_dedupe"))
        return self.fx["requirements"], RequirementsReport(chunks=len(split.chunks()))

    def build_problem_statement(
        self, split, *, title, model, settings, recorder, config, full_text
    ):
        self._enter(PROBLEM, split=split, full_text=full_text)
        recorder.record(metric("problem_synthesis"))
        return self.fx["problem"]

    def build_solution(
        self, requirements, problem, *, title, model, settings, recorder, config, max_iterations
    ):
        self._enter(
            SOLUTION, requirements=requirements, problem=problem, max_iterations=max_iterations
        )
        recorder.record(metric("solution_generate"))
        return self.fx["solution"]

    def build_risks(
        self,
        requirements,
        problem,
        solution,
        *,
        title,
        referenced_documents,
        flags,
        model,
        settings,
        recorder,
        config,
    ):
        self._enter(RISK, solution=solution, flags=list(flags), title=title)
        recorder.record(metric("risk_assess"))
        return self.fx["risks"]

    def install(self, monkeypatch: pytest.MonkeyPatch) -> Stubs:
        for name in (
            "run_quality_pass",
            "extract_requirements",
            "build_problem_statement",
            "build_solution",
            "build_risks",
        ):
            monkeypatch.setattr(graph_mod, name, getattr(self, name))
        return self


def events_of(events: list[StageEvent], status: StageStatus) -> list[str]:
    return [e.stage for e in events if e.status == status]


# --------------------------------------------------------------------------------------
# End to end with stubs
# --------------------------------------------------------------------------------------


def test_run_pipeline_wires_every_stage_and_writes_every_file(tmp_path, monkeypatch, chunk_id):
    stubs = Stubs(chunk_id, barrier=True).install(monkeypatch)
    events: list[StageEvent] = []
    lock = threading.Lock()

    def on_event(e: StageEvent) -> None:
        with lock:
            events.append(e)

    result = run_pipeline(
        PDF,
        settings=SETTINGS,
        model=ScriptedChatModel(),
        runs_dir=tmp_path,
        run_id="t1",
        on_event=on_event,
    )

    # Order: parse, quality, split, then both branches, then solution, risk, assemble.
    finished = [s.stage for s in result.run_log.stages]
    assert finished[:3] == [PARSE, PARSE_QUALITY, SPLIT]
    assert set(finished[3:5]) == {REQUIREMENTS, PROBLEM}
    assert finished[5:] == [SOLUTION, RISK, ASSEMBLE]
    assert all(s.status == StageStatus.FINISHED for s in result.run_log.stages)
    assert all(s.latency_s >= 0 for s in result.run_log.stages)

    # Data flow: the judged document (flags cleared) reaches the risk stage and the
    # summary; both branches saw the same split; solution saw both branch outputs.
    assert stubs.calls[RISK]["flags"] == []
    assert result.summary.flags == []
    assert stubs.calls[REQUIREMENTS]["split"] is stubs.calls[PROBLEM]["split"]
    assert stubs.calls[SOLUTION]["requirements"] is stubs.fx["requirements"]
    assert stubs.calls[SOLUTION]["problem"] is stubs.fx["problem"].statement
    assert stubs.calls[RISK]["solution"] is stubs.fx["solution"].solution
    assert stubs.calls[RISK]["title"] == result.summary.document_title
    assert result.summary.run_id == "t1"
    assert result.summary.model == SETTINGS.model
    assert "\\" not in result.summary.source_path  # posix form on every OS
    assert result.run_log.source_path == result.summary.source_path

    # Events: started and finished once per stage, finished carries the stage's calls.
    assert sorted(events_of(events, StageStatus.STARTED)) == sorted(STAGES)
    assert sorted(events_of(events, StageStatus.FINISHED)) == sorted(STAGES)
    assert not events_of(events, StageStatus.FAILED)
    by_stage = {e.stage: e for e in events if e.status == StageStatus.FINISHED}
    assert by_stage[REQUIREMENTS].calls == 2
    assert by_stage[REQUIREMENTS].totals.cost_usd == pytest.approx(0.02)
    assert by_stage[PROBLEM].calls == 1
    assert by_stage[PARSE].calls == 0
    assert by_stage[PARSE_QUALITY].calls == 1

    # Files: every intermediate, the summary pair and the run log.
    run_dir = tmp_path / "t1"
    assert result.run_dir == run_dir
    expected = {
        "parsed.json",
        "quality.json",
        "split.json",
        "requirements.json",
        "requirements_report.json",
        "problem.json",
        "solution.json",
        "risks.json",
        "summary.json",
        "summary.md",
        "run_log.json",
    }
    assert {p.name for p in run_dir.iterdir()} == expected
    assert set(result.output_paths) == expected - {"run_log.json"}
    log = RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert [s.stage for s in log.stages] == finished
    assert log.finished_at is not None
    assert log.langfuse_trace_url is None
    report = json.loads((run_dir / "requirements_report.json").read_text(encoding="utf-8"))
    assert report["chunks"] == len(result.state["split"].chunks())
    assert "# " in (run_dir / "summary.md").read_text(encoding="utf-8")
    parsed_json = json.loads((run_dir / "parsed.json").read_text(encoding="utf-8"))
    assert parsed_json["flags"] == []  # overwritten by the quality stage


def test_ablation_flags_and_model_override_reach_the_stages(tmp_path, monkeypatch, chunk_id):
    stubs = Stubs(chunk_id).install(monkeypatch)
    result = run_pipeline(
        PDF,
        settings=SETTINGS,
        model=ScriptedChatModel(),
        runs_dir=tmp_path,
        model_spec="deepseek:other",
        full_text_problem=True,
        single_call_extraction=True,
        max_iterations=1,
    )
    assert stubs.calls[REQUIREMENTS]["single_call"] is True
    assert stubs.calls[PROBLEM]["full_text"] is True
    assert stubs.calls[SOLUTION]["max_iterations"] == 1
    assert stubs.calls[PARSE_QUALITY]["settings"].model == "deepseek:other"
    assert result.run_log.model == "deepseek:other"
    assert result.summary.model == "deepseek:other"


def test_defaults_come_from_settings(tmp_path, monkeypatch, chunk_id):
    stubs = Stubs(chunk_id).install(monkeypatch)
    settings = SETTINGS.model_copy(
        update={"single_call_extraction": True, "solution_max_iterations": 2}
    )
    run_pipeline(PDF, settings=settings, model=ScriptedChatModel(), runs_dir=tmp_path)
    assert stubs.calls[REQUIREMENTS]["single_call"] is True
    assert stubs.calls[PROBLEM]["full_text"] is False
    assert stubs.calls[SOLUTION]["max_iterations"] == 2


def test_failed_stage_keeps_log_and_earlier_intermediates(tmp_path, monkeypatch, chunk_id):
    Stubs(chunk_id, fail_at=SOLUTION).install(monkeypatch)
    events: list[StageEvent] = []
    with pytest.raises(PipelineError) as info:
        run_pipeline(
            PDF,
            settings=SETTINGS,
            model=ScriptedChatModel(),
            runs_dir=tmp_path,
            run_id="fail",
            on_event=events.append,
        )
    err = info.value
    assert err.stage == SOLUTION
    assert isinstance(err.cause, RuntimeError)
    assert "solution boom" in str(err)
    run_dir = tmp_path / "fail"
    assert err.run_dir == run_dir
    names = {p.name for p in run_dir.iterdir()}
    assert {"requirements.json", "problem.json", "run_log.json"} <= names
    assert "solution.json" not in names and "summary.json" not in names
    log = RunLog.model_validate_json((run_dir / "run_log.json").read_text(encoding="utf-8"))
    assert log.finished_at is not None
    failed = [s for s in log.stages if s.status == StageStatus.FAILED]
    assert [s.stage for s in failed] == [SOLUTION]
    assert failed[0].error == "RuntimeError: solution boom"
    assert [s.stage for s in log.stages if s.status == StageStatus.FINISHED][-2:] == sorted(
        [REQUIREMENTS, PROBLEM], key=lambda s: [x.stage for x in log.stages].index(s)
    )
    assert events_of(events, StageStatus.FAILED) == [SOLUTION]
    assert RISK not in events_of(events, StageStatus.STARTED)
    assert err.run_log is log or err.run_log.run_id == log.run_id


def test_no_out_dir_writes_nothing(monkeypatch, chunk_id):
    from rfp_agent.observability import RunRecorder

    Stubs(chunk_id).install(monkeypatch)
    recorder = RunRecorder.from_settings(PDF, SETTINGS)
    compiled = graph_mod.build_pipeline(
        settings=SETTINGS, recorder=recorder, model=ScriptedChatModel(), out_dir=None
    )
    state = compiled.invoke({"pdf_path": str(PDF)})
    assert "summary" in state
    assert state.get("output_paths", {}) == {}
    assert not recorder.run_dir.exists()


# --------------------------------------------------------------------------------------
# Helpers and schema
# --------------------------------------------------------------------------------------


def test_stage_totals_group_llm_nodes_by_prefix():
    log = RunLog(
        run_id="x",
        source_path="x.pdf",
        started_at=datetime.now(UTC),
        model="m",
        temperature=0.0,
        nodes=[
            metric("parse_quality", 0.001),
            metric("requirements_extract", 0.01),
            metric("requirements_extract", 0.01),
            metric("requirements_dedupe", 0.005),
            metric("problem_chunk", 0.002),
            metric("problem_synthesis", 0.004),
            metric("solution_generate", 0.03),
            metric("solution_revise", 0.03),
            metric("risk_assess", 0.02),
        ],
    )
    expected = {
        PARSE_QUALITY: (1, 0.001),
        REQUIREMENTS: (3, 0.025),
        PROBLEM: (2, 0.006),
        SOLUTION: (2, 0.06),
        RISK: (1, 0.02),
        PARSE: (0, 0.0),
        ASSEMBLE: (0, 0.0),
    }
    for stage, (calls, cost) in expected.items():
        got_calls, totals = stage_totals(log, stage)
        assert got_calls == calls, stage
        assert totals.cost_usd == pytest.approx(cost), stage
        assert totals.input_tokens == 100 * calls
        assert totals.output_tokens == 10 * calls
        assert totals.latency_s == pytest.approx(0.5 * calls)


def test_apply_overrides_copies_only_when_needed():
    assert apply_overrides(SETTINGS) is SETTINGS
    s = apply_overrides(SETTINGS, model="anthropic:x", full_text_problem=True, max_iterations=5)
    assert s is not SETTINGS
    assert (s.model, s.full_text_problem, s.solution_max_iterations) == ("anthropic:x", True, 5)
    assert s.single_call_extraction is SETTINGS.single_call_extraction
    assert SETTINGS.model != "anthropic:x"


def test_run_log_round_trips_stage_records():
    log = RunLog(
        run_id="x",
        source_path="x.pdf",
        started_at=datetime.now(UTC),
        model="m",
        temperature=0.0,
        stages=[
            StageRecord(
                stage=PARSE,
                status=StageStatus.FINISHED,
                started_at=datetime.now(UTC),
                latency_s=1.5,
            ),
            StageRecord(
                stage=SOLUTION,
                status=StageStatus.FAILED,
                started_at=datetime.now(UTC),
                error="RuntimeError: boom",
            ),
        ],
    )
    again = RunLog.model_validate_json(log.model_dump_json())
    assert again == log
    assert json.loads(log.model_dump_json())["stages"][1]["status"] == "failed"


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def test_cli_run_prints_stages_and_paths(tmp_path, monkeypatch, chunk_id):
    stubs = Stubs(chunk_id).install(monkeypatch)
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda **kw: ScriptedChatModel())
    monkeypatch.setattr(graph_mod, "get_settings", lambda: SETTINGS)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(PDF),
            "--runs-dir",
            str(tmp_path),
            "--run-id",
            "cli",
            "--single-call-extraction",
            "--max-iterations",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert stubs.calls[REQUIREMENTS]["single_call"] is True
    assert stubs.calls[SOLUTION]["max_iterations"] == 1
    out = result.output
    assert "assemble" in out and "finished" in out
    assert "summary.md" in out and "run_log.json" in out
    assert "coverage 1/1 mandatory" in out
    assert (tmp_path / "cli" / "summary.md").exists()


def test_cli_run_reports_failed_stage_with_exit_1(tmp_path, monkeypatch, chunk_id):
    Stubs(chunk_id, fail_at=RISK).install(monkeypatch)
    monkeypatch.setattr(graph_mod, "get_chat_model", lambda **kw: ScriptedChatModel())
    monkeypatch.setattr(graph_mod, "get_settings", lambda: SETTINGS)
    result = CliRunner().invoke(app, ["run", str(PDF), "--runs-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "failed" in result.output and "risk" in result.output
    assert "risk boom" in result.output


def test_cli_missing_key_exits_2(tmp_path, monkeypatch):
    def no_key(**kw):
        raise MissingApiKeyError("DEEPSEEK_API_KEY is not set")

    monkeypatch.setattr(graph_mod, "get_chat_model", no_key)
    monkeypatch.setattr(graph_mod, "get_settings", lambda: SETTINGS)
    result = CliRunner().invoke(app, ["run", str(PDF), "--runs-dir", str(tmp_path)])
    assert result.exit_code == 2
    assert "DEEPSEEK_API_KEY" in result.output
    assert not any(Path(tmp_path).iterdir())


def test_cli_rejects_missing_pdf(tmp_path):
    result = CliRunner().invoke(app, ["run", str(tmp_path / "nope.pdf")])
    assert result.exit_code != 0
