"""Response models of the UI backend (S14). The per-stage shape is the pipeline's own
``StageEvent``, used both in the SSE stream and in a run's status, so the frontend parses
one structure."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from rfp_agent.graph import StageEvent
from rfp_agent.schemas import NodeMetrics, RunTotals

RunState = Literal["queued", "running", "finished", "failed"]
TERMINAL: frozenset[str] = frozenset({"finished", "failed"})

# Artifact name (URL segment) -> file in the run directory, in pipeline order.
ARTIFACTS: dict[str, str] = {
    "parsed": "parsed.json",
    "quality": "quality.json",
    "split": "split.json",
    "requirements": "requirements.json",
    "requirements_report": "requirements_report.json",
    "problem": "problem.json",
    "solution": "solution.json",
    "risks": "risks.json",
    "summary": "summary.json",
    "run_log": "run_log.json",
}

# Files offered as downloads (attachment), by their own name.
DOWNLOADS: dict[str, str] = {
    "summary.json": "application/json",
    "summary.md": "text/markdown; charset=utf-8",
}


class RunCreated(BaseModel):
    run_id: str
    status: RunState


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
    nodes: list[NodeMetrics]  # every LLM call; empty until the run log is written
    langfuse_trace_url: str | None
    artifacts: list[str]  # names from ARTIFACTS already on disk


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
    runs_dir: str
