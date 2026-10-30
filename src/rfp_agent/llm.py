"""LLM layer: model factory, schema-enforced calls with bounded retry, prompt loader.

Every LLM call in the pipeline goes through ``structured_call``:

1. The model is asked for a Pydantic schema through LangChain's provider-native
   ``with_structured_output(include_raw=True)``: forced tool calling for DeepSeek with
   thinking off (the default here), JSON mode for DeepSeek with thinking on (thinking mode
   rejects forced tool choice), the ``output_config.format`` JSON-schema mode for
   Anthropic. See ``structured_method``.
2. If parsing or validation fails, the model's own reply plus the validation error is
   appended to the conversation and the call is retried, up to
   ``Settings.max_structured_retries`` times. A reply cut off by the output cap is not
   retried: the same request would be cut off again.
3. One ``NodeMetrics`` (tokens, cost, latency, retries) is recorded per call into the
   active ``RunRecorder``, whether the call succeeds or exhausts its retries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from pydantic import BaseModel

from rfp_agent.config import PROMPTS_DIR, Settings, get_settings, split_model_spec
from rfp_agent.observability import current_recorder, estimate_cost, usage_from_message
from rfp_agent.schemas import NodeMetrics

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Model factory
# --------------------------------------------------------------------------------------

# Providers whose key lives in Settings (read from .env). Other LangChain providers read
# their own environment variables.
_KEY_FIELDS = {
    "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
}

# Providers that must not receive sampling parameters: current Claude models reject a
# non-default temperature (langchain-anthropic raises before sending for Sonnet 5.5).
_NO_SAMPLING_PARAMS = {"anthropic"}


class MissingApiKeyError(ValueError):
    """The configured provider has no API key."""


def get_chat_model(
    spec: str | None = None,
    *,
    settings: Settings | None = None,
    thinking: bool | None = None,
    **overrides: Any,
) -> BaseChatModel:
    """Build a chat model from a ``provider:model_id`` spec (default ``Settings.model``).

    Keys, timeout and transport retries come from settings; ``overrides`` win over
    everything and are passed straight to the provider class. ``thinking`` switches
    DeepSeek's thinking mode (default ``Settings.deepseek_thinking``); it is ignored for
    other providers, which keep their model default.
    """
    settings = settings or get_settings()
    provider, model_id = split_model_spec(spec or settings.model)
    if provider == "deepseek":
        if thinking is None:
            thinking = settings.deepseek_thinking
        extra_body = dict(overrides.pop("extra_body", None) or {})
        extra_body.setdefault("thinking", {"type": "enabled" if thinking else "disabled"})
        overrides["extra_body"] = extra_body

    kwargs: dict[str, Any] = {
        "timeout": settings.request_timeout_s,
        "max_retries": settings.llm_transport_retries,
    }
    if provider not in _NO_SAMPLING_PARAMS:
        kwargs["temperature"] = settings.temperature
    if settings.max_output_tokens is not None:
        kwargs["max_tokens"] = settings.max_output_tokens
    if provider in _KEY_FIELDS and "api_key" not in overrides:
        field_name, env_name = _KEY_FIELDS[provider]
        key = getattr(settings, field_name)
        if not key:
            raise MissingApiKeyError(
                f"{env_name} is not set; add it to .env to use '{provider}:{model_id}'"
            )
        kwargs["api_key"] = key
    kwargs.update(overrides)
    return init_chat_model(f"{provider}:{model_id}", **kwargs)


def get_judge_model(settings: Settings | None = None, **overrides: Any) -> BaseChatModel:
    """The eval judge (``Settings.judge_model``)."""
    settings = settings or get_settings()
    return get_chat_model(settings.judge_model, settings=settings, **overrides)


def _provider_of(model: BaseChatModel) -> str:
    module = type(model).__module__.split(".")[0]
    if module.startswith("langchain_"):
        return module.removeprefix("langchain_")
    return getattr(model, "_llm_type", None) or module


def model_spec_of(model: BaseChatModel) -> str:
    """``provider:model_id`` of a model instance, for logs and pricing lookup."""
    name = getattr(model, "model_name", None) or getattr(model, "model", None) or "unknown"
    return f"{_provider_of(model)}:{name}"


StructuredMethod = Literal["json_schema", "json_mode", "function_calling"]


def _deepseek_thinking_on(model: BaseChatModel) -> bool:
    extra = getattr(model, "extra_body", None) or {}
    # The DeepSeek API default is thinking on, so a missing toggle counts as on.
    return (extra.get("thinking") or {}).get("type", "enabled") != "disabled"


def structured_method(model: BaseChatModel) -> StructuredMethod:
    """Structured-output mode per provider.

    - Anthropic: native JSON-schema output (current Claude models reject forced tool
      choice, so LangChain's tool-calling path would fall back to unforced tool use).
    - DeepSeek with thinking on: JSON mode (thinking mode rejects forced ``tool_choice``;
      seen live, 400 "Thinking mode does not support this tool_choice").
    - Everything else, DeepSeek with thinking off included: forced tool calling.
    """
    provider = _provider_of(model)
    if provider == "anthropic":
        return "json_schema"
    if provider == "deepseek" and _deepseek_thinking_on(model):
        return "json_mode"
    return "function_calling"


def json_mode_instruction(schema: type[BaseModel]) -> str:
    """System text for JSON mode, where the schema is not sent through the API."""
    return (
        "Reply with a single JSON object and nothing else. It must validate against this "
        f"JSON schema:\n{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
    )


# --------------------------------------------------------------------------------------
# Structured calls
# --------------------------------------------------------------------------------------

FEEDBACK_MAX_CHARS = 2000
NO_OUTPUT_FEEDBACK = (
    "No structured output was returned. Reply with exactly one output that matches the "
    "required schema."
)


@dataclass
class AttemptRecord:
    attempt: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    error: str | None = None


@dataclass
class StructuredResult[T: BaseModel]:
    value: T
    metrics: NodeMetrics
    attempts: list[AttemptRecord] = field(default_factory=list)


class StructuredOutputError(RuntimeError):
    """The model did not produce a valid object within the retry budget."""

    def __init__(
        self,
        message: str,
        *,
        node: str,
        schema: str,
        attempts: list[AttemptRecord],
        metrics: NodeMetrics,
        truncated: bool = False,
    ) -> None:
        super().__init__(message)
        self.node = node
        self.schema = schema
        self.attempts = attempts
        self.metrics = metrics
        self.truncated = truncated


def _is_truncated(message: AIMessage) -> bool:
    meta = message.response_metadata or {}
    return meta.get("finish_reason") == "length" or meta.get("stop_reason") == "max_tokens"


def format_feedback(error: BaseException | None) -> str:
    """The text sent back to the model after a failed attempt."""
    if error is None:
        return NO_OUTPUT_FEEDBACK
    text = str(error)
    if len(text) > FEEDBACK_MAX_CHARS:
        text = text[:FEEDBACK_MAX_CHARS] + " ...[truncated]"
    return (
        "Your previous output did not validate against the required schema.\n"
        f"Errors:\n{text}\n"
        "Return a corrected output that fixes every error. Do not add fields that are not "
        "in the schema."
    )


def _after_system(messages: list[BaseMessage]) -> int:
    """Index just after the leading system messages."""
    i = 0
    while i < len(messages) and isinstance(messages[i], SystemMessage):
        i += 1
    return i


def _feedback_messages(raw: AIMessage, feedback: str) -> list[BaseMessage]:
    """Messages that answer a failed reply.

    A reply that made tool calls must be answered with one tool result per call (both
    OpenAI-style and Anthropic APIs reject a conversation with unanswered tool calls);
    otherwise the feedback is a plain user turn.
    """
    ids = [tc.get("id") for tc in raw.tool_calls] + [tc.get("id") for tc in raw.invalid_tool_calls]
    ids = [i for i in ids if i]
    if ids:
        return [ToolMessage(content=feedback, tool_call_id=i, status="error") for i in ids]
    return [HumanMessage(content=feedback)]


def structured_call[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    messages: list[BaseMessage],
    *,
    node: str,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    max_retries: int | None = None,
    config: RunnableConfig | None = None,
) -> StructuredResult[T]:
    """Call ``model`` and return a validated ``schema`` instance.

    Retries up to ``max_retries`` times (default ``Settings.max_structured_retries``),
    feeding the validation error back. Records one ``NodeMetrics`` into ``recorder`` (or
    the active one) on success and on failure. Raises ``StructuredOutputError`` when the
    budget is exhausted or the reply is truncated.
    """
    settings = settings or get_settings()
    if max_retries is None:
        max_retries = settings.max_structured_retries
    recorder = recorder or current_recorder()
    method = structured_method(model)
    runnable = model.with_structured_output(schema, include_raw=True, method=method)
    spec = model_spec_of(model)
    history: list[BaseMessage] = list(messages)
    if method == "json_mode":
        history.insert(_after_system(history), SystemMessage(json_mode_instruction(schema)))
    attempts: list[AttemptRecord] = []
    started_at = datetime.now(UTC)
    t0 = time.perf_counter()

    def finish_metrics() -> NodeMetrics:
        tin = sum(a.input_tokens for a in attempts)
        tout = sum(a.output_tokens for a in attempts)
        tcache = sum(a.cached_input_tokens for a in attempts)
        m = NodeMetrics(
            node=node,
            model=spec,
            input_tokens=tin,
            output_tokens=tout,
            cached_input_tokens=tcache,
            cost_usd=estimate_cost(spec, tin, tout, tcache),
            latency_s=time.perf_counter() - t0,
            retries=max(len(attempts) - 1, 0),
            started_at=started_at,
        )
        if recorder is not None:
            recorder.record(m)
        return m

    for attempt in range(max_retries + 1):
        out = runnable.invoke(history, config=config)
        raw: AIMessage = out["raw"]
        parsed = out.get("parsed")
        error = out.get("parsing_error")
        tin, tout, tcache = usage_from_message(raw)
        ok = error is None and parsed is not None
        attempts.append(
            AttemptRecord(
                attempt, tin, tout, tcache, None if ok else str(error or NO_OUTPUT_FEEDBACK)
            )
        )
        if ok:
            return StructuredResult(value=parsed, metrics=finish_metrics(), attempts=attempts)

        if _is_truncated(raw):
            raise StructuredOutputError(
                f"{node}: output truncated by the token cap; not retrying",
                node=node,
                schema=schema.__name__,
                attempts=attempts,
                metrics=finish_metrics(),
                truncated=True,
            )
        logger.info(
            "%s: %s attempt %d failed: %s",
            node,
            schema.__name__,
            attempt + 1,
            (attempts[-1].error or "")[:200],
        )
        history += [raw, *_feedback_messages(raw, format_feedback(error))]

    raise StructuredOutputError(
        f"{node}: no valid {schema.__name__} after {len(attempts)} attempts; "
        f"last error: {attempts[-1].error}",
        node=node,
        schema=schema.__name__,
        attempts=attempts,
        metrics=finish_metrics(),
    )


# --------------------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------------------

_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


@dataclass(frozen=True)
class Prompt:
    name: str
    path: Path
    text: str
    sha256: str

    @property
    def variables(self) -> set[str]:
        return set(_VAR.findall(self.text))

    def render(self, **variables: Any) -> str:
        """Substitute ``{{name}}`` placeholders. Missing and unused variables are errors,
        so a typo on either side fails loudly. Single braces are left alone."""
        needed = self.variables
        missing = needed - variables.keys()
        if missing:
            raise KeyError(f"prompt {self.name!r} is missing variables: {sorted(missing)}")
        unused = variables.keys() - needed
        if unused:
            raise ValueError(f"prompt {self.name!r} has no placeholders for: {sorted(unused)}")
        return _VAR.sub(lambda m: str(variables[m.group(1)]), self.text)


def load_prompt(name: str, *, prompts_dir: Path = PROMPTS_DIR) -> Prompt:
    """Read ``prompts/<name>.md`` and record its SHA-256 on the active run."""
    path = prompts_dir / f"{name}.md"
    data = path.read_bytes()
    prompt = Prompt(
        name=name,
        path=path,
        text=data.decode("utf-8"),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    recorder = current_recorder()
    if recorder is not None:
        recorder.record_prompt(name, prompt.sha256)
    return prompt
