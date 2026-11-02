"""DeepSeek thinking toggle and the structured-output mode it implies. No network.

Background: DeepSeek's thinking mode is on by default and rejects forced ``tool_choice``
(seen live: 400 "Thinking mode does not support this tool_choice"). Thinking off keeps
forced tool calling; thinking on switches to JSON mode with the schema in the prompt.
"""

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek

import rfp_agent.llm as llm
from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.config import Settings
from rfp_agent.llm import get_chat_model, structured_call, structured_method
from rfp_agent.schemas import Claim

GOOD = {"text": "Budget is $175,000.", "kind": "fact", "chunk_ids": ["S1.1"]}


@pytest.fixture(autouse=True)
def no_key_env(monkeypatch):
    for var in ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def settings(**kw) -> Settings:
    base = dict(DEEPSEEK_API_KEY="ds-key", ANTHROPIC_API_KEY="an-key")
    return Settings(_env_file=None, **(base | kw))


def deepseek(thinking: str | None) -> ChatDeepSeek:
    extra = {"thinking": {"type": thinking}} if thinking else None
    return ChatDeepSeek(model="deepseek-flash", api_key="d", extra_body=extra)


def test_thinking_off_by_default():
    assert get_chat_model(settings=settings()).extra_body == {"thinking": {"type": "disabled"}}


def test_thinking_from_setting_and_argument():
    on = {"thinking": {"type": "enabled"}}
    assert get_chat_model(settings=settings(deepseek_thinking=True)).extra_body == on
    assert get_chat_model(settings=settings(), thinking=True).extra_body == on


def test_extra_body_override_is_merged():
    m = get_chat_model(settings=settings(), extra_body={"foo": 1})
    assert m.extra_body == {"foo": 1, "thinking": {"type": "disabled"}}


def test_anthropic_ignores_thinking_flag():
    m = get_chat_model("anthropic:claude-sonnet-5-5", settings=settings(), thinking=True)
    assert isinstance(m, ChatAnthropic)
    assert m.thinking is None


def test_method_follows_thinking():
    assert structured_method(deepseek("disabled")) == "function_calling"
    assert structured_method(deepseek("enabled")) == "json_mode"
    assert structured_method(deepseek(None)) == "json_mode"  # API default is thinking on


def test_json_mode_inserts_schema_instruction_after_system(monkeypatch):
    monkeypatch.setattr(llm, "structured_method", lambda model: "json_mode")
    prompt = [SystemMessage("Extract one claim."), HumanMessage("Chunk S1.1: budget $175k.")]
    model = ScriptedChatModel(responses=[tool_call_msg("Claim", GOOD)])
    structured_call(model, Claim, prompt, node="n", settings=settings())
    sent = model.calls[0]
    assert sent[0] == prompt[0]
    assert isinstance(sent[1], SystemMessage) and '"chunk_ids"' in sent[1].content
    assert sent[2] == prompt[1]
