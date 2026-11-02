"""structured_call retry paths with a scripted fake model. No network."""

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek

from fakes import ScriptedChatModel, text_msg, tool_call_msg
from rfp_agent.config import Settings
from rfp_agent.llm import (
    NO_OUTPUT_FEEDBACK,
    StructuredOutputError,
    model_spec_of,
    structured_call,
    structured_method,
)
from rfp_agent.observability import RunRecorder
from rfp_agent.schemas import Claim, ClaimKind

SETTINGS = Settings(_env_file=None, max_structured_retries=2)
PROMPT = [SystemMessage("Extract one claim."), HumanMessage("Chunk S1.1: the budget is $175k.")]
GOOD = {"text": "Budget is $175,000.", "kind": "fact", "chunk_ids": ["S1.1"]}


def run(model, **kw):
    return structured_call(model, Claim, PROMPT, node="test_node", settings=SETTINGS, **kw)


def test_success_first_try():
    model = ScriptedChatModel(responses=[tool_call_msg("Claim", GOOD, tokens=(120, 30, 100))])
    result = run(model)
    assert result.value == Claim(
        text="Budget is $175,000.", kind=ClaimKind.FACT, chunk_ids=["S1.1"]
    )
    m = result.metrics
    assert (m.node, m.model, m.retries) == ("test_node", "fake:scripted", 0)
    assert (m.input_tokens, m.output_tokens, m.cached_input_tokens) == (120, 30, 100)
    assert m.cost_usd == 0.0  # fake model has no price
    assert m.latency_s >= 0
    assert m.last_error is None
    assert len(model.calls) == 1


def test_validation_error_is_fed_back_as_tool_result():
    bad = tool_call_msg("Claim", GOOD | {"confidence": 0.9})  # extra field is forbidden
    model = ScriptedChatModel(responses=[bad, tool_call_msg("Claim", GOOD)])
    result = run(model)
    assert result.metrics.retries == 1
    assert result.metrics.input_tokens == 200  # both attempts counted
    second = model.calls[1]
    assert second[:2] == PROMPT
    assert isinstance(second[2], AIMessage) and second[2].tool_calls
    feedback = second[3]
    assert isinstance(feedback, ToolMessage)
    assert feedback.tool_call_id == bad.tool_calls[0]["id"]
    assert "confidence" in feedback.content
    assert "did not validate" in feedback.content
    assert [a.error is None for a in result.attempts] == [False, True]
    assert result.metrics.last_error and "confidence" in result.metrics.last_error  # F7


def test_missing_tool_call_gets_plain_feedback():
    model = ScriptedChatModel(
        responses=[text_msg("Sure! The claim is..."), tool_call_msg("Claim", GOOD)]
    )
    result = run(model)
    assert result.metrics.retries == 1
    feedback = model.calls[1][-1]
    assert isinstance(feedback, HumanMessage)
    assert feedback.content == NO_OUTPUT_FEEDBACK


def test_exhaustion_raises_with_all_attempts_and_records_cost(tmp_path):
    bad = {"text": "x", "chunk_ids": []}  # min_length=1 violated
    model = ScriptedChatModel(responses=[tool_call_msg("Claim", bad) for _ in range(3)])
    rec = RunRecorder("a.pdf", "fake:scripted", 0.0, runs_dir=tmp_path)
    with pytest.raises(StructuredOutputError) as exc:
        run(model, recorder=rec)
    err = exc.value
    assert len(err.attempts) == 3 and not err.truncated
    assert err.metrics.retries == 2
    assert "chunk_ids" in str(err)
    assert rec.log.nodes == [err.metrics]
    assert err.metrics.last_error and "chunk_ids" in err.metrics.last_error  # F7


def test_max_retries_override():
    model = ScriptedChatModel(responses=[text_msg("no")])
    with pytest.raises(StructuredOutputError) as exc:
        run(model, max_retries=0)
    assert len(exc.value.attempts) == 1


def test_truncated_reply_is_not_retried():
    cut = tool_call_msg("Claim", {"text": "Budget"}, finish_reason="length")
    model = ScriptedChatModel(responses=[cut, tool_call_msg("Claim", GOOD)])
    with pytest.raises(StructuredOutputError) as exc:
        run(model)
    assert exc.value.truncated
    assert len(model.calls) == 1


def test_records_into_active_recorder(tmp_path):
    rec = RunRecorder("a.pdf", "fake:scripted", 0.0, runs_dir=tmp_path)
    model = ScriptedChatModel(
        responses=[tool_call_msg("Claim", GOOD), tool_call_msg("Claim", GOOD)]
    )
    with rec.activate(write=False):
        run(model)
        run(model)
    assert [n.node for n in rec.log.nodes] == ["test_node", "test_node"]
    assert rec.per_node()["test_node"].input_tokens == 200


def test_structured_method_and_spec_per_provider():
    ds = ChatDeepSeek(
        model="deepseek-flash", api_key="dummy", extra_body={"thinking": {"type": "disabled"}}
    )
    an = ChatAnthropic(model="claude-sonnet-5-5", api_key="dummy")
    assert structured_method(ds) == "function_calling"
    assert structured_method(an) == "json_schema"
    assert model_spec_of(ds) == "deepseek:deepseek-flash"
    assert model_spec_of(an) == "anthropic:claude-sonnet-5-5"
