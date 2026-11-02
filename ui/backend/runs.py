"""Runs started through the API (S14): an in-memory registry and one worker thread.

One run at a time: ``ThreadPoolExecutor(max_workers=1)`` keeps later uploads ``queued``
until the current run ends, which keeps provider rate limits and spend predictable (each
run already fans out to two pools of LLM calls).

Events: the pipeline calls ``RunEntry.on_event`` from its executor threads (the
requirements and problem branches run in parallel). The entry appends the event to one
list under a ``threading.Condition``; SSE readers call ``wait(cursor, timeout)`` from a
worker thread (``asyncio.to_thread``) and receive everything after their cursor. One list
serves replay and live delivery, so a client that connects mid-run misses nothing and
sees nothing twice.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rfp_agent.config import Settings
from rfp_agent.graph import STAGES, PipelineError, StageEvent, apply_overrides, run_pipeline
from rfp_agent.llm import get_chat_model
from rfp_agent.schemas import RunTotals

from .models import TERMINAL, RunState
from .store import RunStore

logger = logging.getLogger(__name__)


@dataclass
class RunEntry:
    run_id: str
    source_name: str
    pdf_path: Path
    submitted_at: datetime
    model: str
    status: RunState = "queued"
    error: str | None = None
    events: list[StageEvent] = field(default_factory=list)
    cond: threading.Condition = field(default_factory=threading.Condition, repr=False)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL

    def on_event(self, event: StageEvent) -> None:
        """The pipeline callback. Thread-safe."""
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def set_status(self, status: RunState, error: str | None = None) -> None:
        with self.cond:
            self.status = status
            self.error = error
            self.cond.notify_all()

    def wait(self, cursor: int, timeout: float) -> tuple[list[StageEvent], bool]:
        """Block until there are events after ``cursor`` or the run has ended (or the
        timeout passes). Returns ``(new_events, terminal)``; ``terminal`` is only true once
        every event has been handed out, so the caller can close after draining."""
        with self.cond:
            self.cond.wait_for(lambda: len(self.events) > cursor or self.is_terminal, timeout)
            new = self.events[cursor:]
            return list(new), self.is_terminal and cursor + len(new) == len(self.events)

    def wait_terminal(self, timeout: float) -> bool:
        with self.cond:
            return self.cond.wait_for(lambda: self.is_terminal, timeout)

    def stages_so_far(self) -> list[StageEvent]:
        """Latest event per stage, in pipeline order (the parallel branches interleave)."""
        with self.cond:
            latest = {e.stage: e for e in self.events}
        return [latest[s] for s in STAGES if s in latest]

    def totals(self) -> RunTotals:
        t = RunTotals()
        for e in self.stages_so_far():
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
    ) -> RunEntry:
        """Queue a run. Builds the chat model first, so a missing provider key raises
        ``MissingApiKeyError`` here, before anything is queued."""
        settings = apply_overrides(
            self.settings,
            model=model_spec,
            full_text_problem=full_text_problem,
            single_call_extraction=single_call_extraction,
            max_iterations=max_iterations,
        )
        chat = get_chat_model(settings=settings)
        entry = RunEntry(
            run_id=run_id,
            source_name=source_name,
            pdf_path=pdf_path,
            submitted_at=datetime.now(UTC),
            model=settings.model,
        )
        with self._lock:
            self._entries[run_id] = entry
        self._executor.submit(self._run, entry, settings, chat)
        return entry

    def _run(self, entry: RunEntry, settings: Settings, chat) -> None:
        entry.set_status("running")
        try:
            run_pipeline(
                entry.pdf_path,
                settings=settings,
                model=chat,
                runs_dir=self.store.runs_dir,
                run_id=entry.run_id,
                on_event=entry.on_event,
            )
        except PipelineError as exc:
            entry.set_status("failed", str(exc))
        except Exception as exc:  # anything else must still end the run for its readers
            logger.exception("Run %s crashed outside a stage", entry.run_id)
            entry.set_status("failed", f"{type(exc).__name__}: {exc}")
        else:
            entry.set_status("finished")

    def get(self, run_id: str) -> RunEntry | None:
        with self._lock:
            return self._entries.get(run_id)

    def entries(self) -> list[RunEntry]:
        with self._lock:
            return list(self._entries.values())

    def shutdown(self) -> None:
        """Drop queued runs; the running one finishes (LangGraph threads cannot be
        interrupted cleanly) and its log is written as usual."""
        self._executor.shutdown(wait=False, cancel_futures=True)
