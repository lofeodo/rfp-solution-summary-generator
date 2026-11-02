"""Read-only view of run directories on disk (S14). No threads, no pipeline calls.

A run ID resolves to ``<runs_dir>/<id>`` first, then ``<samples_dir>/<id>``, so the
committed samples (``runs/samples/missouri`` ...) are served as runs named ``missouri``
etc. Generated IDs look like ``20261030-141500-a1b2c3``, sample names are words, so the
two never collide in practice; a run in ``runs_dir`` wins if they ever do.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from rfp_agent.config import REPO_ROOT
from rfp_agent.graph import ASSEMBLE, STAGES, StageEvent, stage_totals
from rfp_agent.schemas import RunLog, SplitDocument, StageStatus

from .models import ARTIFACTS, RunListItem, RunState, RunStatus

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SOURCE_PDF = "source.pdf"
UPLOAD_META = "upload.json"  # {"filename": original upload name, "submitted_at": ...}


@dataclass(frozen=True)
class RunLocation:
    run_id: str
    path: Path
    sample: bool


class RunStore:
    def __init__(self, runs_dir: Path, samples_dir: Path):
        self.runs_dir = Path(runs_dir)
        self.samples_dir = Path(samples_dir)
        self._splits: dict[Path, SplitDocument] = {}
        self._lock = threading.Lock()

    # -- locating ----------------------------------------------------------------------

    def locate(self, run_id: str) -> RunLocation | None:
        """The run directory for ``run_id``, or ``None`` (bad ID or no such directory)."""
        if not RUN_ID_RE.match(run_id):
            return None
        for base, sample in ((self.runs_dir, False), (self.samples_dir, True)):
            path = base / run_id
            if path.is_dir() and path.resolve().is_relative_to(base.resolve()):
                return RunLocation(run_id, path, sample)
        return None

    def new_run_dir(self, run_id: str) -> Path:
        path = self.runs_dir / run_id
        path.mkdir(parents=True, exist_ok=False)
        return path

    def list_on_disk(self) -> list[RunLocation]:
        """Every finished or failed run (a directory holding ``run_log.json``)."""
        found: list[RunLocation] = []
        samples = self.samples_dir.resolve() if self.samples_dir.exists() else None
        for base, sample in ((self.runs_dir, False), (self.samples_dir, True)):
            if not base.is_dir():
                continue
            for path in sorted(base.iterdir()):
                if not sample and samples is not None and path.resolve() == samples:
                    continue
                if (
                    path.is_dir()
                    and RUN_ID_RE.match(path.name)
                    and (path / "run_log.json").is_file()
                ):
                    found.append(RunLocation(path.name, path, sample))
        return found

    # -- reading -----------------------------------------------------------------------

    def read_log(self, loc: RunLocation) -> RunLog | None:
        path = loc.path / "run_log.json"
        if not path.is_file():
            return None
        try:
            return RunLog.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, OSError):
            return None

    def artifact_path(self, loc: RunLocation, name: str) -> Path | None:
        filename = ARTIFACTS.get(name)
        if filename is None:
            return None
        path = loc.path / filename
        return path if path.is_file() else None

    def file_path(self, loc: RunLocation, filename: str) -> Path | None:
        path = loc.path / filename
        return path if path.is_file() else None

    def available_artifacts(self, loc: RunLocation) -> list[str]:
        return [name for name, f in ARTIFACTS.items() if (loc.path / f).is_file()]

    def source_name(self, loc: RunLocation, log: RunLog | None = None) -> str:
        meta = loc.path / UPLOAD_META
        if meta.is_file():
            try:
                return str(json.loads(meta.read_text(encoding="utf-8"))["filename"])
            except (ValueError, KeyError, OSError):
                pass
        if log is not None:
            return Path(log.source_path).name
        return loc.run_id

    def source_pdf(self, loc: RunLocation) -> Path | None:
        """The uploaded PDF, or for samples the PDF named in the run log, provided it lies
        inside the repository (a run log is data, not a licence to read any path)."""
        uploaded = loc.path / SOURCE_PDF
        if uploaded.is_file():
            return uploaded
        log = self.read_log(loc)
        if log is None:
            return None
        root = REPO_ROOT.resolve()
        path = (REPO_ROOT / log.source_path).resolve()
        if path.suffix.lower() == ".pdf" and path.is_relative_to(root) and path.is_file():
            return path
        return None

    def split(self, loc: RunLocation) -> SplitDocument | None:
        """The run's ``split.json``, parsed once and cached (it never changes after the
        split stage writes it). ``None`` until it exists or while it fails to parse."""
        path = loc.path / ARTIFACTS["split"]
        with self._lock:
            cached = self._splits.get(path)
        if cached is not None:
            return cached
        if not path.is_file():
            return None
        try:
            doc = SplitDocument.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, OSError):
            return None
        with self._lock:
            self._splits[path] = doc
        return doc


# --------------------------------------------------------------------------------------
# Run log -> response models
# --------------------------------------------------------------------------------------


def stages_from_log(log: RunLog) -> list[StageEvent]:
    """The log's stage records as ``StageEvent``s with their LLM totals, pipeline order."""
    order = {s: i for i, s in enumerate(STAGES)}
    events = []
    for rec in sorted(log.stages, key=lambda r: order.get(r.stage, len(order))):
        calls, totals = stage_totals(log, rec.stage)
        events.append(
            StageEvent(
                stage=rec.stage,
                status=rec.status,
                started_at=rec.started_at,
                latency_s=rec.latency_s,
                calls=calls,
                totals=totals,
                error=rec.error,
            )
        )
    return events


def state_from_log(log: RunLog) -> tuple[RunState, str | None]:
    """A run with a log has ended: failed if a stage failed or it never assembled."""
    for rec in log.stages:
        if rec.status == StageStatus.FAILED:
            return "failed", f"stage {rec.stage!r} failed: {rec.error}"
    done = any(r.stage == ASSEMBLE and r.status == StageStatus.FINISHED for r in log.stages)
    return ("finished", None) if done else ("failed", "run ended before the assemble stage")


def wall_time(started_at: datetime | None, finished_at: datetime | None) -> float | None:
    if started_at is None or finished_at is None:
        return None
    return round((finished_at - started_at).total_seconds(), 3)


def status_from_log(
    store: RunStore,
    loc: RunLocation,
    log: RunLog,
    *,
    status: RunState | None = None,
    error: str | None = None,
) -> RunStatus:
    derived, derived_error = state_from_log(log)
    return RunStatus(
        run_id=loc.run_id,
        status=status or derived,
        sample=loc.sample,
        source_name=store.source_name(loc, log),
        model=log.model,
        started_at=log.started_at,
        finished_at=log.finished_at,
        error=error if status is not None else derived_error,
        stages=stages_from_log(log),
        totals=log.totals(),
        nodes=log.nodes,
        langfuse_trace_url=log.langfuse_trace_url,
        artifacts=store.available_artifacts(loc),
    )


def list_item_from_log(store: RunStore, loc: RunLocation, log: RunLog) -> RunListItem:
    status, _ = state_from_log(log)
    return RunListItem(
        run_id=loc.run_id,
        status=status,
        sample=loc.sample,
        source_name=store.source_name(loc, log),
        started_at=log.started_at,
        finished_at=log.finished_at,
        cost_usd=round(log.totals().cost_usd, 6),
        latency_s=wall_time(log.started_at, log.finished_at),
        stages_done=sum(1 for r in log.stages if r.status == StageStatus.FINISHED),
    )
