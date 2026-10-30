"""Parse-quality pass (S4): an LLM judges every page the S2 heuristics flagged.

Code flags, the model confirms. For each flagged page one ``structured_call`` returns a
``PageJudgement``; code then decides what happens, so the attribution is auditable:

- judge says the page is fine: the flags are cleared (``triggered_by=code``,
  ``confirmed_bad=False``);
- judge says the page is bad and confirms at least one heuristic flag: the confirmed
  flags stay and the page goes to the VLM hook (``triggered_by=code``);
- judge says the page is bad but confirms none of the flags: the model found a problem
  no heuristic named; an ``other`` flag with the judge's reason replaces the code flags
  and the page goes to the VLM hook (``triggered_by=model``).

The VLM hook only records "would escalate" in core; transcription is stretch ST2. A
judge call that fails after its retries keeps the page's code flags, so a flaky judge
can never hide a damaged page.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import StructuredOutputError, get_chat_model, load_prompt, structured_call
from rfp_agent.observability import current_recorder
from rfp_agent.schemas import (
    Escalation,
    EscalationTrigger,
    FlagReason,
    ImageBlock,
    Page,
    PageFlag,
    PageJudgement,
    ParsedDocument,
    ParseQualityReport,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODE = "parse_quality"
PROMPT = "parse_quality"

# (page, judgement) -> text describing what was done with a confirmed-bad page.
EscalationHook = Callable[[Page, PageJudgement], str]


def record_only_hook(page: Page, judgement: PageJudgement) -> str:
    """Core VLM hook: record the decision, transcribe nothing (ST2 replaces this)."""
    return f"would escalate to VLM: {judgement.reason}"


# --------------------------------------------------------------------------------------
# Prompt rendering
# --------------------------------------------------------------------------------------


def format_flags(flags: list[PageFlag]) -> str:
    return "\n".join(f"- `{f.reason.value}`: {f.detail or 'no detail'}" for f in flags)


def format_images(images: list[ImageBlock]) -> str:
    if not images:
        return "none"
    return "\n".join(
        f"- {i.width:.0f} x {i.height:.0f} pt, caption or nearby text: "
        f"{(i.caption or '').strip() or 'none'}"
        for i in images
    )


def render_prompt(
    page: Page, flags: list[PageFlag], images: list[ImageBlock], *, title: str, page_count: int
) -> str:
    return load_prompt(PROMPT).render(
        title=title,
        page_number=page.number,
        page_count=page_count,
        flags=format_flags(flags),
        images=format_images(images),
        markdown=page.markdown.strip() or "(empty)",
    )


# --------------------------------------------------------------------------------------
# Judge and decision
# --------------------------------------------------------------------------------------


def judge_page(
    page: Page,
    flags: list[PageFlag],
    images: list[ImageBlock],
    *,
    title: str,
    page_count: int,
    model: BaseChatModel,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> PageJudgement:
    """One LLM call judging one flagged page. Raises ``StructuredOutputError``."""
    text = render_prompt(page, flags, images, title=title, page_count=page_count)
    result = structured_call(
        model,
        PageJudgement,
        [HumanMessage(text)],
        node=NODE,
        settings=settings,
        recorder=recorder,
        config=config,
    )
    return result.value


def escalate(
    page: Page,
    flags: list[PageFlag],
    judgement: PageJudgement,
    *,
    hook: EscalationHook = record_only_hook,
) -> tuple[Escalation, list[PageFlag]]:
    """Apply the attribution rule to one judged page.

    Returns the escalation record and the flags the page keeps. The judge's
    ``confirmed_flags`` are intersected with the page's actual flags, so a flag name the
    model invents cannot survive.
    """
    if not judgement.bad:
        return (
            Escalation(
                page=page.number,
                triggered_by=EscalationTrigger.CODE,
                confirmed_bad=False,
                action=f"cleared by judge: {judgement.reason}",
            ),
            [],
        )
    confirmed = set(judgement.confirmed_flags)
    kept = [f for f in flags if f.reason in confirmed]
    if kept:
        trigger = EscalationTrigger.CODE
    else:
        trigger = EscalationTrigger.MODEL
        kept = [PageFlag(page=page.number, reason=FlagReason.OTHER, detail=judgement.reason)]
    escalation = Escalation(
        page=page.number, triggered_by=trigger, confirmed_bad=True, action=hook(page, judgement)
    )
    return escalation, kept


def _judge_failed(page: Page, error: StructuredOutputError) -> Escalation:
    return Escalation(
        page=page.number,
        triggered_by=EscalationTrigger.CODE,
        confirmed_bad=True,
        action=f"judge failed after {len(error.attempts)} attempts ({error}); flags kept",
    )


# --------------------------------------------------------------------------------------
# The pass
# --------------------------------------------------------------------------------------


def run_quality_pass(
    parsed: ParsedDocument,
    *,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    hook: EscalationHook = record_only_hook,
) -> tuple[ParsedDocument, ParseQualityReport]:
    """Judge every flagged page and return a copy of ``parsed`` holding only the flags
    that survived, plus a report. Every escalation is also recorded on the run recorder.
    Pages without flags cost no call; ``parsed`` itself is not modified."""
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    by_page: dict[int, list[PageFlag]] = {}
    for f in parsed.flags:
        by_page.setdefault(f.page, []).append(f)
    if not by_page:
        return parsed.model_copy(deep=True), ParseQualityReport()
    if model is None:
        model = get_chat_model(settings=settings)

    title = parsed.title or parsed.source_path
    report = ParseQualityReport(judged_pages=sorted(by_page))
    kept_flags: list[PageFlag] = []
    for number in report.judged_pages:
        page = parsed.pages[number - 1]
        flags = by_page[number]
        images = [i for i in parsed.images if i.page == number]
        try:
            judgement = judge_page(
                page,
                flags,
                images,
                title=title,
                page_count=parsed.page_count,
                model=model,
                settings=settings,
                recorder=recorder,
                config=config,
            )
        except StructuredOutputError as error:
            logger.warning("%s: page %d judge failed, keeping its flags: %s", NODE, number, error)
            escalation, kept = _judge_failed(page, error), flags
        else:
            report.judgements[number] = judgement
            escalation, kept = escalate(page, flags, judgement, hook=hook)
        report.escalations.append(escalation)
        kept_flags.extend(kept)
        if recorder is not None:
            recorder.record_escalation(escalation)

    return parsed.model_copy(update={"flags": kept_flags}, deep=True), report
