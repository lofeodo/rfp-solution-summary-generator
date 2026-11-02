"""The pipeline as one LangGraph graph (S10).

    parse -> parse_quality -> split -> (requirements || problem) -> solution -> risk -> assemble

Every stage is an existing function from S2 to S9; this module only wires them, times
them and reports on them. Each node is wrapped so that it

- emits a ``StageEvent`` (``started``, ``finished`` or ``failed``) to an optional
  callback, which the CLI prints and the UI (S14) streams; the two parallel branches run
  on executor threads, so the callback must be thread-safe (a queue or a console lock);
- records a ``StageRecord`` (wall time, outcome) on the run recorder, next to the
  per-call ``NodeMetrics`` that ``structured_call`` records; the LLM calls of a stage are
  the nodes whose name starts with the stage's prefix (``STAGE_NODE_PREFIXES``);
- writes the stage's output as JSON into the run directory as soon as it finishes, so a
  failed run keeps every earlier intermediate and the UI can serve them.

Runtime objects (settings, model, recorder, callback) are bound in closures by
``build_pipeline``; the graph state holds only the documents and results. The S7
revision loop stays a function call: ``build_solution`` runs its own compiled graph with
the same ``config``, so tracing nests it under this run.

The checkpoint (ST12). After ``requirements`` and ``problem`` join, a ``checkpoint`` node
either passes through (unattended) or records a ``waiting`` stage and routes to ``END``,
so the run stops with every read-stage file on disk and the worker free. ``resume_pipeline``
reloads those files into the state (``load_state``), applies the reviewer's record
(``apply_checkpoint``), continues the same run log and invokes the graph from
``solution``. No checkpointer: the run directory already is one (D43).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from operator import or_
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from rfp_agent.agents.problem import ProblemResult, build_problem_statement
from rfp_agent.agents.requirements import RequirementsReport, extract_requirements
from rfp_agent.agents.risk import RiskResult, build_risks
from rfp_agent.agents.solution import SolutionResult, build_solution
from rfp_agent.checkpoint import (
    CHECKPOINT_FILENAME,
    CONFIRMED_REQUIREMENTS_FILENAME,
    apply_checkpoint,
)
from rfp_agent.config import RUNS_DIR, Settings, get_settings
from rfp_agent.llm import get_chat_model
from rfp_agent.observability import (
    RUN_LOG_FILENAME,
    RunRecorder,
    langfuse_trace_url,
    make_langfuse_handler,
    shutdown_langfuse,
)
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.quality import run_quality_pass
from rfp_agent.render import assemble, write_summary
from rfp_agent.schemas import (
    Brief,
    CheckpointRecord,
    ParsedDocument,
    ParseQualityReport,
    RequirementsOutput,
    ReviewHistory,
    RunLog,
    RunTotals,
    SolutionSummary,
    SplitDocument,
    StageRecord,
    StageStatus,
    StrictModel,
)
from rfp_agent.splitting import split_document

logger = logging.getLogger(__name__)

# Stage (graph node) names, in pipeline order. ``requirements`` and ``problem`` run in
# parallel after ``split``.
PARSE = "parse"
PARSE_QUALITY = "parse_quality"
SPLIT = "split"
REQUIREMENTS = "requirements"
PROBLEM = "problem"
SOLUTION = "solution"
RISK = "risk"
ASSEMBLE = "assemble"
STAGES: tuple[str, ...] = (
    PARSE,
    PARSE_QUALITY,
    SPLIT,
    REQUIREMENTS,
    PROBLEM,
    SOLUTION,
    RISK,
    ASSEMBLE,
)
# The human touchpoint between the read stages and the draft stages (ST12). Not in
# ``STAGES``: it is a graph node, but not a stage of the machine's work.
CHECKPOINT = "checkpoint"

# Position of each node in the pipeline; equal positions run in parallel. A graph built
# with ``start_stage`` holds only the nodes at or after that position.
_ORDER: dict[str, int] = {
    PARSE: 0,
    PARSE_QUALITY: 1,
    SPLIT: 2,
    REQUIREMENTS: 3,
    PROBLEM: 3,
    CHECKPOINT: 4,
    SOLUTION: 5,
    RISK: 6,
    ASSEMBLE: 7,
}
START_STAGES: tuple[str, ...] = (PARSE, SPLIT, REQUIREMENTS, SOLUTION, RISK, ASSEMBLE)

# LLM node names (``NodeMetrics.node``) that belong to each stage, by prefix.
STAGE_NODE_PREFIXES: dict[str, tuple[str, ...]] = {
    PARSE_QUALITY: ("parse_quality",),
    REQUIREMENTS: ("requirements_",),
    PROBLEM: ("problem_",),
    SOLUTION: ("solution_",),
    RISK: ("risk_",),
}

# Intermediate files written into the run directory: stage -> (state key, file name).
STAGE_FILES: dict[str, tuple[tuple[str, str], ...]] = {
    PARSE: (("parsed", "parsed.json"),),
    PARSE_QUALITY: (("parsed", "parsed.json"), ("quality_report", "quality.json")),
    SPLIT: (("split", "split.json"),),
    REQUIREMENTS: (
        ("requirements", "requirements.json"),
        ("requirements_report", "requirements_report.json"),
    ),
    PROBLEM: (("problem", "problem.json"),),
    SOLUTION: (("solution", "solution.json"),),
    RISK: (("risks", "risks.json"),),
    CHECKPOINT: (
        ("checkpoint", CHECKPOINT_FILENAME),
        ("requirements", CONFIRMED_REQUIREMENTS_FILENAME),
    ),
}

# How each state key is read back from its file (``load_state``). ``requirements`` is
# the extractor's output; the confirmed list is applied by ``resume_pipeline``.
_STATE_MODELS: dict[str, Callable[[str], Any]] = {
    "parsed": ParsedDocument.model_validate_json,
    "quality_report": ParseQualityReport.model_validate_json,
    "split": SplitDocument.model_validate_json,
    "requirements": RequirementsOutput.model_validate_json,
    "requirements_report": lambda text: RequirementsReport(**json.loads(text)),
    "problem": ProblemResult.model_validate_json,
    "solution": SolutionResult.model_validate_json,
    "risks": RiskResult.model_validate_json,
    "checkpoint": CheckpointRecord.model_validate_json,
}

ERROR_TEXT_LIMIT = 2000


class PipelineState(TypedDict, total=False):
    pdf_path: str
    parsed: ParsedDocument
    quality_report: ParseQualityReport
    split: SplitDocument
    requirements: RequirementsOutput
    requirements_report: RequirementsReport
    problem: ProblemResult
    checkpoint: CheckpointRecord  # set by resume_pipeline (ST12)
    paused_at: str  # set by the checkpoint node when the run stops there
    solution: SolutionResult
    risks: RiskResult
    summary: SolutionSummary
    output_paths: Annotated[dict[str, str], or_]  # merged: parallel stages both add paths


class StageEvent(StrictModel):
    """Progress of one stage, for the CLI and the UI. ``calls`` and ``totals`` cover the
    LLM calls recorded for the stage so far (all of them on ``finished``)."""

    stage: str
    status: StageStatus
    started_at: datetime
    latency_s: float = 0.0
    calls: int = 0
    totals: RunTotals = RunTotals()
    error: str | None = None


EventCallback = Callable[[StageEvent], None]


class PipelineError(RuntimeError):
    """A stage failed. Carries the stage, the run log (already written) and the run
    directory so a caller can report what was spent and what was kept."""

    def __init__(self, stage: str, run_log: RunLog, run_dir: Path, cause: BaseException):
        super().__init__(f"stage {stage!r} failed: {type(cause).__name__}: {cause}")
        self.stage = stage
        self.run_log = run_log
        self.run_dir = run_dir
        self.cause = cause


class PipelineStateError(RuntimeError):
    """A resume was asked of a run directory that is not waiting at the checkpoint."""


@dataclass
class PipelineResult:
    summary: SolutionSummary | None
    run_log: RunLog
    run_dir: Path
    state: PipelineState
    paused_at: str | None = None  # the node the run stopped at (``CHECKPOINT``) or None

    @property
    def output_paths(self) -> dict[str, str]:
        return dict(self.state.get("output_paths", {}))

    @property
    def paused(self) -> bool:
        return self.paused_at is not None


# --------------------------------------------------------------------------------------
# Per-stage metrics and files
# --------------------------------------------------------------------------------------


def stage_totals(log: RunLog, stage: str) -> tuple[int, RunTotals]:
    """``(calls, totals)`` of the LLM calls that belong to ``stage``."""
    prefixes = STAGE_NODE_PREFIXES.get(stage, ())
    totals = RunTotals()
    calls = 0
    for n in log.nodes:
        if not n.node.startswith(prefixes):
            continue
        calls += 1
        totals.input_tokens += n.input_tokens
        totals.output_tokens += n.output_tokens
        totals.cached_input_tokens += n.cached_input_tokens
        totals.cost_usd += n.cost_usd
        totals.latency_s += n.latency_s
        totals.retries += n.retries
    return calls, totals


def _to_json(obj: Any) -> str:
    if isinstance(obj, BaseModel):
        return obj.model_dump_json(indent=2) + "\n"
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return json.dumps(dataclasses.asdict(obj), indent=2) + "\n"
    return json.dumps(obj, indent=2, default=str) + "\n"


def write_stage_files(stage: str, updates: dict[str, Any], out_dir: Path) -> dict[str, str]:
    """Write the stage's outputs from ``updates`` into ``out_dir``; return name -> path."""
    written: dict[str, str] = {}
    for key, filename in STAGE_FILES.get(stage, ()):
        if key not in updates:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(_to_json(updates[key]), encoding="utf-8", newline="\n")
        written[filename] = str(path)
    return written


def load_state(run_dir: Path) -> PipelineState:
    """Read a run directory's stage files back into a ``PipelineState`` (ST12).

    Every file a stage wrote is loaded; missing files are skipped, so the state holds
    exactly what the run got to. ``requirements`` is the extractor's output
    (``requirements.json``); the confirmed list, if any, is applied by the caller.
    """
    run_dir = Path(run_dir)
    state: PipelineState = {}
    paths: dict[str, str] = {}
    for stage, files in STAGE_FILES.items():
        for key, filename in files:
            if stage == CHECKPOINT and key == "requirements":
                continue
            path = run_dir / filename
            if not path.is_file() or key in state:
                continue
            loaded = _STATE_MODELS[key](path.read_text(encoding="utf-8"))
            state[key] = loaded  # type: ignore[literal-required]
            paths[filename] = str(path)
    if "parsed" in state:
        state["pdf_path"] = state["parsed"].source_path
    if paths:
        state["output_paths"] = paths
    return state


def waiting_checkpoint(log: RunLog) -> StageRecord | None:
    """The ``waiting`` checkpoint record of a paused run, or ``None``."""
    for s in reversed(log.stages):
        if s.stage == CHECKPOINT:
            return s if s.status == StageStatus.WAITING else None
    return None


# --------------------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------------------

StageFn = Callable[[PipelineState, RunnableConfig], dict[str, Any]]


def build_pipeline(
    *,
    settings: Settings,
    recorder: RunRecorder,
    model: BaseChatModel,
    out_dir: Path | None = None,
    on_event: EventCallback | None = None,
    start_stage: str = PARSE,
    pause_at_checkpoint: bool = False,
):
    """Compile the pipeline graph with its runtime objects bound.

    ``out_dir`` receives each stage's JSON as it finishes (``None`` writes nothing;
    the final ``summary.json`` and ``summary.md`` are written only when it is set).
    ``start_stage`` (one of ``START_STAGES``) builds only the nodes from that stage on,
    for a resumed run whose earlier state comes from ``load_state``.
    ``pause_at_checkpoint`` makes the checkpoint node stop the run (ST12).
    """
    if start_stage not in START_STAGES:
        raise ValueError(f"start_stage must be one of {START_STAGES}, not {start_stage!r}")
    first = _ORDER[start_stage]

    def included(name: str) -> bool:
        return _ORDER[name] >= first

    def title_of(state: PipelineState) -> str:
        return state["parsed"].title or Path(state["pdf_path"]).name

    def brief_of(state: PipelineState) -> Brief | None:
        record = state.get("checkpoint")
        return record.brief if record is not None else None

    def emit(event: StageEvent) -> None:
        if on_event is not None:
            on_event(event)

    def stage(name: str, fn: StageFn):
        def node(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
            started_at = datetime.now(UTC)
            t0 = time.perf_counter()
            emit(StageEvent(stage=name, status=StageStatus.STARTED, started_at=started_at))
            try:
                updates = fn(state, config)
            except Exception as exc:
                latency = time.perf_counter() - t0
                error = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
                recorder.record_stage(
                    StageRecord(
                        stage=name,
                        status=StageStatus.FAILED,
                        started_at=started_at,
                        latency_s=latency,
                        error=error,
                    )
                )
                calls, totals = stage_totals(recorder.log, name)
                emit(
                    StageEvent(
                        stage=name,
                        status=StageStatus.FAILED,
                        started_at=started_at,
                        latency_s=latency,
                        calls=calls,
                        totals=totals,
                        error=error,
                    )
                )
                raise
            paths = write_stage_files(name, updates, out_dir) if out_dir is not None else {}
            if paths:
                updates = {**updates, "output_paths": {**updates.get("output_paths", {}), **paths}}
            latency = time.perf_counter() - t0
            recorder.record_stage(
                StageRecord(
                    stage=name,
                    status=StageStatus.FINISHED,
                    started_at=started_at,
                    latency_s=latency,
                )
            )
            calls, totals = stage_totals(recorder.log, name)
            emit(
                StageEvent(
                    stage=name,
                    status=StageStatus.FINISHED,
                    started_at=started_at,
                    latency_s=latency,
                    calls=calls,
                    totals=totals,
                )
            )
            return updates

        node.__name__ = name
        return node

    def parse(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        parsed = parse_pdf(state["pdf_path"])
        # parse_pdf stringifies a Path, which uses backslashes on Windows; keep the
        # posix form the run was started with so every output reads the same on any OS.
        return {"parsed": parsed.model_copy(update={"source_path": state["pdf_path"]})}

    def parse_quality(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        parsed, report = run_quality_pass(
            state["parsed"], model=model, settings=settings, recorder=recorder, config=config
        )
        return {"parsed": parsed, "quality_report": report}

    def split(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        return {"split": split_document(state["parsed"])}

    def requirements(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        output, report = extract_requirements(
            state["split"],
            title=title_of(state),
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
            single_call=settings.single_call_extraction,
        )
        return {"requirements": output, "requirements_report": report}

    def problem(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        result = build_problem_statement(
            state["split"],
            title=title_of(state),
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
            full_text=settings.full_text_problem,
        )
        return {"problem": result}

    def checkpoint(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        """Unattended: pass through, record nothing. Attended: record that the run is
        waiting and stop; ``resume_pipeline`` closes the record."""
        if not pause_at_checkpoint:
            return {}
        started_at = datetime.now(UTC)
        recorder.record_stage(
            StageRecord(stage=CHECKPOINT, status=StageStatus.WAITING, started_at=started_at)
        )
        emit(StageEvent(stage=CHECKPOINT, status=StageStatus.WAITING, started_at=started_at))
        return {"paused_at": CHECKPOINT}

    def after_checkpoint(state: PipelineState) -> str:
        return END if state.get("paused_at") else SOLUTION

    def solution(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        result = build_solution(
            state["requirements"],
            state["problem"].statement,
            title=title_of(state),
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
            max_iterations=settings.solution_max_iterations,
            brief=brief_of(state),
        )
        return {"solution": result}

    def risk(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        parsed = state["parsed"]
        result = build_risks(
            state["requirements"],
            state["problem"].statement,
            state["solution"].solution,
            title=title_of(state),
            referenced_documents=parsed.referenced_documents,
            flags=parsed.flags,
            model=model,
            settings=settings,
            recorder=recorder,
            config=config,
            brief=brief_of(state),
        )
        return {"risks": result}

    def assemble_stage(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
        record = state.get("checkpoint")
        summary = assemble(
            run_id=recorder.run_id,
            model=settings.model,
            parsed=state["parsed"],
            split=state["split"],
            requirements=state["requirements"],
            problem_statement=state["problem"].statement,
            solution=state["solution"].solution,
            risks=state["risks"].assessment,
            strict=True,
            brief=brief_of(state),
            review=ReviewHistory(checkpoint=record) if record is not None else None,
        )
        updates: dict[str, Any] = {"summary": summary}
        if out_dir is not None:
            json_path, md_path = write_summary(summary, out_dir)
            updates["output_paths"] = {json_path.name: str(json_path), md_path.name: str(md_path)}
        return updates

    nodes: dict[str, Callable[..., dict[str, Any]]] = {
        PARSE: stage(PARSE, parse),
        PARSE_QUALITY: stage(PARSE_QUALITY, parse_quality),
        SPLIT: stage(SPLIT, split),
        REQUIREMENTS: stage(REQUIREMENTS, requirements),
        PROBLEM: stage(PROBLEM, problem),
        CHECKPOINT: checkpoint,
        SOLUTION: stage(SOLUTION, solution),
        RISK: stage(RISK, risk),
        ASSEMBLE: stage(ASSEMBLE, assemble_stage),
    }
    edges: list[tuple[str, str]] = [
        (PARSE, PARSE_QUALITY),
        (PARSE_QUALITY, SPLIT),
        (SPLIT, REQUIREMENTS),
        (SPLIT, PROBLEM),
        (SOLUTION, RISK),
        (RISK, ASSEMBLE),
    ]
    graph: StateGraph = StateGraph(PipelineState)
    for name, fn in nodes.items():
        if included(name):
            graph.add_node(name, fn)
    for name in nodes:
        if _ORDER[name] == first:
            graph.add_edge(START, name)
    for source, target in edges:
        if included(source):
            graph.add_edge(source, target)
    if included(REQUIREMENTS):
        graph.add_edge([REQUIREMENTS, PROBLEM], CHECKPOINT)
    if included(CHECKPOINT):
        graph.add_conditional_edges(CHECKPOINT, after_checkpoint, {END: END, SOLUTION: SOLUTION})
    graph.add_edge(ASSEMBLE, END)
    return graph.compile()


# --------------------------------------------------------------------------------------
# One run, end to end
# --------------------------------------------------------------------------------------


def apply_overrides(
    settings: Settings,
    *,
    model: str | None = None,
    full_text_problem: bool | None = None,
    single_call_extraction: bool | None = None,
    max_iterations: int | None = None,
) -> Settings:
    """A copy of ``settings`` with the CLI's per-run overrides applied."""
    updates: dict[str, Any] = {}
    if model is not None:
        updates["model"] = model
    if full_text_problem is not None:
        updates["full_text_problem"] = full_text_problem
    if single_call_extraction is not None:
        updates["single_call_extraction"] = single_call_extraction
    if max_iterations is not None:
        updates["solution_max_iterations"] = max_iterations
    return settings.model_copy(update=updates) if updates else settings


def run_pipeline(
    pdf: str | Path,
    *,
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
    runs_dir: Path | None = None,
    run_id: str | None = None,
    model_spec: str | None = None,
    full_text_problem: bool | None = None,
    single_call_extraction: bool | None = None,
    max_iterations: int | None = None,
    on_event: EventCallback | None = None,
    pause_at_checkpoint: bool = False,
) -> PipelineResult:
    """Run the whole pipeline on one PDF and write everything under
    ``<runs_dir>/<run_id>/``: every intermediate, ``summary.json``, ``summary.md`` and
    ``run_log.json`` (the log is written even when a stage fails).

    With ``pause_at_checkpoint`` the run stops after the read stages (ST12): the result
    has ``paused_at == CHECKPOINT`` and no summary, and ``resume_pipeline`` finishes it.

    Raises ``PipelineError`` when a stage fails; ``MissingApiKeyError`` propagates from
    the model factory before anything is written.
    """
    settings = apply_overrides(
        settings or get_settings(),
        model=model_spec,
        full_text_problem=full_text_problem,
        single_call_extraction=single_call_extraction,
        max_iterations=max_iterations,
    )
    # Forward slashes whatever the OS, so run logs and samples read the same everywhere.
    pdf_path = Path(pdf).as_posix()
    if model is None:
        model = get_chat_model(settings=settings)
    recorder = RunRecorder.from_settings(
        pdf_path, settings, run_id=run_id, runs_dir=runs_dir or RUNS_DIR
    )
    return _invoke(
        {"pdf_path": pdf_path},
        settings=settings,
        recorder=recorder,
        model=model,
        on_event=on_event,
        start_stage=PARSE,
        pause_at_checkpoint=pause_at_checkpoint,
    )


def resume_pipeline(
    run_dir: str | Path,
    record: CheckpointRecord,
    *,
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
    model_spec: str | None = None,
    max_iterations: int | None = None,
    on_event: EventCallback | None = None,
) -> PipelineResult:
    """Confirm the checkpoint of a paused run and draft the rest (ST12).

    Reloads the read-stage files and the run log from ``run_dir``, applies ``record``
    (``apply_checkpoint``; a bad record raises ``CheckpointError`` before anything is
    written), writes ``checkpoint.json`` and ``requirements_confirmed.json``, closes the
    ``waiting`` checkpoint record with the time the run waited, and invokes the graph
    from ``solution`` on the same run log, so totals accumulate across the pause.

    Raises ``PipelineStateError`` when the directory holds no run waiting at the
    checkpoint.
    """
    run_dir = Path(run_dir)
    log_path = run_dir / RUN_LOG_FILENAME
    if not log_path.is_file():
        raise PipelineStateError(f"{run_dir} has no run log")
    log = RunLog.model_validate_json(log_path.read_text(encoding="utf-8"))
    waiting = waiting_checkpoint(log)
    if waiting is None:
        raise PipelineStateError(f"run {log.run_id} is not waiting at the checkpoint")
    state = load_state(run_dir)
    for key in ("parsed", "split", "requirements", "problem"):
        if key not in state:
            raise PipelineStateError(f"run {log.run_id} has no {key} to resume from")

    settings = apply_overrides(
        settings or get_settings(), model=model_spec, max_iterations=max_iterations
    )
    if model is None:
        model = get_chat_model(settings=settings)
    confirmed = apply_checkpoint(state["requirements"], record)
    now = datetime.now(UTC)
    waited = max(0.0, (now - waiting.started_at).total_seconds())
    record = record.model_copy(update={"waited_s": waited})

    recorder = RunRecorder.from_log(log, runs_dir=run_dir.parent)
    closed = StageRecord(
        stage=CHECKPOINT,
        status=StageStatus.FINISHED,
        started_at=waiting.started_at,
        latency_s=waited,
    )
    recorder.log.stages[recorder.log.stages.index(waiting)] = closed
    paths = write_stage_files(
        CHECKPOINT, {"checkpoint": record, "requirements": confirmed}, run_dir
    )
    state["requirements"] = confirmed
    state["checkpoint"] = record
    state["output_paths"] = {**state.get("output_paths", {}), **paths}
    state.pop("paused_at", None)
    if on_event is not None:
        on_event(
            StageEvent(
                stage=CHECKPOINT,
                status=StageStatus.FINISHED,
                started_at=waiting.started_at,
                latency_s=waited,
            )
        )
    return _invoke(
        state,
        settings=settings,
        recorder=recorder,
        model=model,
        on_event=on_event,
        start_stage=SOLUTION,
        pause_at_checkpoint=False,
    )


def _invoke(
    state: PipelineState,
    *,
    settings: Settings,
    recorder: RunRecorder,
    model: BaseChatModel,
    on_event: EventCallback | None,
    start_stage: str,
    pause_at_checkpoint: bool,
) -> PipelineResult:
    """Build the graph from ``start_stage``, run it on ``state`` under the recorder and
    the optional Langfuse handler, and wrap the outcome."""
    handler = make_langfuse_handler(settings)
    config: RunnableConfig = {
        "run_name": f"rfp-run-{recorder.run_id}",
        "metadata": {"run_id": recorder.run_id, "source": recorder.log.source_path},
    }
    if handler is not None:
        config["callbacks"] = [handler]
    graph = build_pipeline(
        settings=settings,
        recorder=recorder,
        model=model,
        out_dir=recorder.run_dir,
        on_event=on_event,
        start_stage=start_stage,
        pause_at_checkpoint=pause_at_checkpoint,
    )
    try:
        with recorder.activate():
            try:
                final: PipelineState = graph.invoke(state, config=config)
            except Exception as exc:
                failed = [s.stage for s in recorder.log.stages if s.status == StageStatus.FAILED]
                stage = failed[-1] if failed else "unknown"
                logger.error("Run %s failed in stage %s: %s", recorder.run_id, stage, exc)
                raise PipelineError(stage, recorder.log, recorder.run_dir, exc) from exc
            finally:
                recorder.set_trace_url(langfuse_trace_url(handler, settings))
    finally:
        shutdown_langfuse(settings)
    paused_at = final.get("paused_at")
    if paused_at is not None:
        recorder.pause()  # the log says "not finished", with the waiting record in it
    return PipelineResult(
        summary=final.get("summary"),
        run_log=recorder.log,
        run_dir=recorder.run_dir,
        state=final,
        paused_at=paused_at,
    )
