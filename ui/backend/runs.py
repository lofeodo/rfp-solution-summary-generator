"""Runs driven through the API (S14, ST12c): an in-memory registry and one worker thread.

One job at a time: ``ThreadPoolExecutor(max_workers=1)`` runs every LLM job, whichever
run it belongs to: a new run up to the checkpoint (or to the end when unattended), the
drafting that follows a confirmed checkpoint, a revision, a regeneration. Later jobs
wait their turn, which keeps provider rate limits and spend predictable. A job's state
is set when it is queued (``drafting``, ``refining``), so a run reads busy at once and
cannot take a second job meanwhile. Sign-off calls no model and runs in the request.

Events: the pipeline calls ``RunEntry.on_event`` from its executor threads (the
requirements and problem branches run in parallel). The entry appends stage events and
its own state changes to one list under a ``threading.Condition``; SSE readers call
``wait(cursor, timeout)`` from a worker thread (``asyncio.to_thread``) and receive
everything after their cursor. One list serves replay and live delivery, so a client
that connects mid-job misses nothing and sees nothing twice.

The run directory is the source of truth. A run found on disk after a restart is
``adopt``-ed: an entry seeded from its log and files, so a paused run can be confirmed
and a finished one refined as if this process had started it.
"""

from __future__ import annotations

import logging
import shutil
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rfp_agent import refine, versions
from rfp_agent.checkpoint import CheckpointError
from rfp_agent.config import Settings
from rfp_agent.graph import (
    PipelineError,
    PipelineStateError,
    StageEvent,
    apply_overrides,
    resume_pipeline,
    run_pipeline,
)
from rfp_agent.llm import get_chat_model
from rfp_agent.parsing.vlm import get_vlm_model
from rfp_agent.schemas import Artefact, CheckpointRecord, RunTotals, StageStatus, VlmScope

from .models import RESTING, RunState, StateChange
from .store import DISPLAY_ORDER, RunStore, stages_from_log, state_from_log

logger = logging.getLogger(__name__)

Event = StageEvent | StateChange


class RunBusy(RuntimeError):
    """The run has a job queued or in flight."""


@dataclass
class RunEntry:
    run_id: str
    source_name: str
    pdf_path: Path
    submitted_at: datetime
    model: str
    status: RunState = "queued"
    error: str | None = None
    events: list[Event] = field(default_factory=list)
    cond: threading.Condition = field(default_factory=threading.Condition, repr=False)
    run_dir: Path | None = None
    resting_before: RunState = "queued"  # where a failed revision returns the run
    base_totals: RunTotals = field(default_factory=RunTotals)  # spent before this job
    job_cursor: int = 0  # index of the first event of the current job
    deleted: bool = False  # set by ``RunRegistry.delete``; ``begin`` then refuses

    @property
    def is_idle(self) -> bool:
        return self.status in RESTING

    def on_event(self, event: StageEvent) -> None:
        """The pipeline callback. Thread-safe."""
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def set_status(self, status: RunState, error: str | None = None) -> None:
        with self.cond:
            self.status = status
            self.error = error
            self.events.append(StateChange(status=status, error=error))
            self.cond.notify_all()

    def begin(self, status: RunState, base_totals: RunTotals | None = None) -> None:
        """Start a job: refuse a busy run, remember where it rested, clear the last
        error. Raises ``RunBusy``."""
        with self.cond:
            if self.deleted:
                raise RunBusy(f"run {self.run_id} was deleted")
            if not self.is_idle:
                raise RunBusy(f"run {self.run_id} is {self.status}; wait for it to finish")
            self.resting_before = self.status
            self.base_totals = base_totals or RunTotals()
            self.job_cursor = len(self.events)
            self.status = status
            self.error = None
            self.events.append(StateChange(status=status))
            self.cond.notify_all()

    def wait(self, cursor: int, timeout: float) -> tuple[list[Event], bool]:
        """Block until there are events after ``cursor`` or the run rests (or the
        timeout passes). Returns ``(new_events, resting)``; ``resting`` is only true once
        every event has been handed out, so the caller can close after draining."""
        with self.cond:
            self.cond.wait_for(lambda: len(self.events) > cursor or self.is_idle, timeout)
            new = self.events[cursor:]
            return list(new), self.is_idle and cursor + len(new) == len(self.events)

    def wait_idle(self, timeout: float) -> bool:
        with self.cond:
            return self.cond.wait_for(lambda: self.is_idle, timeout)

    def stages_so_far(self) -> list[StageEvent]:
        """Latest event per stage, in display order (the parallel branches interleave)."""
        with self.cond:
            latest = {e.stage: e for e in self.events if isinstance(e, StageEvent)}
        return [latest[s] for s in DISPLAY_ORDER if s in latest]

    def totals(self) -> RunTotals:
        """What the run has spent: before this job, plus every stage of this job that
        has ended (a stage's totals arrive with its ``finished`` or ``failed`` event)."""
        with self.cond:
            ended = [
                e
                for e in self.events[self.job_cursor :]
                if isinstance(e, StageEvent) and e.status != StageStatus.STARTED
            ]
        t = self.base_totals.model_copy()
        for e in ended:
            t.input_tokens += e.totals.input_tokens
            t.output_tokens += e.totals.output_tokens
            t.cached_input_tokens += e.totals.cached_input_tokens
            t.cost_usd += e.totals.cost_usd
            t.latency_s += e.totals.latency_s
            t.retries += e.totals.retries
        return t


class RunRegistry:
    def __init__(self, store: RunStore, settings: Settings):
        self.store = store
        self.settings = settings
        self._entries: dict[str, RunEntry] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rfp-run")

    # -- entries -----------------------------------------------------------------------

    def get(self, run_id: str) -> RunEntry | None:
        with self._lock:
            return self._entries.get(run_id)

    def entries(self) -> list[RunEntry]:
        with self._lock:
            return list(self._entries.values())

    def adopt(self, run_id: str) -> RunEntry | None:
        """The entry for ``run_id``, registering a run found on disk when this process
        has none (after a restart). ``None`` for samples and directories with no log."""
        existing = self.get(run_id)
        if existing is not None:
            return existing
        loc = self.store.locate(run_id)
        if loc is None or loc.sample:
            return None
        log = self.store.read_log(loc)
        if log is None:
            return None
        status, error = state_from_log(log, loc.path)
        entry = RunEntry(
            run_id=run_id,
            source_name=self.store.source_name(loc, log),
            pdf_path=Path(log.source_path),
            submitted_at=log.started_at,
            model=log.model,
            status=status,
            error=error,
            run_dir=loc.path,
            resting_before=status,
        )
        entry.events = [*stages_from_log(log), StateChange(status=status, error=error)]
        entry.job_cursor = len(entry.events)
        entry.base_totals = log.totals()
        with self._lock:
            return self._entries.setdefault(run_id, entry)

    def delete(self, run_id: str) -> None:
        """Forget a run and remove its directory. Raises ``RunBusy`` when it has a job
        queued or in flight; samples are refused by the caller. The entry is marked
        deleted under its lock, so a request that fetched it a moment earlier cannot
        queue a job on a directory that is gone."""
        loc = self.store.locate(run_id)
        with self._lock:
            entry = self._entries.get(run_id)
        if entry is not None:
            with entry.cond:
                if not entry.is_idle:
                    raise RunBusy(f"run {run_id} is {entry.status}; wait for it to finish")
                entry.deleted = True
            with self._lock:
                self._entries.pop(run_id, None)
        if loc is not None and not loc.sample:
            shutil.rmtree(loc.path)

    def _build_model(self, model_spec: str | None, max_iterations: int | None = None):
        """Settings and chat model for a job, built in the request thread so a missing key
        (``MissingApiKeyError``) or a bad model spec fails the request, not the job."""
        settings = apply_overrides(self.settings, model=model_spec, max_iterations=max_iterations)
        return settings, get_chat_model(settings=settings)

    def _spent(self, entry: RunEntry) -> RunTotals:
        loc = self.store.locate(entry.run_id)
        log = self.store.read_log(loc) if loc is not None else None
        return log.totals() if log is not None else RunTotals()

    def _queue(
        self,
        entry: RunEntry,
        work: Callable[[], RunState],
        *,
        soft: tuple[type[BaseException], ...] = (),
    ) -> None:
        """Run ``work`` on the worker; it returns the state the run rests in after it.
        ``soft`` failures return the run to where it rested before, with the error;
        a failed pipeline stage fails the run."""

        def job() -> None:
            try:
                status = work()
            except soft as exc:
                entry.set_status(entry.resting_before, str(exc))
            except PipelineError as exc:
                entry.set_status("failed", str(exc))
            except Exception as exc:  # anything else must still end the job for its readers
                logger.exception("Run %s: job crashed", entry.run_id)
                entry.set_status("failed", f"{type(exc).__name__}: {exc}")
            else:
                entry.set_status(status)

        self._executor.submit(job)

    # -- jobs --------------------------------------------------------------------------

    def submit(
        self,
        run_id: str,
        pdf_path: Path,
        source_name: str,
        *,
        model_spec: str | None = None,
        full_text_problem: bool | None = None,
        single_call_extraction: bool | None = None,
        max_iterations: int | None = None,
        vlm: bool | None = None,
        vlm_scope: VlmScope | None = None,
        unattended: bool = False,
    ) -> RunEntry:
        """Queue a new run. It pauses at the checkpoint unless ``unattended``. Builds the
        chat model (and the vision model when the VLM is on) first, so a missing provider
        key raises ``MissingApiKeyError`` here, before anything is queued."""
        settings = apply_overrides(
            self.settings,
            model=model_spec,
            full_text_problem=full_text_problem,
            single_call_extraction=single_call_extraction,
            max_iterations=max_iterations,
            vlm=vlm,
            vlm_scope=vlm_scope,
        )
        chat = get_chat_model(settings=settings)
        vision = get_vlm_model(settings) if settings.vlm else None
        entry = RunEntry(
            run_id=run_id,
            source_name=source_name,
            pdf_path=pdf_path,
            submitted_at=datetime.now(UTC),
            model=settings.model,
            run_dir=self.store.runs_dir / run_id,
        )
        entry.set_status("queued")
        with self._lock:
            self._entries[run_id] = entry

        def work() -> RunState:
            entry.set_status("running")
            result = run_pipeline(
                entry.pdf_path,
                settings=settings,
                model=chat,
                vlm_model=vision,
                runs_dir=self.store.runs_dir,
                run_id=entry.run_id,
                on_event=entry.on_event,
                pause_at_checkpoint=not unattended,
            )
            return "awaiting_checkpoint" if result.paused else "finished"

        self._queue(entry, work)
        return entry

    def checkpoint(
        self,
        entry: RunEntry,
        record: CheckpointRecord,
        *,
        model_spec: str | None = None,
        max_iterations: int | None = None,
    ) -> None:
        """Queue the drafting that follows a confirmed checkpoint. The caller validated
        the record; a run that moved on meanwhile returns to rest with the error."""
        settings, chat = self._build_model(model_spec, max_iterations)
        entry.begin("drafting", self._spent(entry))
        run_dir = self._run_dir(entry)

        def work() -> RunState:
            resume_pipeline(run_dir, record, settings=settings, model=chat, on_event=entry.on_event)
            return "finished"

        self._queue(entry, work, soft=(CheckpointError, PipelineStateError))

    def revise(
        self,
        entry: RunEntry,
        artefact: Artefact,
        *,
        reviewer: str,
        instruction: str,
        model_spec: str | None = None,
    ) -> str:
        """Queue a revision; returns the ID it will have in ``revisions.json``. A revision
        that fails (no valid model output, or a request the run no longer takes) leaves
        the artefact unchanged and the run where it rested."""
        settings, chat = self._build_model(model_spec)
        run_dir = self._run_dir(entry)
        entry.begin("refining", self._spent(entry))
        revision_id = versions.next_revision_id(versions.load_revisions(run_dir))

        def work() -> RunState:
            refine.revise(
                run_dir,
                artefact,
                reviewer=reviewer,
                instruction=instruction,
                settings=settings,
                model=chat,
                on_event=entry.on_event,
            )
            return entry.resting_before

        self._queue(entry, work, soft=(Exception,))
        return revision_id

    def regenerate(
        self,
        entry: RunEntry,
        stage: str,
        *,
        reviewer: str,
        model_spec: str | None = None,
        max_iterations: int | None = None,
    ) -> str:
        """Queue the regeneration of ``solution`` or ``risk``. A failed stage leaves the
        artefact as it was and the run ``finished`` (a failed regeneration, not a failed
        run)."""
        settings, chat = self._build_model(model_spec, max_iterations)
        run_dir = self._run_dir(entry)
        entry.begin("refining", self._spent(entry))
        revision_id = versions.next_revision_id(versions.load_revisions(run_dir))

        def work() -> RunState:
            refine.regenerate(
                run_dir,
                stage,
                reviewer=reviewer,
                settings=settings,
                model=chat,
                on_event=entry.on_event,
            )
            return "finished"

        self._queue(entry, work, soft=(Exception,))
        return revision_id

    def sign_off(self, entry: RunEntry, *, reviewer: str, note: str | None) -> None:
        """Freeze the run, in the request (code only: one re-assembly). Raises
        ``RunBusy``, or ``refine.RefineError`` when the run cannot be signed off (stale
        artefacts, not drafted); the run then rests where it was."""
        entry.begin("refining", self._spent(entry))
        try:
            refine.sign_off(
                self._run_dir(entry),
                reviewer=reviewer,
                note=note,
                settings=self.settings,
                on_event=entry.on_event,
            )
        except refine.RefineError:
            entry.set_status(entry.resting_before)  # refused: nothing changed
            raise
        except Exception as exc:
            entry.set_status(entry.resting_before, f"{type(exc).__name__}: {exc}")
            raise
        entry.set_status("signed_off")

    def _run_dir(self, entry: RunEntry) -> Path:
        return entry.run_dir or self.store.runs_dir / entry.run_id

    def shutdown(self) -> None:
        """Drop queued jobs; the running one finishes (LangGraph threads cannot be
        interrupted cleanly) and writes its files as usual."""
        self._executor.shutdown(wait=False, cancel_futures=True)
