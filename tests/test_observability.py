"""Run recorder, cost arithmetic and Langfuse on/off. No network."""

import json
import logging
import sys
import types
from datetime import UTC, datetime

import pytest
from langchain_core.messages import AIMessage

from rfp_agent import observability as obs
from rfp_agent.config import Settings
from rfp_agent.schemas import Escalation, EscalationTrigger, NodeMetrics, RunLog

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def metrics(node: str, **kw) -> NodeMetrics:
    base = dict(node=node, model="deepseek:deepseek-flash", started_at=NOW)
    return NodeMetrics(**(base | kw))


# --- cost -----------------------------------------------------------------------------


def test_cost_deepseek_with_cache_hits():
    # 1M input of which 400k cached, 100k output at flash peak rates.
    cost = obs.estimate_cost("deepseek:deepseek-flash", 1_000_000, 100_000, 400_000)
    expected = 0.6 * 0.30 + 0.4 * 0.006 + 0.1 * 1.20
    assert cost == pytest.approx(expected)


def test_cost_claude_bare_id():
    assert obs.estimate_cost("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12.0)


def test_cost_cached_never_exceeds_input():
    # A provider reporting more cache hits than input must not produce negative cost.
    assert obs.estimate_cost("deepseek-flash", 100, 0, 500) == pytest.approx(100 * 0.006 / 1e6)


def test_cost_unknown_model_is_zero_and_warns_once(caplog):
    obs._warned_unpriced.discard("nobody:mystery")
    with caplog.at_level(logging.WARNING, logger="rfp_agent.observability"):
        assert obs.estimate_cost("nobody:mystery", 10, 10) == 0.0
        assert obs.estimate_cost("nobody:mystery", 10, 10) == 0.0
    assert sum("mystery" in r.message for r in caplog.records) == 1


def test_usage_from_message():
    msg = AIMessage(
        content="",
        usage_metadata={
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
            "input_token_details": {"cache_read": 100},
        },
    )
    assert obs.usage_from_message(msg) == (120, 30, 100)
    assert obs.usage_from_message(AIMessage(content="x")) == (0, 0, 0)
    assert obs.usage_from_message(None) == (0, 0, 0)


# --- recorder -------------------------------------------------------------------------


def test_new_run_id_shape():
    rid = obs.new_run_id(NOW)
    assert rid.startswith("20261030-120000-") and len(rid) == len("20261030-120000-") + 6
    assert obs.new_run_id(NOW) != rid


def test_recorder_writes_and_round_trips(tmp_path):
    rec = obs.RunRecorder("inputs/rfp_brief.pdf", "deepseek:deepseek-flash", 0.0, runs_dir=tmp_path)
    rec.record(metrics("requirements", input_tokens=100, output_tokens=10, cost_usd=0.01))
    rec.record(metrics("requirements", input_tokens=50, output_tokens=5, cost_usd=0.02, retries=1))
    rec.record(metrics("problem", input_tokens=7, output_tokens=3, latency_s=1.5))
    rec.record_prompt("requirements_extract", "abc")
    rec.record_escalation(
        Escalation(page=5, triggered_by=EscalationTrigger.CODE, confirmed_bad=True, action="x")
    )
    rec.set_trace_url("https://example/trace/1")
    rec.finish()
    path = rec.write()

    assert path == tmp_path / rec.run_id / "run_log.json"
    loaded = RunLog.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert loaded == rec.log
    assert loaded.finished_at is not None
    assert loaded.prompt_hashes == {"requirements_extract": "abc"}
    assert loaded.totals().input_tokens == 157
    assert loaded.totals().retries == 1

    per = rec.per_node()
    assert list(per) == ["requirements", "problem"]
    assert per["requirements"].input_tokens == 150
    assert per["requirements"].cost_usd == pytest.approx(0.03)
    assert per["problem"].latency_s == 1.5


def test_activate_sets_current_and_writes_on_error(tmp_path):
    rec = obs.RunRecorder("x.pdf", "m:x", 0.0, runs_dir=tmp_path)
    assert obs.current_recorder() is None
    with pytest.raises(RuntimeError), rec.activate():
        assert obs.current_recorder() is rec
        rec.record(metrics("n"))
        raise RuntimeError("node failed")
    assert obs.current_recorder() is None
    assert (tmp_path / rec.run_id / "run_log.json").is_file()
    assert rec.log.finished_at is not None


def test_from_settings_uses_model_and_temperature(tmp_path):
    s = Settings(_env_file=None, model="anthropic:claude-opus-5-5", temperature=0.2)
    rec = obs.RunRecorder.from_settings("a.pdf", s, runs_dir=tmp_path)
    assert rec.log.model == "anthropic:claude-opus-5-5"
    assert rec.log.temperature == 0.2


# --- Langfuse -------------------------------------------------------------------------


@pytest.fixture
def no_langfuse_env(monkeypatch):
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(var, raising=False)


def test_langfuse_disabled_is_noop_without_import(monkeypatch, no_langfuse_env):
    # Make any import of langfuse fail loudly: the disabled path must not touch it.
    monkeypatch.setitem(sys.modules, "langfuse", None)
    monkeypatch.setitem(sys.modules, "langfuse.langchain", None)
    s = Settings(_env_file=None)
    assert obs.make_langfuse_handler(s) is None
    assert obs.langfuse_trace_url(object(), s) is None
    obs.shutdown_langfuse(s)


def test_langfuse_enabled_builds_handler_with_settings(monkeypatch, no_langfuse_env):
    calls: dict = {}

    class FakeLangfuse:
        def __init__(self, **kw):
            calls["client"] = kw

    class FakeHandler:
        def __init__(self, **kw):
            calls["handler"] = kw
            self.last_trace_id = "abc123"

    class FakeClient:
        def get_trace_url(self, trace_id):
            return f"https://lf/trace/{trace_id}"

        def flush(self):
            calls["flushed"] = True

    root = types.ModuleType("langfuse")
    root.Langfuse = FakeLangfuse
    root.get_client = lambda public_key=None: FakeClient()
    lc = types.ModuleType("langfuse.langchain")
    lc.CallbackHandler = FakeHandler
    monkeypatch.setitem(sys.modules, "langfuse", root)
    monkeypatch.setitem(sys.modules, "langfuse.langchain", lc)

    s = Settings(
        _env_file=None,
        LANGFUSE_PUBLIC_KEY="pk",
        LANGFUSE_SECRET_KEY="sk",
        LANGFUSE_HOST="https://lf.example",
    )
    handler = obs.make_langfuse_handler(s)
    assert isinstance(handler, FakeHandler)
    assert calls["client"] == {
        "public_key": "pk",
        "secret_key": "sk",
        "base_url": "https://lf.example",
    }
    assert calls["handler"] == {"public_key": "pk"}
    assert obs.langfuse_trace_url(handler, s) == "https://lf/trace/abc123"

    handler.last_trace_id = "0" * 32  # no-op tracer id
    assert obs.langfuse_trace_url(handler, s) is None

    obs.shutdown_langfuse(s)
    assert calls["flushed"] is True


def test_trace_url_swallows_backend_errors(monkeypatch, no_langfuse_env):
    class Boom:
        def get_trace_url(self, trace_id):
            raise AttributeError("Langfuse client is not initialized")

    root = types.ModuleType("langfuse")
    root.get_client = lambda public_key=None: Boom()
    monkeypatch.setitem(sys.modules, "langfuse", root)
    s = Settings(_env_file=None, LANGFUSE_PUBLIC_KEY="pk", LANGFUSE_SECRET_KEY="sk")
    handler = types.SimpleNamespace(last_trace_id="abc")
    assert obs.langfuse_trace_url(handler, s) is None
