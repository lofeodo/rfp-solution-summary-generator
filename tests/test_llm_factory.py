"""Model factory: provider wiring from Settings. Builds real client objects, no network."""

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek

from rfp_agent.config import Settings
from rfp_agent.llm import MissingApiKeyError, get_chat_model, get_judge_model


@pytest.fixture(autouse=True)
def no_key_env(monkeypatch):
    for var in ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def settings(**kw) -> Settings:
    base = dict(DEEPSEEK_API_KEY="ds-key", ANTHROPIC_API_KEY="an-key")
    return Settings(_env_file=None, **(base | kw))


def test_deepseek_default():
    m = get_chat_model(settings=settings(temperature=0.0, request_timeout_s=30))
    assert isinstance(m, ChatDeepSeek)
    assert m.model_name == "deepseek-flash"
    assert m.temperature == 0.0
    assert m.api_key.get_secret_value() == "ds-key"
    assert m.request_timeout == 30
    assert m.max_retries == 2


def test_anthropic_gets_no_temperature():
    m = get_chat_model("anthropic:claude-sonnet-5-5", settings=settings(temperature=0.3))
    assert isinstance(m, ChatAnthropic)
    assert m.model == "claude-sonnet-5-5"
    assert m.temperature is None
    assert m.anthropic_api_key.get_secret_value() == "an-key"


def test_max_output_tokens_passed_when_set():
    m = get_chat_model(settings=settings(max_output_tokens=4000))
    assert m.max_tokens == 4000


def test_missing_key_names_the_variable():
    with pytest.raises(MissingApiKeyError, match="DEEPSEEK_API_KEY"):
        get_chat_model(settings=Settings(_env_file=None))


def test_overrides_win():
    m = get_chat_model(settings=settings(), temperature=0.7, max_retries=0)
    assert m.temperature == 0.7
    assert m.max_retries == 0


def test_judge_uses_judge_model():
    m = get_judge_model(settings(judge_model="anthropic:claude-haiku-5-5"))
    assert isinstance(m, ChatAnthropic)
    assert m.model == "claude-haiku-5-5"


def test_bad_spec_raises():
    with pytest.raises(ValueError):
        get_chat_model("deepseek-flash", settings=settings())
