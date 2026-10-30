"""Config tests. Settings are built with ``_env_file=None`` so a developer's real .env
never leaks into the test run."""

import pytest

from rfp_agent import config
from rfp_agent.config import ModelPricing, Settings, pricing_for, split_model_spec

ENV_VARS = [
    "RFP_MODEL",
    "RFP_JUDGE_MODEL",
    "RFP_TEMPERATURE",
    "RFP_FULL_TEXT_PROBLEM",
    "RFP_MAX_STRUCTURED_RETRIES",
    "RFP_MAX_OUTPUT_TOKENS",
    "RFP_REQUEST_TIMEOUT_S",
    "RFP_LLM_TRANSPORT_RETRIES",
    "RFP_DEEPSEEK_THINKING",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_defaults():
    s = Settings(_env_file=None)
    assert s.model == "deepseek:deepseek-flash"
    assert s.judge_model == "anthropic:claude-sonnet-5-5"
    assert s.temperature == 0.0
    assert s.max_structured_retries == 2
    assert s.max_output_tokens is None
    assert s.request_timeout_s == 120.0
    assert s.llm_transport_retries == 2
    assert s.deepseek_thinking is False
    assert s.llm_concurrency == 4
    assert s.full_text_problem is False
    assert s.single_call_extraction is False
    assert s.generator == ("deepseek", "deepseek-flash")
    assert s.judge == ("anthropic", "claude-sonnet-5-5")
    assert s.langfuse_enabled is False
    assert s.langfuse_host == "https://cloud.langfuse.com"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("RFP_MODEL", "anthropic:claude-opus-5-5")
    monkeypatch.setenv("RFP_TEMPERATURE", "0.3")
    monkeypatch.setenv("RFP_FULL_TEXT_PROBLEM", "true")
    monkeypatch.setenv("RFP_MAX_OUTPUT_TOKENS", "4000")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    s = Settings(_env_file=None)
    assert s.generator == ("anthropic", "claude-opus-5-5")
    assert s.temperature == 0.3
    assert s.full_text_problem is True
    assert s.max_output_tokens == 4000
    assert s.deepseek_api_key == "sk-test"
    assert s.langfuse_enabled is True


def test_langfuse_needs_both_keys(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    assert Settings(_env_file=None).langfuse_enabled is False


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("deepseek:deepseek-flash", ("deepseek", "deepseek-flash")),
        ("Anthropic:claude-sonnet-5-5", ("anthropic", "claude-sonnet-5-5")),
        (" openai : gpt-x ", ("openai", "gpt-x")),
    ],
)
def test_split_model_spec(spec, expected):
    assert split_model_spec(spec) == expected


@pytest.mark.parametrize("spec", ["deepseek-flash", ":model", "provider:", ""])
def test_split_model_spec_rejects_bad_specs(spec):
    with pytest.raises(ValueError):
        split_model_spec(spec)


def test_pricing_lookup():
    flash = pricing_for("deepseek-flash")
    assert isinstance(flash, ModelPricing)
    assert pricing_for("deepseek:deepseek-flash") == flash
    assert flash.output_per_mtok > flash.input_per_mtok > flash.cached_input_per_mtok
    assert pricing_for("anthropic:claude-sonnet-5-5") is not None
    assert pricing_for("nobody:unknown-model") is None


def test_paths_point_at_repo():
    assert (config.REPO_ROOT / "pyproject.toml").is_file()
    assert config.PROMPTS_DIR == config.REPO_ROOT / "prompts"
    assert config.DEFAULT_INPUT.name == "rfp_brief.pdf"
