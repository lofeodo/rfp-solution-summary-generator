"""Response and request models of the UI backend (S14, ST12c). The per-stage shape is the
pipeline's own ``StageEvent``, used both in the SSE stream and in a run's status, so the
frontend parses one structure."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from rfp_agent.graph import StageEvent
from rfp_agent.schemas import (
    Artefact,
    CheckpointRecord,
    NodeMetrics,
    RequirementDecision,
    RunTotals,
    SignOff,
    VersionState,
)

# queued -> running -> awaiting_checkpoint -> drafting -> finished <-> refining -> signed_off,
# and failed from any stage of the pipeline (ST12c). A failed revision is not a failed run.
RunState = Literal[
    "queued",
    "running",
    "awaiting_checkpoint",
    "drafting",
    "finished",
    "refining",
    "signed_off",
    "failed",
]
# No job in flight: the run waits for a human, or for nothing. SSE streams close here.
RESTING: frozenset[str] = frozenset({"awaiting_checkpoint", "finished", "signed_off", "failed"})

# Artifact name (URL segment) -> file in the run directory, in pipeline order.
ARTIFACTS: dict[str, str] = {
    "parsed": "parsed.json",
    "quality": "quality.json",
    "split": "split.json",
    "requirements": "requirements.json",
    "requirements_report": "requirements_report.json",
    "problem": "problem.json",
    "checkpoint": "checkpoint.json",
    "requirements_confirmed": "requirements_confirmed.json",
    "solution": "solution.json",
    "risks": "risks.json",
    "summary": "summary.json",
    "current": "current.json",
    "revisions": "revisions.json",
    "run_log": "run_log.json",
}

# Files offered as downloads (attachment), by their own name.
DOWNLOADS: dict[str, str] = {
    "summary.json": "application/json",
    "summary.md": "text/markdown; charset=utf-8",
}

Reviewer = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)]


class StateChange(BaseModel):
    """A run's state changed. Sent as ``event: state`` between the stage events."""

    status: RunState
    error: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunCreated(BaseModel):
    run_id: str
    status: RunState


class JobAccepted(BaseModel):
    """A checkpoint, revision or regeneration was queued. Follow it on the SSE stream."""

    run_id: str
    status: RunState
    revision_id: str | None = None  # the ID the revision will get in ``revisions.json``


class Allowed(BaseModel):
    """What the run takes now, computed by code; the frontend shows only these actions."""

    checkpoint: bool = False
    revise: list[Artefact] = Field(default_factory=list)
    regenerate: list[Literal["solution", "risk"]] = Field(default_factory=list)
    sign_off: bool = False


class ReviewState(BaseModel):
    checkpoint: CheckpointRecord | None = None
    versions: VersionState = Field(default_factory=VersionState)
    stale: list[Artefact] = Field(default_factory=list)
    sign_off: SignOff | None = None
    revisions: int = 0  # records in ``revisions.json`` (revisions, regenerations, sign-off)
    allowed: Allowed = Field(default_factory=Allowed)


class RunListItem(BaseModel):
    run_id: str
    status: RunState
    sample: bool
    source_name: str
    started_at: datetime | None
    finished_at: datetime | None
    cost_usd: float
    latency_s: float | None  # wall time of the whole run, once it ended
    stages_done: int


class RunStatus(BaseModel):
    run_id: str
    status: RunState
    sample: bool
    source_name: str
    model: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    stages: list[StageEvent]  # latest event per stage, pipeline order
    totals: RunTotals
    nodes: list[NodeMetrics]  # every LLM call; empty while a job is in flight
    langfuse_trace_url: str | None
    artifacts: list[str]  # names from ARTIFACTS already on disk
    review: ReviewState = Field(default_factory=ReviewState)


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
    runs_dir: str


# -- requests (ST12c) ------------------------------------------------------------------


class CheckpointRequest(BaseModel):
    reviewer: Reviewer
    decisions: list[RequirementDecision] = Field(default_factory=list)
    brief: str | None = Field(default=None, max_length=50_000)
    note: str | None = Field(default=None, max_length=5_000)
    model: str | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=10)


class ReviseRequest(BaseModel):
    reviewer: Reviewer
    artefact: Artefact
    instruction: Text
    model: str | None = None


class RegenerateRequest(BaseModel):
    reviewer: Reviewer
    stage: Literal["solution", "risk"]
    model: str | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=10)


class SignOffRequest(BaseModel):
    reviewer: Reviewer
    note: str | None = Field(default=None, max_length=5_000)
