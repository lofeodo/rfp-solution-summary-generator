"""A scripted chat model for unit tests: returns pre-built AIMessages in order and records
every conversation it was sent. Works with LangChain's tool-calling
``with_structured_output`` path because ``bind_tools`` returns the model itself."""

from __future__ import annotations

import itertools
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

_ids = itertools.count(1)


def usage(inp: int, out: int, cached: int = 0) -> dict:
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "input_token_details": {"cache_read": cached},
    }


def tool_call_msg(
    name: str,
    args: dict,
    *,
    tokens: tuple[int, int, int] = (100, 20, 0),
    finish_reason: str | None = None,
) -> AIMessage:
    """An AIMessage that calls the structured-output tool ``name`` with ``args``."""
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": f"call_{next(_ids)}", "type": "tool_call"}],
        usage_metadata=usage(*tokens),
        response_metadata={"finish_reason": finish_reason or "tool_calls"},
    )


def text_msg(
    text: str, *, tokens: tuple[int, int, int] = (100, 20, 0), finish_reason: str = "stop"
) -> AIMessage:
    return AIMessage(
        content=text,
        usage_metadata=usage(*tokens),
        response_metadata={"finish_reason": finish_reason},
    )


class ScriptedChatModel(BaseChatModel):
    responses: list[AIMessage]
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    model_name: str = "scripted"

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        if not self.responses:
            raise AssertionError("ScriptedChatModel ran out of responses")
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])
