"""Observability: a local JSON run log per run, plus optional Langfuse tracing.

Two layers, deliberately independent:

- ``RunRecorder`` holds the run's ``RunLog`` (see ``schemas.py``) and writes it to
  ``runs/<run_id>/run_log.json``. ``structured_call`` in ``llm.py`` records one
  ``NodeMetrics`` per logical LLM call (retries included) into the active recorder, and the
  prompt loader records prompt hashes. The eval harness and the UI read this file, so
  nothing depends on a hosted service being reachable.
- Langfuse is attached as a LangChain callback handler when its keys are set. Without keys
  every helper here is a no-op and the ``langfuse`` package is never imported.

Cost is an upper bound: DeepSeek peak rates, cache reads at the cached rate, cache writes
at the normal input rate (Anthropic bills them at 1.25x, so Claude cost is slightly
under-counted on calls that write the cache).
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rfp_agent.config import RUNS_DIR, Settings, get_settings, pricing_for
from rfp_agent.schemas import Escalation, NodeMetrics, RunLog, RunTotals

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

RUN_LOG_FILENAME = "run_log.json"

# --------------------------------------------------------------------------------------
# Cost and usage
# --------------------------------------------------------------------------------------

_warned_unpriced: set[str] = set()


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0
) -> float:
    """USD cost of one call from the pricing table in ``config.py``.

    ``input_tokens`` includes cached tokens (LangChain's convention for both providers);
    the cached part is billed at the cached rate. Unknown models cost 0 and log a warning
    once, so a missing price is visible rather than silently guessed.
    """
    pricing = pricing_for(model)
    if pricing is None:
        if model not in _warned_unpriced:
            _warned_unpriced.add(model)
            logger.warning("No pricing for model %r; recording cost as 0", model)
        return 0.0
    cached = min(max(cached_input_tokens, 0), max(input_tokens, 0))
    uncached = max(input_tokens - cached, 0)
    return (
        uncached * pricing.input_per_mtok
        + cached * pricing.cached_input_per_mtok
        + output_tokens * pricing.output_per_mtok
    ) / 1_000_000


def usage_from_message(message: AIMessage | None) -> tuple[int, int, int]:
    """``(input, output, cached_input)`` tokens from ``AIMessage.usage_metadata``.

    Zeros when the provider reported nothing (fakes, some error paths).
    """
    usage = getattr(message, "usage_metadata", None) or {}
    details = usage.get("input_token_details") or {}
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(details.get("cache_read") or 0),
    )


# --------------------------------------------------------------------------------------
# Run recorder
# --------------------------------------------------------------------------------------


def new_run_id(now: datetime | None = None) -> str:
    """Sortable, collision-resistant run id: ``YYYYMMDD-HHMMSS-<6 hex>`` (UTC)."""
    now = now or datetime.now(UTC)
    return f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


_current: ContextVar[RunRecorder | None] = ContextVar("rfp_run_recorder", default=None)


def current_recorder() -> RunRecorder | None:
    """The recorder of the run in progress, or ``None`` outside a run."""
    return _current.get()


class RunRecorder:
    """Accumulates a ``RunLog`` for one pipeline run and writes it as JSON."""

    def __init__(
        self,
        source_path: str | Path,
        model: str,
        temperature: float,
        *,
        run_id: str | None = None,
        runs_dir: Path = RUNS_DIR,
    ) -> None:
        self.log = RunLog(
            run_id=run_id or new_run_id(),
            source_path=str(source_path),
            started_at=datetime.now(UTC),
            model=model,
            temperature=temperature,
        )
        self.run_dir = runs_dir / self.log.run_id

    @classmethod
    def from_settings(
        cls, source_path: str | Path, settings: Settings | None = None, **kwargs: Any
    ) -> RunRecorder:
        settings = settings or get_settings()
        return cls(source_path, settings.model, settings.temperature, **kwargs)

    @property
    def run_id(self) -> str:
        return self.log.run_id

    def record(self, metrics: NodeMetrics) -> None:
        self.log.nodes.append(metrics)

    def record_prompt(self, name: str, sha256: str) -> None:
        previous = self.log.prompt_hashes.get(name)
        if previous is not None and previous != sha256:
            logger.warning("Prompt %r changed during run %s", name, self.run_id)
        self.log.prompt_hashes[name] = sha256

    def record_escalation(self, escalation: Escalation) -> None:
        self.log.escalations.append(escalation)

    def set_trace_url(self, url: str | None) -> None:
        self.log.langfuse_trace_url = url

    def totals(self) -> RunTotals:
        return self.log.totals()

    def per_node(self) -> dict[str, RunTotals]:
        """Totals grouped by node name, in first-seen order."""
        out: dict[str, RunTotals] = {}
        for n in self.log.nodes:
            t = out.setdefault(n.node, RunTotals())
            t.input_tokens += n.input_tokens
            t.output_tokens += n.output_tokens
            t.cached_input_tokens += n.cached_input_tokens
            t.cost_usd += n.cost_usd
            t.latency_s += n.latency_s
            t.retries += n.retries
        return out

    def finish(self) -> RunLog:
        if self.log.finished_at is None:
            self.log.finished_at = datetime.now(UTC)
        return self.log

    def write(self, path: Path | None = None) -> Path:
        path = path or self.run_dir / RUN_LOG_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.log.model_dump_json(indent=2), encoding="utf-8")
        return path

    @contextmanager
    def activate(self, *, write: bool = True) -> Iterator[RunRecorder]:
        """Make this the current recorder; on exit finish the run and write the log.

        The log is written even if the run raises, so a failed run still shows what it
        spent.
        """
        token = _current.set(self)
        try:
            yield self
        finally:
            _current.reset(token)
            self.finish()
            if write:
                self.write()


# --------------------------------------------------------------------------------------
# Langfuse (optional)
# --------------------------------------------------------------------------------------


def make_langfuse_handler(settings: Settings | None = None) -> Any | None:
    """A Langfuse LangChain ``CallbackHandler``, or ``None`` when keys are absent.

    Pass the result in ``config={"callbacks": [handler]}``; LangGraph propagates it to
    every LLM call inside the graph. Keys come from ``Settings`` (which reads ``.env``),
    not from the process environment, so the client is constructed explicitly.
    """
    settings = settings or get_settings()
    if not settings.langfuse_enabled:
        return None
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_host,
    )
    return CallbackHandler(public_key=settings.langfuse_public_key)


def langfuse_trace_url(handler: Any | None, settings: Settings | None = None) -> str | None:
    """URL of the handler's last trace, or ``None``. Never raises: tracing must not be
    able to fail a run."""
    settings = settings or get_settings()
    if handler is None or not settings.langfuse_enabled:
        return None
    trace_id = getattr(handler, "last_trace_id", None)
    if not trace_id or set(str(trace_id)) <= {"0"}:
        return None
    try:
        from langfuse import get_client

        return get_client(public_key=settings.langfuse_public_key).get_trace_url(trace_id=trace_id)
    except Exception:  # noqa: BLE001 - backend down or misconfigured; the run goes on
        logger.warning("Could not resolve the Langfuse trace URL", exc_info=True)
        return None


def shutdown_langfuse(settings: Settings | None = None) -> None:
    """Flush pending Langfuse events at process end; no-op without keys."""
    settings = settings or get_settings()
    if not settings.langfuse_enabled:
        return
    try:
        from langfuse import get_client

        get_client(public_key=settings.langfuse_public_key).flush()
    except Exception:  # noqa: BLE001
        logger.warning("Langfuse flush failed", exc_info=True)
