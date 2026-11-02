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

The hook returns an ``EscalationOutcome``. The default ``record_only_hook`` only records
"would escalate" (the core behaviour); ``parsing.vlm.make_vlm_hook`` (ST2) returns the
page's transcription as the outcome's markdown, which then replaces the page's markdown,
clears its flags and leaves a ``TranscriptionRecord`` in the report. With
``scope="flagged"`` the judge is skipped and every flagged page goes straight to the
hook (trigger ``code``), which is how the ablation compares the two policies.

A judge call that fails after its retries keeps the page's code flags, so a flaky judge
can never hide a damaged page.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import StructuredOutputError, get_chat_model, load_prompt, structured_call
from rfp_agent.observability import current_recorder
from rfp_agent.parsing.heuristics import count_words, table_blocks
from rfp_agent.schemas import (
    Escalation,
    EscalationTrigger,
    FlagReason,
    ImageBlock,
    Page,
    PageFlag,
    PageJudgement,
    PageKind,
    ParsedDocument,
    ParseQualityReport,
    Table,
    TranscriptionRecord,
    VlmScope,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODE = "parse_quality"
PROMPT = "parse_quality"


@dataclass(frozen=True)
class EscalationOutcome:
    """What a hook did with a confirmed-bad page. ``markdown`` set means the page was
    re-rendered and this text replaces the library parser's."""

    action: str
    markdown: str | None = None
    notes: str = ""
    model: str = ""


# (page, judgement) -> what was done with a confirmed-bad page.
EscalationHook = Callable[[Page, PageJudgement], EscalationOutcome]


def record_only_hook(page: Page, judgement: PageJudgement) -> EscalationOutcome:
    """Core hook: record the decision, transcribe nothing (``RFP_VLM=false``)."""
    return EscalationOutcome(action=f"would escalate to VLM: {judgement.reason}")


FLAGGED_SCOPE_REASON = "flagged scope: every heuristically flagged page goes to the VLM"


def flagged_scope_judgement(flags: list[PageFlag]) -> PageJudgement:
    """The synthetic verdict used when the judge is skipped: bad, all flags confirmed."""
    return PageJudgement(
        text_usable=False,
        content_missing=False,
        page_kind=PageKind.OTHER,
        confirmed_flags=sorted({f.reason for f in flags}, key=str),
        reason=FLAGGED_SCOPE_REASON,
    )


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
) -> tuple[Escalation, list[PageFlag], EscalationOutcome | None]:
    """Apply the attribution rule to one judged page.

    Returns the escalation record, the flags the page keeps, and the hook's outcome
    (``None`` when the judge cleared the page). The judge's ``confirmed_flags`` are
    intersected with the page's actual flags, so a flag name the model invents cannot
    survive. A hook outcome carrying markdown clears the flags: the page is parsed now.
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
            None,
        )
    confirmed = set(judgement.confirmed_flags)
    kept = [f for f in flags if f.reason in confirmed]
    if kept:
        trigger = EscalationTrigger.CODE
    else:
        trigger = EscalationTrigger.MODEL
        kept = [PageFlag(page=page.number, reason=FlagReason.OTHER, detail=judgement.reason)]
    outcome = hook(page, judgement)
    if outcome.markdown is not None:
        kept = []
    escalation = Escalation(
        page=page.number, triggered_by=trigger, confirmed_bad=True, action=outcome.action
    )
    return escalation, kept, outcome


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
    scope: VlmScope = "judged",
) -> tuple[ParsedDocument, ParseQualityReport]:
    """Judge every flagged page and return a copy of ``parsed`` holding only the flags
    that survived, plus a report. Every escalation is also recorded on the run recorder.
    Pages without flags cost no call; ``parsed`` itself is not modified.

    ``scope="flagged"`` skips the judge: every flagged page is treated as confirmed bad
    and handed to ``hook``. When the hook returns markdown (the ST2 VLM hook), that
    page's markdown, word count and tables are replaced in the returned copy and a
    ``TranscriptionRecord`` keeps the library text for comparison.
    """
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    by_page: dict[int, list[PageFlag]] = {}
    for f in parsed.flags:
        by_page.setdefault(f.page, []).append(f)
    if not by_page:
        return parsed.model_copy(deep=True), ParseQualityReport(scope=scope)
    if model is None and scope == "judged":
        model = get_chat_model(settings=settings)

    title = parsed.title or parsed.source_path
    report = ParseQualityReport(judged_pages=sorted(by_page), scope=scope)
    kept_flags: list[PageFlag] = []
    replaced: dict[int, Page] = {}
    for number in report.judged_pages:
        page = parsed.pages[number - 1]
        flags = by_page[number]
        images = [i for i in parsed.images if i.page == number]
        outcome: EscalationOutcome | None = None
        if scope == "flagged":
            judgement = flagged_scope_judgement(flags)
            report.judgements[number] = judgement
            escalation, kept, outcome = escalate(page, flags, judgement, hook=hook)
        else:
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
                logger.warning(
                    "%s: page %d judge failed, keeping its flags: %s", NODE, number, error
                )
                escalation, kept = _judge_failed(page, error), flags
            else:
                report.judgements[number] = judgement
                escalation, kept, outcome = escalate(page, flags, judgement, hook=hook)
        if outcome is not None and outcome.markdown is not None:
            replaced[number] = Page(
                number=number, markdown=outcome.markdown, word_count=count_words(outcome.markdown)
            )
            report.transcriptions.append(
                TranscriptionRecord(
                    page=number,
                    model=outcome.model,
                    library_markdown=page.markdown,
                    vlm_markdown=outcome.markdown,
                    library_words=page.word_count,
                    vlm_words=replaced[number].word_count,
                    notes=outcome.notes,
                )
            )
        report.escalations.append(escalation)
        kept_flags.extend(kept)
        if recorder is not None:
            recorder.record_escalation(escalation)

    updates: dict[str, object] = {"flags": kept_flags}
    if replaced:
        updates["pages"] = [replaced.get(p.number, p) for p in parsed.pages]
        updates["tables"] = _rebuild_tables(parsed.tables, replaced)
    return parsed.model_copy(update=updates, deep=True), report


def _rebuild_tables(tables: list[Table], replaced: dict[int, Page]) -> list[Table]:
    """``tables`` with the entries of every re-rendered page cut from its new markdown,
    in page order."""
    out: list[Table] = []
    done: set[int] = set()
    for t in tables:
        if t.page not in replaced:
            out.append(t)
        elif t.page not in done:
            done.add(t.page)
            out.extend(
                Table(page=t.page, markdown=m) for m in table_blocks(replaced[t.page].markdown)
            )
    for number in sorted(set(replaced) - done):
        out.extend(Table(page=number, markdown=m) for m in table_blocks(replaced[number].markdown))
    return sorted(out, key=lambda t: t.page)
