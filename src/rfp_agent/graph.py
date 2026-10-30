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
from rfp_agent.config import RUNS_DIR, Settings, get_settings
from rfp_agent.llm import get_chat_model
from rfp_agent.observability import (
    RunRecorder,
    langfuse_trace_url,
    make_langfuse_handler,
    shutdown_langfuse,
)
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.quality import run_quality_pass
from rfp_agent.render import assemble, write_summary
from rfp_agent.schemas import (
    ParsedDocument,
    ParseQualityReport,
    RequirementsOutput,
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


@dataclass
class PipelineResult:
    summary: SolutionSummary
    run_log: RunLog
    run_dir: Path
    state: PipelineState

    @property
    def output_paths(self) -> dict[str, str]:
        return dict(self.state.get("output_paths", {}))


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
):
    """Compile the pipeline graph with its runtime objects bound.

    ``out_dir`` receives each stage's JSON as it finishes (``None`` writes nothing;
    the final ``summary.json`` and ``summary.md`` are written only when it is set).
    """

    def title_of(state: PipelineState) -> str:
        return state["parsed"].title or Path(state["pdf_path"]).name

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
        )
        return {"risks": result}

    def assemble_stage(state: PipelineState, config: RunnableConfig) -> dict[str, Any]:
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
        )
        updates: dict[str, Any] = {"summary": summary}
        if out_dir is not None:
            json_path, md_path = write_summary(summary, out_dir)
            updates["output_paths"] = {json_path.name: str(json_path), md_path.name: str(md_path)}
        return updates

    graph: StateGraph = StateGraph(PipelineState)
    graph.add_node(PARSE, stage(PARSE, parse))
    graph.add_node(PARSE_QUALITY, stage(PARSE_QUALITY, parse_quality))
    graph.add_node(SPLIT, stage(SPLIT, split))
    graph.add_node(REQUIREMENTS, stage(REQUIREMENTS, requirements))
    graph.add_node(PROBLEM, stage(PROBLEM, problem))
    graph.add_node(SOLUTION, stage(SOLUTION, solution))
    graph.add_node(RISK, stage(RISK, risk))
    graph.add_node(ASSEMBLE, stage(ASSEMBLE, assemble_stage))
    graph.add_edge(START, PARSE)
    graph.add_edge(PARSE, PARSE_QUALITY)
    graph.add_edge(PARSE_QUALITY, SPLIT)
    graph.add_edge(SPLIT, REQUIREMENTS)
    graph.add_edge(SPLIT, PROBLEM)
    graph.add_edge([REQUIREMENTS, PROBLEM], SOLUTION)
    graph.add_edge(SOLUTION, RISK)
    graph.add_edge(RISK, ASSEMBLE)
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
) -> PipelineResult:
    """Run the whole pipeline on one PDF and write everything under
    ``<runs_dir>/<run_id>/``: every intermediate, ``summary.json``, ``summary.md`` and
    ``run_log.json`` (the log is written even when a stage fails).

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
    handler = make_langfuse_handler(settings)
    config: RunnableConfig = {
        "run_name": f"rfp-run-{recorder.run_id}",
        "metadata": {"run_id": recorder.run_id, "source": pdf_path},
    }
    if handler is not None:
        config["callbacks"] = [handler]
    graph = build_pipeline(
        settings=settings,
        recorder=recorder,
        model=model,
        out_dir=recorder.run_dir,
        on_event=on_event,
    )
    try:
        with recorder.activate():
            try:
                state: PipelineState = graph.invoke({"pdf_path": pdf_path}, config=config)
            except Exception as exc:
                failed = [s.stage for s in recorder.log.stages if s.status == StageStatus.FAILED]
                stage = failed[-1] if failed else "unknown"
                logger.error("Run %s failed in stage %s: %s", recorder.run_id, stage, exc)
                raise PipelineError(stage, recorder.log, recorder.run_dir, exc) from exc
            finally:
                recorder.set_trace_url(langfuse_trace_url(handler, settings))
    finally:
        shutdown_langfuse(settings)
    return PipelineResult(
        summary=state["summary"], run_log=recorder.log, run_dir=recorder.run_dir, state=state
    )
