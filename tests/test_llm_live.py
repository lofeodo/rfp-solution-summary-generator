"""Live smoke tests against the real providers. Paid: run with ``pytest -m llm``.

Each test skips when its key is missing from ``.env``. Cost is a fraction of a cent.
"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from rfp_agent.config import Settings
from rfp_agent.llm import get_chat_model, structured_call
from rfp_agent.observability import RunRecorder
from rfp_agent.schemas import Claim

pytestmark = pytest.mark.llm

SETTINGS = Settings()
MESSAGES = [
    SystemMessage(
        "Extract the single most important factual claim from the RFP chunk. "
        "Cite the chunk ID given in the input."
    ),
    HumanMessage(
        "Chunk S2.1: The total contract amount shall not exceed $175,000. "
        "The contract period runs from November 2024 to February 2026."
    ),
]


DEEPSEEK = SETTINGS.model if SETTINGS.generator[0] == "deepseek" else "deepseek:deepseek-flash"


def _check(spec: str, tmp_path, **model_kw) -> None:
    model = get_chat_model(spec, settings=SETTINGS, **model_kw)
    rec = RunRecorder("live-test", spec, SETTINGS.temperature, runs_dir=tmp_path)
    with rec.activate():
        result = structured_call(model, Claim, MESSAGES, node="live_smoke", settings=SETTINGS)
    assert result.value.chunk_ids == ["S2.1"]
    m = result.metrics
    assert m.input_tokens > 0 and m.output_tokens > 0
    assert m.cost_usd > 0
    assert (tmp_path / rec.run_id / "run_log.json").is_file()
    print(f"\n{spec}: {m.model_dump_json()}\nvalue: {result.value.model_dump_json()}")


@pytest.mark.skipif(not SETTINGS.deepseek_api_key, reason="DEEPSEEK_API_KEY not set")
def test_deepseek_structured_call_thinking_off(tmp_path):
    _check(DEEPSEEK, tmp_path, thinking=False)


@pytest.mark.skipif(not SETTINGS.deepseek_api_key, reason="DEEPSEEK_API_KEY not set")
def test_deepseek_structured_call_thinking_on(tmp_path):
    _check(DEEPSEEK, tmp_path, thinking=True)


@pytest.mark.skipif(not SETTINGS.anthropic_api_key, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_structured_call(tmp_path):
    _check(SETTINGS.judge_model, tmp_path)
