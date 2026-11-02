"""Vision-model transcription of poorly rendered pages (ST2).

The parse-quality pass (S4) escalates pages whose extracted text is unusable (broken
tables, garbled layout) or incomplete (an image holding a table or a form). This module
turns that escalation into a re-render: the page is rasterised with pymupdf, sent to a
vision-capable chat model together with the library parser's markdown as a reference,
and the model's transcription replaces the page's markdown before splitting.

The call goes through ``structured_call`` like every other node, so retries, token
counts, cost and latency are recorded under the node ``parse_quality_vlm``, which the
graph's stage prefix keeps inside the ``parse_quality`` stage. The image is sent as an
``image_url`` data URL, the one content-block shape both the Anthropic and the
OpenAI-compatible LangChain adapters accept, so the model is a plain
``provider:model_id`` setting (``RFP_VLM_MODEL``); the provider must accept images.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf
from langchain_core.messages import HumanMessage

from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import (
    StructuredOutputError,
    get_chat_model,
    load_prompt,
    model_spec_of,
    structured_call,
)
from rfp_agent.parsing.heuristics import count_words
from rfp_agent.parsing.quality import EscalationHook, EscalationOutcome
from rfp_agent.schemas import Page, PageJudgement, VlmTranscription

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODE = "parse_quality_vlm"
PROMPT = "parse_vlm"
# Output cap for the transcription call, independent of the generator's
# RFP_MAX_OUTPUT_TOKENS: a dense letter page is well under 4k tokens of markdown.
VLM_MAX_TOKENS = 8000


class PageRenderError(RuntimeError):
    """The page could not be rasterised (bad path or page number)."""


def render_page_png(pdf_path: str | Path, page_number: int, *, dpi: int) -> bytes:
    """PNG bytes of one page (1-based) rendered at ``dpi``."""
    path = Path(pdf_path)
    try:
        with pymupdf.open(path) as doc:
            if not 1 <= page_number <= doc.page_count:
                raise PageRenderError(
                    f"{path.name} has {doc.page_count} pages, no page {page_number}"
                )
            return doc[page_number - 1].get_pixmap(dpi=dpi).tobytes("png")
    except PageRenderError:
        raise
    except Exception as exc:  # pymupdf raises plain RuntimeError/FileNotFoundError
        raise PageRenderError(f"cannot render {path} page {page_number}: {exc}") from exc


def get_vlm_model(settings: Settings | None = None) -> BaseChatModel:
    """The vision model from ``Settings.vlm_model`` with its own output cap."""
    settings = settings or get_settings()
    return get_chat_model(settings.vlm_model, settings=settings, max_tokens=VLM_MAX_TOKENS)


def build_message(png: bytes, text: str) -> HumanMessage:
    """One human message: the page image first, then the rendered prompt."""
    data = base64.b64encode(png).decode("ascii")
    return HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}},
            {"type": "text", "text": text},
        ]
    )


def render_prompt(page: Page, *, reason: str, title: str, page_count: int) -> str:
    return load_prompt(PROMPT).render(
        title=title,
        page_number=page.number,
        page_count=page_count,
        reason=reason,
        library_markdown=page.markdown.strip() or "(empty)",
    )


def transcribe_page(
    png: bytes,
    page: Page,
    *,
    reason: str,
    title: str,
    page_count: int,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> VlmTranscription:
    """One vision call transcribing one page. Raises ``StructuredOutputError``."""
    text = render_prompt(page, reason=reason, title=title, page_count=page_count)
    result = structured_call(
        model,
        VlmTranscription,
        [build_message(png, text)],
        node=NODE,
        settings=settings,
        recorder=recorder,
        config=config,
    )
    return result.value


def make_vlm_hook(
    pdf_path: str | Path,
    *,
    title: str,
    page_count: int,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> EscalationHook:
    """The escalation hook the quality pass calls for each confirmed-bad page.

    A successful call returns the transcription as the outcome's markdown; a render or
    model failure returns an outcome without markdown, so the page keeps its flags and
    the run goes on with the library text.
    """
    settings = settings or get_settings()
    spec = model_spec_of(model)

    def hook(page: Page, judgement: PageJudgement) -> EscalationOutcome:
        try:
            png = render_page_png(pdf_path, page.number, dpi=settings.vlm_dpi)
            transcription = transcribe_page(
                png,
                page,
                reason=judgement.reason,
                title=title,
                page_count=page_count,
                model=model,
                settings=settings,
                recorder=recorder,
                config=config,
            )
        except (PageRenderError, StructuredOutputError) as error:
            logger.warning(
                "%s: page %d VLM failed, keeping its flags: %s", NODE, page.number, error
            )
            return EscalationOutcome(action=f"VLM failed: {error}; flags kept")
        markdown = transcription.markdown.strip()
        if not markdown:
            logger.warning("%s: page %d VLM returned no text, keeping its flags", NODE, page.number)
            return EscalationOutcome(action="VLM failed: empty transcription; flags kept")
        words = count_words(markdown)
        return EscalationOutcome(
            action=f"transcribed by VLM ({words} words, {spec})",
            markdown=markdown,
            notes=transcription.notes.strip(),
            model=spec,
        )

    return hook
