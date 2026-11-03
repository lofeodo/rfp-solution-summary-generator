"""Read-only view of run directories on disk (S14, ST12c). No threads, no pipeline calls.

A run ID resolves to ``<runs_dir>/<id>`` first, then ``<samples_dir>/<id>``, so the
committed samples (``runs/samples/missouri`` ...) are served as runs named ``missouri``
etc. Generated IDs look like ``20261030-141500-a1b2c3``, sample names are words, so the
two never collide in practice; a run in ``runs_dir`` wins if they ever do.

A run's state is read from its files alone (``state_from_log``), so a run paused at the
checkpoint, refined or signed off reads the same after a restart.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from rfp_agent import versions
from rfp_agent.checkpoint import CHECKPOINT_FILENAME
from rfp_agent.config import REPO_ROOT
from rfp_agent.graph import (
    ASSEMBLE,
    CHECKPOINT,
    REVISE,
    RISK,
    SOLUTION,
    STAGES,
    StageEvent,
    stage_totals,
    waiting_checkpoint,
)
from rfp_agent.schemas import (
    Artefact,
    CheckpointRecord,
    RevisionLog,
    RunLog,
    SplitDocument,
    StageStatus,
    VersionState,
)

from .models import (
    ARTIFACTS,
    RESTING,
    Allowed,
    ReviewState,
    RunListItem,
    RunState,
    RunStatus,
)

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

    def version_file(self, loc: RunLocation, artefact: Artefact, version: int) -> Path | None:
        """Version ``version`` of ``artefact``: its ``.vN.json`` copy, or the live file
        when ``version`` is the current one (an unrevised artefact has no copy yet)."""
        if version < 1:
            return None
        copy = versions.version_path(loc.path, artefact, version)
        if copy.is_file():
            return copy
        current = load_version_state(loc.path).artefacts[artefact].version
        live = versions.live_path(loc.path, artefact)
        if artefact is Artefact.REQUIREMENTS and not live.is_file():
            live = loc.path / versions.EXTRACTED_REQUIREMENTS_FILENAME  # never confirmed
        if version == current and live.is_file():
            return live
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

# Stage order for display: the pipeline, the checkpoint between reading and drafting,
# then the reviewer's revisions (ST12c).
DISPLAY_ORDER: tuple[str, ...] = (*STAGES[:5], CHECKPOINT, *STAGES[5:], REVISE)
_ORDER = {s: i for i, s in enumerate(DISPLAY_ORDER)}


def latest_records(log: RunLog) -> list:
    """The latest record of each stage, in display order. A regeneration or a revision
    appends a second record for its stage; the latest one says where the stage stands."""
    latest = {rec.stage: rec for rec in log.stages}
    return sorted(latest.values(), key=lambda r: _ORDER.get(r.stage, len(_ORDER)))


def stages_from_log(log: RunLog) -> list[StageEvent]:
    """The latest record of each stage as a ``StageEvent`` with the LLM totals of every
    call of that stage (all attempts), in display order."""
    events = []
    for rec in latest_records(log):
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


def load_version_state(run_dir: Path) -> VersionState:
    try:
        return versions.load_version_state(run_dir)
    except (ValidationError, OSError):
        return VersionState()


def load_revisions(run_dir: Path) -> RevisionLog:
    try:
        return versions.load_revisions(run_dir)
    except (ValidationError, OSError):
        return RevisionLog()


def load_checkpoint(run_dir: Path) -> CheckpointRecord | None:
    path = Path(run_dir) / CHECKPOINT_FILENAME
    if not path.is_file():
        return None
    try:
        return CheckpointRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, OSError):
        return None


def state_from_log(log: RunLog, run_dir: Path | None = None) -> tuple[RunState, str | None]:
    """Where a run with a log rests, from its files alone.

    - ``awaiting_checkpoint``: the checkpoint record is ``waiting``;
    - ``signed_off``: ``current.json`` holds a sign-off;
    - ``finished``: an ``assemble`` record finished. A stage that failed after that is a
      failed regeneration: the artefact is unchanged and the run stays usable;
    - ``failed``: a stage failed before the first assembly, or the run ended without one.
    """
    if waiting_checkpoint(log) is not None:
        return "awaiting_checkpoint", None
    if run_dir is not None and versions.is_signed_off(load_version_state(run_dir)):
        return "signed_off", None
    if any(r.stage == ASSEMBLE and r.status == StageStatus.FINISHED for r in log.stages):
        return "finished", None
    for rec in log.stages:
        if rec.status == StageStatus.FAILED:
            return "failed", f"stage {rec.stage!r} failed: {rec.error}"
    return "failed", "run ended before the assemble stage"


def allowed_actions(
    status: RunState, *, drafted: bool, stale: list[Artefact], sample: bool
) -> Allowed:
    """What a run takes in ``status``. Samples are read-only; a run with a job in flight
    takes nothing until the job ends (one job per run at a time)."""
    if sample or status not in RESTING:
        return Allowed()
    if status == "awaiting_checkpoint":
        return Allowed(checkpoint=True, revise=[Artefact.REQUIREMENTS, Artefact.PROBLEM])
    if status == "finished" and drafted:
        return Allowed(
            revise=list(Artefact),
            regenerate=[SOLUTION, RISK],
            sign_off=not stale,
        )
    return Allowed()


def review_state(loc: RunLocation, status: RunState) -> ReviewState:
    """The checkpoint, versions, stale flags, sign-off and allowed actions of a run."""
    vstate = load_version_state(loc.path)
    stale = [a for a, _ in versions.stale_artefacts(vstate)]
    drafted = all((loc.path / f).is_file() for f in ("solution.json", "risks.json"))
    return ReviewState(
        checkpoint=load_checkpoint(loc.path),
        versions=vstate,
        stale=stale,
        sign_off=vstate.signed_off,
        revisions=len(load_revisions(loc.path).revisions),
        allowed=allowed_actions(status, drafted=drafted, stale=stale, sample=loc.sample),
    )


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
    derived, derived_error = state_from_log(log, loc.path)
    final = status or derived
    return RunStatus(
        run_id=loc.run_id,
        status=final,
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
        review=review_state(loc, final),
    )


def list_item_from_log(store: RunStore, loc: RunLocation, log: RunLog) -> RunListItem:
    status, _ = state_from_log(log, loc.path)
    return RunListItem(
        run_id=loc.run_id,
        status=status,
        sample=loc.sample,
        source_name=store.source_name(loc, log),
        started_at=log.started_at,
        finished_at=log.finished_at,
        cost_usd=round(log.totals().cost_usd, 6),
        latency_s=wall_time(log.started_at, log.finished_at),
        stages_done=sum(
            1 for r in latest_records(log) if r.stage in STAGES and r.status == StageStatus.FINISHED
        ),
    )
