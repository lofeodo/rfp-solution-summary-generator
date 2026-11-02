"""ST2 vision-model transcription with a scripted fake model. No network. The page
render runs on the real Federal Way PDF (pymupdf, local)."""

from __future__ import annotations

import base64
import struct

import pytest

from fakes import ScriptedChatModel, text_msg, tool_call_msg
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing.quality import record_only_hook
from rfp_agent.parsing.vlm import (
    NODE,
    VLM_MAX_TOKENS,
    PageRenderError,
    build_message,
    get_vlm_model,
    make_vlm_hook,
    render_page_png,
    transcribe_page,
)
from rfp_agent.schemas import Page, PageJudgement, PageKind

PDF = DATA_DIR / "rfps" / "federal_way.pdf"
SETTINGS = Settings(_env_file=None, max_structured_retries=1, vlm_dpi=140)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8  # enough for the message tests
PAGE = Page(number=5, markdown="#### Scope\n\nThe following tables outline...", word_count=6)
JUDGEMENT = PageJudgement(
    text_usable=True,
    content_missing=True,
    page_kind=PageKind.TABLE,
    confirmed_flags=["large_image_block"],
    reason="The environment table is inside a 474x426 pt image.",
)


def reply(markdown: str, notes: str = "") -> object:
    return tool_call_msg("VlmTranscription", {"markdown": markdown, "notes": notes})


def png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", png[16:24])  # IHDR width, height


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def test_render_page_png_at_140_dpi_stays_under_the_1568_px_long_edge():
    png = render_page_png(PDF, 5, dpi=140)
    width, height = png_size(png)
    assert (width, height) == (1190, 1540)  # letter page, 612 x 792 pt
    assert max(width, height) <= 1568
    assert 50_000 < len(png) < 1_000_000


def test_render_page_png_rejects_bad_pages_and_paths(tmp_path):
    with pytest.raises(PageRenderError, match="no page 99"):
        render_page_png(PDF, 99, dpi=72)
    with pytest.raises(PageRenderError, match="no page 0"):
        render_page_png(PDF, 0, dpi=72)
    with pytest.raises(PageRenderError, match="cannot render"):
        render_page_png(tmp_path / "missing.pdf", 1, dpi=72)


# --------------------------------------------------------------------------------------
# The message and the call
# --------------------------------------------------------------------------------------


def test_message_is_image_block_then_text_block():
    message = build_message(PNG, "transcribe this")
    image, text = message.content
    assert image["type"] == "image_url"
    url = image["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == PNG
    assert text == {"type": "text", "text": "transcribe this"}


def test_transcribe_page_renders_the_prompt_and_records_the_vlm_node(tmp_path):
    model = ScriptedChatModel(responses=[reply("| a | b |\n| --- | --- |", "footer cut")])
    rec = RunRecorder("federal_way.pdf", "fake:scripted", 0.0, runs_dir=tmp_path)
    with rec.activate(write=False):
        out = transcribe_page(
            PNG,
            PAGE,
            reason=JUDGEMENT.reason,
            title="City of Federal Way ERP RFP",
            page_count=16,
            model=model,
            settings=SETTINGS,
        )
    assert (out.markdown, out.notes) == ("| a | b |\n| --- | --- |", "footer cut")
    (message,) = model.calls[0]
    text = message.content[1]["text"]
    assert "Title: City of Federal Way ERP RFP" in text
    assert "Page 5 of 16" in text
    assert "inside a 474x426 pt image" in text
    assert "<extracted>\n#### Scope\n\nThe following tables outline...\n</extracted>" in text
    assert "{{" not in text
    assert [n.node for n in rec.log.nodes] == [NODE]
    assert "parse_vlm" in rec.log.prompt_hashes


def test_empty_library_text_renders_a_placeholder():
    model = ScriptedChatModel(responses=[reply("x")])
    transcribe_page(
        PNG,
        Page(number=1, markdown="  ", word_count=0),
        reason="r",
        title="t",
        page_count=1,
        model=model,
        settings=SETTINGS,
    )
    assert "<extracted>\n(empty)\n</extracted>" in model.calls[0][0].content[1]["text"]


# --------------------------------------------------------------------------------------
# The hook
# --------------------------------------------------------------------------------------


def hook_for(model: ScriptedChatModel, pdf=PDF):
    return make_vlm_hook(pdf, title="Federal Way", page_count=16, model=model, settings=SETTINGS)


def test_hook_returns_markdown_and_a_descriptive_action():
    markdown = "| System | Action |\n| --- | --- |\n| Eden | Replace |\n| Quadrant | Replace |"
    model = ScriptedChatModel(responses=[reply(markdown, "none")])
    outcome = hook_for(model)(PAGE, JUDGEMENT)
    assert outcome.markdown == markdown
    assert outcome.notes == "none"
    assert outcome.model == "fake:scripted"
    assert outcome.action == "transcribed by VLM (6 words, fake:scripted)"
    # the real page was rendered and sent: a data URL much larger than the stub PNG
    url = model.calls[0][0].content[0]["image_url"]["url"]
    assert len(url) > 100_000


def test_hook_failure_paths_keep_the_flags():
    # 1. the model never produces a valid object (retry budget 1 -> two attempts)
    model = ScriptedChatModel(responses=[text_msg("not json"), text_msg("still not")])
    outcome = hook_for(model)(PAGE, JUDGEMENT)
    assert outcome.markdown is None
    assert outcome.action.startswith("VLM failed: ") and outcome.action.endswith("; flags kept")
    # 2. the page cannot be rendered: no model call at all
    model = ScriptedChatModel(responses=[reply("x")])
    outcome = hook_for(model)(Page(number=99, markdown="", word_count=0), JUDGEMENT)
    assert outcome.markdown is None
    assert "no page 99" in outcome.action
    assert model.calls == []
    # 3. an empty transcription is a failure too
    model = ScriptedChatModel(responses=[reply("   ")])
    outcome = hook_for(model)(PAGE, JUDGEMENT)
    assert outcome.markdown is None
    assert outcome.action == "VLM failed: empty transcription; flags kept"


def test_hook_is_not_the_record_only_hook():
    assert hook_for(ScriptedChatModel()) is not record_only_hook


# --------------------------------------------------------------------------------------
# Model factory
# --------------------------------------------------------------------------------------


def test_get_vlm_model_uses_the_vlm_spec_and_its_own_token_cap():
    settings = Settings(
        _env_file=None,
        vlm_model="anthropic:claude-sonnet-5-5",
        anthropic_api_key="sk-test",
        max_output_tokens=500,
    )
    model = get_vlm_model(settings)
    assert type(model).__module__.startswith("langchain_anthropic")
    assert model.model == "claude-sonnet-5-5"
    assert model.max_tokens == VLM_MAX_TOKENS  # not the generator's 500
