"""FastAPI app for the UI (S14, ST12c): upload a PDF, run the pipeline to the checkpoint,
take the reviewer's checkpoint, revisions, regenerations and sign-off, stream stage and
state events over SSE, serve every output of a run. The API contract is in ``README.md``
next to this file. Built by ``create_app`` (uvicorn runs it as a factory), so importing this
module has no side effects.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from rfp_agent.brief import parse_brief
from rfp_agent.checkpoint import CONFIRMED_REQUIREMENTS_FILENAME, validate_checkpoint
from rfp_agent.config import REPO_ROOT, RUNS_DIR, Settings, get_settings
from rfp_agent.graph import STAGES, StageEvent
from rfp_agent.llm import MissingApiKeyError
from rfp_agent.observability import new_run_id
from rfp_agent.refine import RefineError
from rfp_agent.schemas import (
    CHUNK_ID_RE,
    Artefact,
    CheckpointRecord,
    Chunk,
    RequirementsOutput,
    RevisionLog,
    RunTotals,
)

from .models import (
    DOWNLOADS,
    CheckpointRequest,
    Health,
    JobAccepted,
    RegenerateRequest,
    ReviewState,
    ReviseRequest,
    RunCreated,
    RunListItem,
    RunStatus,
    SignOffRequest,
)
from .runs import RunBusy, RunEntry, RunRegistry
from .store import (
    SOURCE_PDF,
    UPLOAD_META,
    RunLocation,
    RunStore,
    list_item_from_log,
    load_revisions,
    review_state,
    stages_from_log,
    status_from_log,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
READ_CHUNK = 1024 * 1024
KEEPALIVE_S = 15.0
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # Vite dev server
FRONTEND_DIST = REPO_ROOT / "ui" / "frontend" / "dist"
_CHUNK_ID = re.compile(CHUNK_ID_RE)


def sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def create_app(
    *,
    runs_dir: Path = RUNS_DIR,
    samples_dir: Path | None = None,
    settings: Settings | None = None,
    frontend_dist: Path | None = FRONTEND_DIST,
) -> FastAPI:
    settings = settings or get_settings()
    store = RunStore(runs_dir, samples_dir if samples_dir is not None else runs_dir / "samples")
    registry = RunRegistry(store, settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        registry.shutdown()

    app = FastAPI(title="RFP solution summary", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.state.registry = registry
    app.add_middleware(
        CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )
    api = APIRouter(prefix="/api")

    # -- helpers -----------------------------------------------------------------------

    def locate(run_id: str) -> RunLocation:
        loc = store.locate(run_id)
        if loc is None:
            raise HTTPException(404, f"no run {run_id!r}")
        return loc

    def live_status(entry: RunEntry, loc: RunLocation | None) -> RunStatus:
        return RunStatus(
            run_id=entry.run_id,
            status=entry.status,
            sample=False,
            source_name=entry.source_name,
            model=entry.model,
            started_at=entry.submitted_at,
            finished_at=None,
            error=entry.error,
            stages=entry.stages_so_far(),
            totals=entry.totals(),
            nodes=[],
            langfuse_trace_url=None,
            artifacts=store.available_artifacts(loc) if loc else [],
            review=review_state(loc, entry.status) if loc else ReviewState(),
        )

    def live_item(entry: RunEntry) -> RunListItem:
        stages = entry.stages_so_far()
        return RunListItem(
            run_id=entry.run_id,
            status=entry.status,
            sample=False,
            source_name=entry.source_name,
            started_at=entry.submitted_at,
            finished_at=None,
            cost_usd=round(entry.totals().cost_usd, 6),
            latency_s=None,
            stages_done=sum(1 for e in stages if e.stage in STAGES and e.status == "finished"),
        )

    # -- routes ------------------------------------------------------------------------

    @api.get("/health")
    def health() -> Health:
        return Health(model=settings.model, runs_dir=str(store.runs_dir))

    @api.post("/runs", status_code=202)
    def create_run(
        file: Annotated[UploadFile, File(description="The RFP as a PDF")],
        model: Annotated[str | None, Form(description="provider:model override")] = None,
        full_text_problem: Annotated[bool | None, Form()] = None,
        single_call_extraction: Annotated[bool | None, Form()] = None,
        max_iterations: Annotated[int | None, Form(ge=1, le=10)] = None,
        unattended: Annotated[
            bool, Form(description="Run to the end without pausing at the checkpoint")
        ] = False,
    ) -> RunCreated:
        source_name = Path(file.filename or "").name or "upload.pdf"
        run_id = new_run_id()
        run_dir = store.new_run_dir(run_id)
        try:
            pdf_path = run_dir / SOURCE_PDF
            size = 0
            with pdf_path.open("wb") as out:
                while chunk := file.file.read(READ_CHUNK):
                    if size == 0 and not chunk.startswith(b"%PDF"):
                        raise HTTPException(400, "the upload is not a PDF")
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, f"PDF larger than {MAX_UPLOAD_BYTES} bytes")
                    out.write(chunk)
            if size == 0:
                raise HTTPException(400, "the upload is empty")
            meta = {
                "filename": source_name,
                "submitted_at": datetime.now(UTC).isoformat(),
                "options": {
                    "model": model,
                    "full_text_problem": full_text_problem,
                    "single_call_extraction": single_call_extraction,
                    "max_iterations": max_iterations,
                    "unattended": unattended,
                },
            }
            (run_dir / UPLOAD_META).write_text(json.dumps(meta, indent=2), encoding="utf-8")
            try:
                entry = registry.submit(
                    run_id,
                    pdf_path,
                    source_name,
                    model_spec=model,
                    full_text_problem=full_text_problem,
                    single_call_extraction=single_call_extraction,
                    max_iterations=max_iterations,
                    unattended=unattended,
                )
            except MissingApiKeyError as exc:
                raise HTTPException(503, str(exc)) from exc
            except Exception as exc:  # unknown provider, bad model spec, missing package
                raise HTTPException(400, f"cannot build model: {exc}") from exc
        except BaseException:
            shutil.rmtree(run_dir, ignore_errors=True)
            raise
        return RunCreated(run_id=entry.run_id, status=entry.status)

    @api.get("/runs")
    def list_runs() -> list[RunListItem]:
        items: dict[str, RunListItem] = {}
        for loc in store.list_on_disk():
            log = store.read_log(loc)
            if log is not None and loc.run_id not in items:
                items[loc.run_id] = list_item_from_log(store, loc, log)
        for entry in registry.entries():
            if not entry.is_idle or entry.run_id not in items:
                items[entry.run_id] = live_item(entry)
        runs = sorted(
            (i for i in items.values() if not i.sample),
            key=lambda i: i.started_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return runs + sorted((i for i in items.values() if i.sample), key=lambda i: i.run_id)

    @api.get("/runs/{run_id}")
    def run_status(run_id: str) -> RunStatus:
        entry = registry.get(run_id)
        loc = store.locate(run_id)
        if entry is not None and not entry.is_idle:
            return live_status(entry, loc)
        log = store.read_log(loc) if loc is not None else None
        if loc is not None and log is not None:
            if entry is not None:
                return status_from_log(store, loc, log, status=entry.status, error=entry.error)
            return status_from_log(store, loc, log)
        if entry is not None:  # ended without a log: crashed outside the pipeline
            return live_status(entry, loc)
        if loc is not None:  # a directory with no log and no live run: interrupted
            return RunStatus(
                run_id=run_id,
                status="failed",
                sample=loc.sample,
                source_name=store.source_name(loc),
                model=None,
                started_at=None,
                finished_at=None,
                error="interrupted: the run has no run log",
                stages=[],
                totals=RunTotals(),
                nodes=[],
                langfuse_trace_url=None,
                artifacts=store.available_artifacts(loc),
            )
        raise HTTPException(404, f"no run {run_id!r}")

    @api.get("/runs/{run_id}/events")
    async def run_events(run_id: str) -> StreamingResponse:
        entry = registry.get(run_id)
        if entry is not None:
            stream = live_events(entry)
        else:
            loc = locate(run_id)
            log = store.read_log(loc)
            if log is None:
                raise HTTPException(404, f"run {run_id!r} has no run log")
            stream = logged_events(store, loc, log)
        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api.get("/runs/{run_id}/artifacts/{name}")
    def artifact(run_id: str, name: str) -> FileResponse:
        path = store.artifact_path(locate(run_id), name)
        if path is None:
            raise HTTPException(404, f"artifact {name!r} not available for run {run_id!r}")
        return FileResponse(path, media_type="application/json")

    @api.get("/runs/{run_id}/summary.md")
    def summary_markdown(run_id: str) -> FileResponse:
        path = store.file_path(locate(run_id), "summary.md")
        if path is None:
            raise HTTPException(404, f"run {run_id!r} has no summary yet")
        return FileResponse(path, media_type=DOWNLOADS["summary.md"])

    @api.get("/runs/{run_id}/download/{name}")
    def download(run_id: str, name: str) -> FileResponse:
        if name not in DOWNLOADS:
            raise HTTPException(404, f"no download {name!r}")
        path = store.file_path(locate(run_id), name)
        if path is None:
            raise HTTPException(404, f"run {run_id!r} has no {name} yet")
        return FileResponse(path, media_type=DOWNLOADS[name], filename=f"{run_id}-{name}")

    @api.get("/runs/{run_id}/source.pdf")
    def source_pdf(run_id: str) -> FileResponse:
        path = store.source_pdf(locate(run_id))
        if path is None:
            raise HTTPException(404, f"source PDF of run {run_id!r} not found")
        return FileResponse(path, media_type="application/pdf")

    @api.get("/runs/{run_id}/chunks")
    def chunks(run_id: str) -> list[Chunk]:
        split = store.split(locate(run_id))
        if split is None:
            raise HTTPException(404, f"run {run_id!r} has no split yet")
        return split.chunks()

    @api.get("/runs/{run_id}/chunks/{chunk_id}")
    def chunk(run_id: str, chunk_id: str) -> Chunk:
        loc = locate(run_id)
        if not _CHUNK_ID.match(chunk_id):
            raise HTTPException(404, f"no chunk {chunk_id!r}")
        split = store.split(loc)
        if split is None:
            raise HTTPException(404, f"run {run_id!r} has no split yet")
        found = split.chunk_by_id(chunk_id)
        if found is None:
            raise HTTPException(404, f"no chunk {chunk_id!r} in run {run_id!r}")
        return found

    # -- the human in the loop (ST12c) --------------------------------------------------

    def mutable(run_id: str) -> tuple[RunLocation, RunEntry]:
        """The run and its registry entry (adopted from disk after a restart), for a
        request that changes it. Samples are read-only."""
        loc = locate(run_id)
        if loc.sample:
            raise HTTPException(403, f"{run_id!r} is a sample run; samples are read-only")
        entry = registry.adopt(run_id)
        if entry is None:
            raise HTTPException(409, f"run {run_id!r} has no run log yet")
        return loc, entry

    def refusal(entry: RunEntry, what: str) -> HTTPException:
        """409 saying why the run cannot take ``what`` in its current state."""
        status = entry.status
        if status == "signed_off":
            why = "it was signed off; a signed-off run is frozen"
        elif status == "awaiting_checkpoint":
            why = "it is waiting at the checkpoint; confirm the checkpoint first"
        elif status == "finished":
            why = "it is past the checkpoint"
        elif status == "failed":
            why = "it failed"
        else:
            why = f"it is {status}; wait for the current job to end"
        return HTTPException(409, f"run {entry.run_id} cannot {what}: {why}")

    def start(fn, *args, **kwargs):
        """Call a registry method that builds a model and queues a job; map its errors."""
        try:
            return fn(*args, **kwargs)
        except RunBusy as exc:
            raise HTTPException(409, str(exc)) from exc
        except MissingApiKeyError as exc:
            raise HTTPException(503, str(exc)) from exc
        except RefineError as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:  # unknown provider, bad model spec, missing package
            raise HTTPException(400, f"cannot build model: {exc}") from exc

    @api.post("/runs/{run_id}/checkpoint", status_code=202)
    def confirm_checkpoint(run_id: str, body: CheckpointRequest) -> JobAccepted:
        loc, entry = mutable(run_id)
        if entry.status != "awaiting_checkpoint":
            raise refusal(entry, "take a checkpoint")
        confirmed = loc.path / CONFIRMED_REQUIREMENTS_FILENAME
        source = confirmed if confirmed.is_file() else loc.path / "requirements.json"
        requirements = RequirementsOutput.model_validate_json(source.read_text(encoding="utf-8"))
        record = CheckpointRecord(
            reviewer=body.reviewer,
            confirmed_at=datetime.now(UTC),
            decisions=body.decisions,
            brief=parse_brief(body.brief),
            note=body.note.strip() if body.note and body.note.strip() else None,
        )
        problems = validate_checkpoint(requirements, record)
        if problems:
            raise HTTPException(400, "; ".join(problems))
        start(
            registry.checkpoint,
            entry,
            record,
            model_spec=body.model,
            max_iterations=body.max_iterations,
        )
        return JobAccepted(run_id=run_id, status=entry.status)

    @api.post("/runs/{run_id}/revise", status_code=202)
    def revise_artefact(run_id: str, body: ReviseRequest) -> JobAccepted:
        loc, entry = mutable(run_id)
        if body.artefact not in review_state(loc, entry.status).allowed.revise:
            raise refusal(entry, f"revise the {body.artefact.value}")
        revision_id = start(
            registry.revise,
            entry,
            body.artefact,
            reviewer=body.reviewer,
            instruction=body.instruction,
            model_spec=body.model,
        )
        return JobAccepted(run_id=run_id, status=entry.status, revision_id=revision_id)

    @api.post("/runs/{run_id}/regenerate", status_code=202)
    def regenerate_stage(run_id: str, body: RegenerateRequest) -> JobAccepted:
        loc, entry = mutable(run_id)
        if body.stage not in review_state(loc, entry.status).allowed.regenerate:
            raise refusal(entry, f"regenerate the {body.stage} stage")
        revision_id = start(
            registry.regenerate,
            entry,
            body.stage,
            reviewer=body.reviewer,
            model_spec=body.model,
            max_iterations=body.max_iterations,
        )
        return JobAccepted(run_id=run_id, status=entry.status, revision_id=revision_id)

    @api.post("/runs/{run_id}/sign-off")
    def sign_off_run(run_id: str, body: SignOffRequest) -> RunStatus:
        loc, entry = mutable(run_id)
        review = review_state(loc, entry.status)
        if not review.allowed.sign_off:
            if entry.status == "finished" and review.stale:
                stale = ", ".join(a.value for a in review.stale)
                raise HTTPException(
                    409,
                    f"run {run_id} cannot be signed off: stale {stale}; regenerate or revise first",
                )
            raise refusal(entry, "be signed off")
        start(registry.sign_off, entry, reviewer=body.reviewer, note=body.note)
        return run_status(run_id)

    @api.get("/runs/{run_id}/revisions")
    def revisions(run_id: str) -> RevisionLog:
        return load_revisions(locate(run_id).path)

    @api.get("/runs/{run_id}/versions/{artefact}/{version}")
    def version(run_id: str, artefact: str, version: int) -> FileResponse:
        loc = locate(run_id)
        try:
            which = Artefact(artefact)
        except ValueError as exc:
            raise HTTPException(404, f"no artefact {artefact!r}") from exc
        path = store.version_file(loc, which, version)
        if path is None:
            raise HTTPException(404, f"run {run_id!r} has no {artefact} v{version}")
        return FileResponse(path, media_type="application/json")

    app.include_router(api)

    # The built frontend, when present. Registered last so /api routes win.
    if frontend_dist is not None and (frontend_dist / "index.html").is_file():
        mount_frontend(app, frontend_dist)
    return app


async def live_events(entry: RunEntry) -> AsyncIterator[str]:
    """Every event of a registry run from the first, then live ones, then ``done`` once
    the run rests (paused at the checkpoint, finished, signed off or failed)."""
    cursor = 0
    while True:
        new, resting = await asyncio.to_thread(entry.wait, cursor, KEEPALIVE_S)
        for event in new:
            kind = "stage" if isinstance(event, StageEvent) else "state"
            yield sse(kind, event.model_dump_json())
        cursor += len(new)
        if resting:
            yield sse("done", json.dumps({"status": entry.status, "error": entry.error}))
            return
        if not new:
            yield ": keepalive\n\n"


async def logged_events(store: RunStore, loc: RunLocation, log) -> AsyncIterator[str]:
    """A run that ended before this process saw it: its stage records, then ``done``."""
    status = status_from_log(store, loc, log)
    for event in stages_from_log(log):
        yield sse("stage", event.model_dump_json())
    yield sse("done", json.dumps({"status": status.status, "error": status.error}))


def mount_frontend(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, "not found")
        candidate = (root / full_path).resolve()
        if full_path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(root / "index.html")  # client-side routes
