"""Refinement of a run by a reviewer (ST12b): revise, regenerate, sign off.

Each operation works on a run directory and continues its run log, like the checkpoint
(D43): it loads the stage files (with the confirmed requirement list), changes one
artefact, versions it (``rfp_agent.versions``), marks what depends on it stale, appends a
record to ``revisions.json`` and, once the run is drafted, re-assembles the summary so
``summary.json`` and ``summary.md`` always show the current versions and the review
history. Assembly is code only, so it runs every time; the LLM stages never re-run on
their own.

- ``revise``: one instruction, one artefact, one model call through the producing
  stage's validators (``agents/revise.py``). Requirements and the problem statement can
  be revised while the run still waits at the checkpoint; the solution and the risks
  only once they exist. A ``revise`` stage record and the ``revise_*`` call metrics go
  on the run log. A revision whose model output never validates leaves the artefact
  untouched and is recorded as ``failed`` in ``revisions.json``; it is not a failed
  stage of the run.
- ``regenerate``: re-run the solution or the risk stage alone on the current inputs,
  through the graph (``end_stage``), never cascading: regenerating the solution leaves
  the risks (and any revision of them) as they are, marked stale.
- ``sign_off``: refused while anything is stale; freezes the run, after which nothing
  can be revised or regenerated.

Errors: ``RefineError`` for a request the run cannot take (bad state, empty
instruction), ``RevisionFailed`` when the model could not produce a valid revision,
``PipelineError`` when a regenerated stage fails, ``PipelineStateError`` when the
directory holds no run.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from rfp_agent import versions
from rfp_agent.agents.revise import (
    revise_problem,
    revise_requirements,
    revise_risks,
    revise_solution,
)
from rfp_agent.agents.solution import compute_coverage
from rfp_agent.config import Settings, get_settings
from rfp_agent.graph import (
    ASSEMBLE,
    ERROR_TEXT_LIMIT,
    REVISE,
    RISK,
    SOLUTION,
    EventCallback,
    PipelineError,
    PipelineResult,
    PipelineState,
    PipelineStateError,
    StageEvent,
    _invoke,
    apply_overrides,
    load_state,
    waiting_checkpoint,
)
from rfp_agent.llm import get_chat_model
from rfp_agent.observability import RUN_LOG_FILENAME, RunRecorder
from rfp_agent.schemas import (
    Artefact,
    Brief,
    DiffSummary,
    RevisionKind,
    RevisionRecord,
    RevisionStatus,
    RunLog,
    RunTotals,
    SignOff,
    SolutionSummary,
    StageRecord,
    StageStatus,
    VersionState,
)

REGENERABLE: dict[str, Artefact] = {SOLUTION: Artefact.SOLUTION, RISK: Artefact.RISKS}


class RefineError(ValueError):
    """The run cannot take this request (signed off, still waiting, stale, empty
    instruction, missing artefact)."""


class RevisionFailed(RuntimeError):
    """The model could not produce a revision that passes validation. The failed record
    is already in ``revisions.json``; the artefact is unchanged."""

    def __init__(self, record: RevisionRecord, run_log: RunLog, run_dir: Path):
        super().__init__(f"revision {record.id} of {record.artefact} failed: {record.error}")
        self.record = record
        self.run_log = run_log
        self.run_dir = run_dir


@dataclass
class RefineResult:
    record: RevisionRecord
    versions: VersionState
    run_log: RunLog
    run_dir: Path
    summary: SolutionSummary | None = None
    output_paths: dict[str, str] | None = None

    @property
    def diff(self) -> DiffSummary | None:
        return self.record.diff


# --------------------------------------------------------------------------------------
# Loading and small helpers
# --------------------------------------------------------------------------------------


def open_run(run_dir: Path) -> tuple[RunLog, PipelineState, VersionState]:
    """The run log, the state (confirmed requirements) and the version state."""
    run_dir = Path(run_dir)
    log_path = run_dir / RUN_LOG_FILENAME
    if not log_path.is_file():
        raise PipelineStateError(f"{run_dir} has no run log")
    log = RunLog.model_validate_json(log_path.read_text(encoding="utf-8"))
    return log, load_state(run_dir, confirmed=True), versions.load_version_state(run_dir)


def drafted(state: PipelineState) -> bool:
    return "solution" in state and "risks" in state


def body_of(artefact: Artefact, obj: Any) -> Any:
    """The part of a stage result a reviewer reads, which the diff compares."""
    if artefact is Artefact.PROBLEM:
        return obj.statement
    if artefact is Artefact.SOLUTION:
        return obj.solution
    if artefact is Artefact.RISKS:
        return obj.assessment
    return obj


def _title(state: PipelineState) -> str:
    return state["parsed"].title or Path(state["pdf_path"]).name


def _brief(state: PipelineState) -> Brief | None:
    record = state.get("checkpoint")
    return record.brief if record is not None else None


def _spent(log: RunLog, since: int) -> tuple[int, RunTotals]:
    nodes = log.nodes[since:]
    totals = RunTotals()
    for n in nodes:
        totals.input_tokens += n.input_tokens
        totals.output_tokens += n.output_tokens
        totals.cached_input_tokens += n.cached_input_tokens
        totals.cost_usd += n.cost_usd
        totals.latency_s += n.latency_s
        totals.retries += n.retries
    return len(nodes), totals


def _check_open(log: RunLog, vstate: VersionState) -> None:
    if versions.is_signed_off(vstate):
        s = vstate.signed_off
        raise RefineError(
            f"run {log.run_id} was signed off by {s.reviewer} on "
            f"{s.signed_at:%Y-%m-%d %H:%M} UTC; a signed-off run is frozen"
        )


def _check_drafted(log: RunLog, state: PipelineState, what: str) -> None:
    if waiting_checkpoint(log) is not None:
        raise RefineError(
            f"run {log.run_id} is waiting at the checkpoint; confirm it before {what}"
        )
    if not drafted(state):
        raise RefineError(f"run {log.run_id} has no draft (solution and risks) to {what}")


def _emit(on_event: EventCallback | None, event: StageEvent) -> None:
    if on_event is not None:
        on_event(event)


def _reassemble(
    state: PipelineState,
    run_dir: Path,
    *,
    recorder: RunRecorder,
    settings: Settings,
    model: BaseChatModel | None,
    on_event: EventCallback | None,
) -> PipelineResult:
    """Re-run the assembly alone (code only) with the current review history."""
    review = versions.review_history(run_dir, state.get("checkpoint"))
    if review is not None:
        state["review"] = review
    recorder.log.finished_at = None  # the run now ends with this assembly
    return _invoke(
        state,
        settings=settings,
        recorder=recorder,
        model=model,  # type: ignore[arg-type]  # assemble calls no model
        on_event=on_event,
        start_stage=ASSEMBLE,
        end_stage=ASSEMBLE,
        pause_at_checkpoint=False,
    )


def realign_downstream(state: PipelineState, removed: list[str]) -> dict[Artefact, Any]:
    """The solution and risks with every removed requirement ID stripped and coverage
    recomputed against the current list, so the strict assembler still resolves every
    citation. Only the artefacts that change are returned."""
    gone = set(removed)
    changed: dict[Artefact, Any] = {}
    if not gone:
        return changed
    reqs = state["requirements"].requirements
    if "solution" in state:
        result = state["solution"]
        sol = result.solution
        if any(gone & set(c.requirement_ids) for c in sol.components) or (
            gone & set(sol.coverage.uncovered_requirement_ids)
        ):
            components = [
                c.model_copy(
                    update={"requirement_ids": [i for i in c.requirement_ids if i not in gone]}
                )
                for c in sol.components
            ]
            new_sol = sol.model_copy(
                update={"components": components, "coverage": compute_coverage(components, reqs)}
            )
            changed[Artefact.SOLUTION] = result.model_copy(update={"solution": new_sol})
    if "risks" in state:
        result = state["risks"]
        risks = result.assessment.risks
        uncovered = result.findings.uncovered_requirement_ids
        if any(gone & set(k.requirement_ids) for k in risks) or gone & set(uncovered):
            assessment = result.assessment.model_copy(
                update={
                    "risks": [
                        k.model_copy(
                            update={
                                "requirement_ids": [i for i in k.requirement_ids if i not in gone]
                            }
                        )
                        for k in risks
                    ]
                }
            )
            findings = result.findings.model_copy(
                update={"uncovered_requirement_ids": [i for i in uncovered if i not in gone]}
            )
            changed[Artefact.RISKS] = result.model_copy(
                update={"assessment": assessment, "findings": findings}
            )
    return changed


def _call_reviser(
    artefact: Artefact,
    state: PipelineState,
    instruction: str,
    *,
    model: BaseChatModel,
    settings: Settings,
    recorder: RunRecorder,
) -> tuple[Any, list[str]]:
    """Run the artefact's reviser; return the new stage result and any removed IDs."""
    common: dict[str, Any] = {
        "instruction": instruction,
        "title": _title(state),
        "model": model,
        "settings": settings,
        "recorder": recorder,
    }
    if artefact is Artefact.REQUIREMENTS:
        return revise_requirements(state["requirements"], state["split"], **common)
    if artefact is Artefact.PROBLEM:
        return revise_problem(state["problem"], state["split"], brief=_brief(state), **common), []
    if artefact is Artefact.SOLUTION:
        return (
            revise_solution(
                state["solution"],
                state["requirements"],
                state["problem"].statement,
                brief=_brief(state),
                **common,
            ),
            [],
        )
    parsed = state["parsed"]
    return (
        revise_risks(
            state["risks"],
            state["requirements"],
            state["problem"].statement,
            state["solution"].solution,
            brief=_brief(state),
            referenced_documents=parsed.referenced_documents,
            flags=parsed.flags,
            **common,
        ),
        [],
    )


def _finish(
    state: PipelineState,
    run_dir: Path,
    record: RevisionRecord,
    vstate: VersionState,
    *,
    recorder: RunRecorder,
    settings: Settings,
    model: BaseChatModel | None,
    on_event: EventCallback | None,
    waiting: bool,
) -> RefineResult:
    """Append the record, then re-assemble a drafted run or keep a waiting one paused."""
    versions.append_revision(run_dir, record)
    if drafted(state) and not waiting:
        result = _reassemble(
            state, run_dir, recorder=recorder, settings=settings, model=model, on_event=on_event
        )
        return RefineResult(
            record=record,
            versions=vstate,
            run_log=result.run_log,
            run_dir=run_dir,
            summary=result.summary,
            output_paths=result.output_paths,
        )
    if waiting:
        recorder.pause()  # still waiting at the checkpoint: the log stays unfinished
    else:
        recorder.write()
    return RefineResult(record=record, versions=vstate, run_log=recorder.log, run_dir=run_dir)


# --------------------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------------------


def revise(
    run_dir: str | Path,
    artefact: Artefact,
    *,
    reviewer: str,
    instruction: str,
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
    model_spec: str | None = None,
    on_event: EventCallback | None = None,
) -> RefineResult:
    """Apply ``instruction`` to ``artefact`` of the run in ``run_dir`` (see the module
    docstring). An instruction the model answers with no change records a revision with
    an empty diff and no new version."""
    run_dir = Path(run_dir)
    artefact = Artefact(artefact)
    if not reviewer.strip():
        raise RefineError("a revision needs the reviewer's name")
    if not instruction.strip():
        raise RefineError("the instruction is empty")
    log, state, vstate = open_run(run_dir)
    _check_open(log, vstate)
    waiting = waiting_checkpoint(log) is not None
    if artefact in (Artefact.SOLUTION, Artefact.RISKS):
        _check_drafted(log, state, f"revise the {artefact.value}")
    for key in ("parsed", "split", artefact.value):
        if key not in state:
            raise RefineError(f"run {log.run_id} has no {key} to revise")

    settings = apply_overrides(settings or get_settings(), model=model_spec)
    if model is None:
        model = get_chat_model(settings=settings)
    if artefact is Artefact.REQUIREMENTS:
        versions.ensure_live(run_dir, artefact)  # a waiting run starts its confirmed list
    recorder = RunRecorder.from_log(log, runs_dir=run_dir.parent)
    since = len(recorder.log.nodes)
    started_at = datetime.now(UTC)
    t0 = time.perf_counter()
    revision_id = versions.next_revision_id(versions.load_revisions(run_dir))
    from_version = vstate.artefacts[artefact].version
    _emit(on_event, StageEvent(stage=REVISE, status=StageStatus.STARTED, started_at=started_at))

    try:
        with recorder.activate(write=False):
            new, removed = _call_reviser(
                artefact,
                state,
                instruction.strip(),
                model=model,
                settings=settings,
                recorder=recorder,
            )
    except Exception as exc:
        latency = time.perf_counter() - t0
        calls, totals = _spent(recorder.log, since)
        error = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_LIMIT]
        record = RevisionRecord(
            id=revision_id,
            kind=RevisionKind.REVISE,
            artefact=artefact,
            reviewer=reviewer.strip(),
            instruction=instruction.strip(),
            from_version=from_version,
            model=settings.model,
            calls=calls,
            cost_usd=totals.cost_usd,
            latency_s=latency,
            status=RevisionStatus.FAILED,
            error=error,
            created_at=started_at,
        )
        versions.append_revision(run_dir, record)
        if waiting:
            recorder.pause()
        else:
            recorder.write()
        _emit(
            on_event,
            StageEvent(
                stage=REVISE,
                status=StageStatus.FAILED,
                started_at=started_at,
                latency_s=latency,
                calls=calls,
                totals=totals,
                error=error,
            ),
        )
        raise RevisionFailed(record, recorder.log, run_dir) from exc

    diff = versions.diff(body_of(artefact, state[artefact.value]), body_of(artefact, new))
    to_version = from_version
    made_stale: list[Artefact] = []
    if not diff.empty:
        to_version = versions.commit(run_dir, artefact, new, vstate)
        state[artefact.value] = new  # type: ignore[literal-required]
        for other, realigned in realign_downstream(state, removed).items():
            versions.commit(run_dir, other, realigned, vstate)
            state[other.value] = realigned  # type: ignore[literal-required]
        made_stale = versions.mark_stale(
            vstate, artefact, f"{artefact.value} changed in {revision_id} (v{to_version})"
        )
        versions.save_version_state(run_dir, vstate)
    else:
        # The diff is empty, so the artefact's stale flag (if any) is cleared: the model
        # saw the current inputs and code re-validated every ID against them.
        if vstate.artefacts[artefact].stale:
            vstate.artefacts[artefact] = vstate.artefacts[artefact].model_copy(
                update={"stale": False, "stale_because": None}
            )
            versions.save_version_state(run_dir, vstate)
    latency = time.perf_counter() - t0
    recorder.record_stage(
        StageRecord(
            stage=REVISE, status=StageStatus.FINISHED, started_at=started_at, latency_s=latency
        )
    )
    calls, totals = _spent(recorder.log, since)
    record = RevisionRecord(
        id=revision_id,
        kind=RevisionKind.REVISE,
        artefact=artefact,
        reviewer=reviewer.strip(),
        instruction=instruction.strip(),
        from_version=from_version,
        to_version=to_version,
        made_stale=made_stale,
        model=settings.model,
        calls=calls,
        cost_usd=totals.cost_usd,
        latency_s=latency,
        diff=diff,
        created_at=started_at,
    )
    _emit(
        on_event,
        StageEvent(
            stage=REVISE,
            status=StageStatus.FINISHED,
            started_at=started_at,
            latency_s=latency,
            calls=calls,
            totals=totals,
        ),
    )
    return _finish(
        state,
        run_dir,
        record,
        vstate,
        recorder=recorder,
        settings=settings,
        model=model,
        on_event=on_event,
        waiting=waiting,
    )


def regenerate(
    run_dir: str | Path,
    stage: str,
    *,
    reviewer: str,
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
    model_spec: str | None = None,
    max_iterations: int | None = None,
    on_event: EventCallback | None = None,
) -> RefineResult:
    """Re-run ``stage`` (``solution`` or ``risk``) alone on the current inputs and make
    its output the artefact's next version. Raises ``PipelineError`` when the stage
    fails (a failed record is appended first; the artefact's live file is untouched)."""
    run_dir = Path(run_dir)
    if stage not in REGENERABLE:
        raise RefineError(f"only {', '.join(REGENERABLE)} can be regenerated, not {stage!r}")
    if not reviewer.strip():
        raise RefineError("a regeneration needs the reviewer's name")
    artefact = REGENERABLE[stage]
    log, state, vstate = open_run(run_dir)
    _check_open(log, vstate)
    _check_drafted(log, state, f"regenerate the {artefact.value}")

    settings = apply_overrides(
        settings or get_settings(), model=model_spec, max_iterations=max_iterations
    )
    if model is None:
        model = get_chat_model(settings=settings)
    before = state[artefact.value]
    from_version = vstate.artefacts[artefact].version
    live = versions.live_path(run_dir, artefact)
    # Keep the current version's copy before the stage overwrites the live file.
    if not versions.version_path(run_dir, artefact, from_version).is_file():
        versions.version_path(run_dir, artefact, from_version).write_bytes(live.read_bytes())
    recorder = RunRecorder.from_log(log, runs_dir=run_dir.parent)
    since = len(recorder.log.nodes)
    started_at = datetime.now(UTC)
    t0 = time.perf_counter()
    revision_id = versions.next_revision_id(versions.load_revisions(run_dir))
    try:
        result = _invoke(
            state,
            settings=settings,
            recorder=recorder,
            model=model,
            on_event=on_event,
            start_stage=stage,
            end_stage=stage,
            pause_at_checkpoint=False,
        )
    except PipelineError as exc:
        # A failed stage writes no file, so the live file still holds the current version.
        calls, totals = _spent(recorder.log, since)
        versions.append_revision(
            run_dir,
            RevisionRecord(
                id=revision_id,
                kind=RevisionKind.REGENERATE,
                artefact=artefact,
                reviewer=reviewer.strip(),
                from_version=from_version,
                model=settings.model,
                calls=calls,
                cost_usd=totals.cost_usd,
                latency_s=time.perf_counter() - t0,
                status=RevisionStatus.FAILED,
                error=str(exc)[:ERROR_TEXT_LIMIT],
                created_at=started_at,
            ),
        )
        raise
    new = result.state[artefact.value]
    state[artefact.value] = new  # type: ignore[literal-required]
    diff = versions.diff(body_of(artefact, before), body_of(artefact, new))
    to_version = versions.commit(run_dir, artefact, new, vstate)
    made_stale = versions.mark_stale(
        vstate, artefact, f"{artefact.value} regenerated in {revision_id} (v{to_version})"
    )
    versions.save_version_state(run_dir, vstate)
    calls, totals = _spent(recorder.log, since)
    record = RevisionRecord(
        id=revision_id,
        kind=RevisionKind.REGENERATE,
        artefact=artefact,
        reviewer=reviewer.strip(),
        from_version=from_version,
        to_version=to_version,
        made_stale=made_stale,
        model=settings.model,
        calls=calls,
        cost_usd=totals.cost_usd,
        latency_s=time.perf_counter() - t0,
        diff=diff,
        created_at=started_at,
    )
    return _finish(
        state,
        run_dir,
        record,
        vstate,
        recorder=recorder,
        settings=settings,
        model=model,
        on_event=on_event,
        waiting=False,
    )


def sign_off(
    run_dir: str | Path,
    *,
    reviewer: str,
    note: str | None = None,
    settings: Settings | None = None,
    on_event: EventCallback | None = None,
) -> RefineResult:
    """Freeze the run at its current versions. Refused while any artefact is stale."""
    run_dir = Path(run_dir)
    if not reviewer.strip():
        raise RefineError("a sign-off needs the reviewer's name")
    log, state, vstate = open_run(run_dir)
    _check_open(log, vstate)
    _check_drafted(log, state, "sign off")
    stale = versions.stale_artefacts(vstate)
    if stale:
        listed = "; ".join(f"{a.value} ({why})" for a, why in stale)
        raise RefineError(
            f"run {log.run_id} has stale artefacts: {listed}. Regenerate or revise them "
            "before signing off"
        )
    settings = settings or get_settings()
    now = datetime.now(UTC)
    vstate.signed_off = SignOff(
        reviewer=reviewer.strip(),
        signed_at=now,
        note=note.strip() if note and note.strip() else None,
        versions={a: v.version for a, v in vstate.artefacts.items()},
    )
    versions.save_version_state(run_dir, vstate)
    record = RevisionRecord(
        id=versions.next_revision_id(versions.load_revisions(run_dir)),
        kind=RevisionKind.SIGN_OFF,
        reviewer=reviewer.strip(),
        note=vstate.signed_off.note,
        created_at=now,
    )
    recorder = RunRecorder.from_log(log, runs_dir=run_dir.parent)
    return _finish(
        state,
        run_dir,
        record,
        vstate,
        recorder=recorder,
        settings=settings,
        model=None,
        on_event=on_event,
        waiting=False,
    )
