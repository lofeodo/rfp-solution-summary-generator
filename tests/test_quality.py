"""Parse-quality pass (S4) with a scripted fake model. No network."""

from __future__ import annotations

import json

import pytest

from fakes import ScriptedChatModel, text_msg, tool_call_msg
from rfp_agent.config import Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing.quality import escalate, record_only_hook, run_quality_pass
from rfp_agent.schemas import (
    EscalationTrigger,
    FlagReason,
    ImageBlock,
    Page,
    PageFlag,
    PageJudgement,
    PageKind,
    ParsedDocument,
    ParseQualityReport,
)

SETTINGS = Settings(_env_file=None, max_structured_retries=1)

LOW = FlagReason.LOW_WORD_COUNT
IMG = FlagReason.LARGE_IMAGE_BLOCK
TABLE = FlagReason.BROKEN_TABLE


def doc(flags: list[PageFlag], images: list[ImageBlock] | None = None) -> ParsedDocument:
    pages = [
        Page(number=1, markdown="# City of Example\n\nRequest for Proposals", word_count=6),
        Page(number=2, markdown="## Scope\n\nThe modules are listed below.", word_count=7),
        Page(number=3, markdown="Plain narrative text on page three.", word_count=6),
    ]
    return ParsedDocument(
        source_path="example.pdf",
        title="Example RFP",
        pages=pages,
        images=images or [],
        flags=flags,
    )


def judgement(
    *,
    usable: bool = True,
    missing: bool = False,
    kind: str = "narrative",
    confirmed: list[str] | None = None,
    reason: str = "Looks fine.",
) -> dict:
    return {
        "text_usable": usable,
        "content_missing": missing,
        "page_kind": kind,
        "confirmed_flags": confirmed or [],
        "reason": reason,
    }


def verdict(**kw):
    return tool_call_msg("PageJudgement", judgement(**kw))


def run(parsed, responses, **kw):
    model = ScriptedChatModel(responses=responses)
    out, report = run_quality_pass(parsed, model=model, settings=SETTINGS, **kw)
    return model, out, report


def test_no_flags_makes_no_call():
    parsed = doc([])
    model, out, report = run(parsed, [])
    assert model.calls == []
    assert out == parsed
    assert report == ParseQualityReport()


def test_cleared_page_drops_flag_and_leaves_input_untouched():
    parsed = doc([PageFlag(page=1, reason=LOW, detail="6 words")])
    _, out, report = run(parsed, [verdict(kind="cover", reason="A cover page.")])
    assert out.flags == []
    assert parsed.flags == [PageFlag(page=1, reason=LOW, detail="6 words")]
    (esc,) = report.escalations
    assert (esc.page, esc.triggered_by, esc.confirmed_bad) == (1, EscalationTrigger.CODE, False)
    assert esc.action == "cleared by judge: A cover page."
    assert report.judgements[1].page_kind is PageKind.COVER
    assert report.judged_pages == [1]


def test_confirmed_flag_is_kept_and_escalated_by_code():
    flag = PageFlag(page=2, reason=IMG, detail="image covers 42% of the page")
    parsed = doc([flag])
    _, out, report = run(
        parsed,
        [verdict(missing=True, kind="table", confirmed=["large_image_block"], reason="Table.")],
    )
    assert out.flags == [flag]
    (esc,) = report.escalations
    assert (esc.triggered_by, esc.confirmed_bad) == (EscalationTrigger.CODE, True)
    assert esc.action == "would escalate to VLM: Table."


def test_model_raised_problem_replaces_code_flags():
    parsed = doc([PageFlag(page=3, reason=LOW, detail="6 words")])
    _, out, report = run(parsed, [verdict(usable=False, reason="Columns interleaved.")])
    assert out.flags == [PageFlag(page=3, reason=FlagReason.OTHER, detail="Columns interleaved.")]
    (esc,) = report.escalations
    assert (esc.triggered_by, esc.confirmed_bad) == (EscalationTrigger.MODEL, True)


def test_several_flags_on_one_page_share_one_call_and_only_confirmed_survive():
    low = PageFlag(page=2, reason=LOW, detail="7 words")
    img = PageFlag(page=2, reason=IMG, detail="image covers 54% of the page")
    parsed = doc([low, img])
    model, out, report = run(parsed, [verdict(missing=True, confirmed=["large_image_block"])])
    assert len(model.calls) == 1
    assert out.flags == [img]
    assert len(report.escalations) == 1


def test_invented_flag_name_does_not_survive():
    # The judge confirms a flag the page does not have: the page is still bad, but no
    # heuristic flag was confirmed, so the model owns the escalation.
    parsed = doc([PageFlag(page=1, reason=LOW, detail="6 words")])
    _, out, report = run(parsed, [verdict(usable=False, confirmed=["broken_table"])])
    assert [f.reason for f in out.flags] == [FlagReason.OTHER]
    assert report.escalations[0].triggered_by is EscalationTrigger.MODEL


def test_flags_confirmed_on_a_page_judged_fine_are_ignored():
    parsed = doc([PageFlag(page=1, reason=LOW)])
    _, out, report = run(parsed, [verdict(confirmed=["low_word_count"])])
    assert out.flags == []
    assert report.escalations[0].confirmed_bad is False


def test_judge_failure_keeps_flags_and_continues(caplog):
    flags = [PageFlag(page=1, reason=LOW, detail="6 words"), PageFlag(page=3, reason=LOW)]
    parsed = doc(flags)
    # Page 1: no tool call twice (1 retry allowed) -> failure. Page 3: cleared.
    responses = [text_msg("I think it is fine."), text_msg("Still fine."), verdict()]
    model, out, report = run(parsed, responses)
    assert len(model.calls) == 3
    assert out.flags == [flags[0]]
    first, second = report.escalations
    assert (first.page, first.triggered_by, first.confirmed_bad) == (
        1,
        EscalationTrigger.CODE,
        True,
    )
    assert first.action.startswith("judge failed after 2 attempts")
    assert second.confirmed_bad is False
    assert 1 not in report.judgements and 3 in report.judgements
    assert "page 1 judge failed" in caplog.text


def test_prompt_carries_page_flags_and_images():
    parsed = doc(
        [PageFlag(page=2, reason=IMG, detail="image covers 42% of the page")],
        images=[ImageBlock(page=2, width=474.2, height=426.0, caption="Scope: ERP modules")],
    )
    model, _, _ = run(parsed, [verdict()])
    (message,) = model.calls[0]
    text = message.content
    assert "Title: Example RFP" in text
    assert "Page 2 of 3" in text
    assert "- `large_image_block`: image covers 42% of the page" in text
    assert "474 x 426 pt, caption or nearby text: Scope: ERP modules" in text
    assert "The modules are listed below." in text
    assert "{{" not in text


def test_page_without_images_and_empty_text_render_placeholders():
    parsed = doc([PageFlag(page=1, reason=LOW)])
    parsed.pages[0] = Page(number=1, markdown="  ", word_count=0)
    model, _, _ = run(parsed, [verdict(kind="blank")])
    text = model.calls[0][0].content
    assert "## Images on this page\n\nnone" in text
    assert "<page>\n(empty)\n</page>" in text
    assert "- `low_word_count`: no detail" in text


def test_escalations_and_metrics_land_on_active_recorder(tmp_path):
    parsed = doc([PageFlag(page=1, reason=LOW), PageFlag(page=2, reason=IMG)])
    rec = RunRecorder("example.pdf", "fake:scripted", 0.0, runs_dir=tmp_path)
    with rec.activate():
        run(parsed, [verdict(), verdict(missing=True, confirmed=["large_image_block"])])
    assert [(e.page, e.confirmed_bad) for e in rec.log.escalations] == [(1, False), (2, True)]
    assert [n.node for n in rec.log.nodes] == ["parse_quality", "parse_quality"]
    assert "parse_quality" in rec.log.prompt_hashes
    written = json.loads((tmp_path / rec.run_id / "run_log.json").read_text(encoding="utf-8"))
    assert len(written["escalations"]) == 2


def test_custom_hook_action_is_used():
    calls = []

    def hook(page: Page, j: PageJudgement) -> str:
        calls.append((page.number, j.page_kind))
        return "transcribed by test hook"

    parsed = doc([PageFlag(page=2, reason=IMG)])
    _, _, report = run(
        parsed, [verdict(missing=True, kind="table", confirmed=["large_image_block"])], hook=hook
    )
    assert calls == [(2, PageKind.TABLE)]
    assert report.escalations[0].action == "transcribed by test hook"


def test_escalate_directly_with_default_hook():
    page = Page(number=5, markdown="x", word_count=1)
    flag = PageFlag(page=5, reason=TABLE)
    j = PageJudgement(
        text_usable=False,
        content_missing=False,
        page_kind=PageKind.TABLE,
        confirmed_flags=[TABLE],
        reason="Cells merged.",
    )
    esc, kept = escalate(page, [flag], j)
    assert kept == [flag]
    assert esc.action == record_only_hook(page, j) == "would escalate to VLM: Cells merged."


@pytest.mark.parametrize(
    "usable,missing,bad", [(True, False, False), (False, False, True), (True, True, True)]
)
def test_judgement_bad_property(usable, missing, bad):
    j = PageJudgement(
        text_usable=usable, content_missing=missing, page_kind=PageKind.OTHER, reason="r"
    )
    assert j.bad is bad


def test_report_round_trips_through_json():
    parsed = doc([PageFlag(page=2, reason=IMG)])
    _, _, report = run(parsed, [verdict(missing=True, confirmed=["large_image_block"])])
    again = ParseQualityReport.model_validate_json(report.model_dump_json())
    assert again == report
    assert isinstance(next(iter(again.judgements)), int)


def test_judgement_rejects_unknown_fields_and_flags():
    with pytest.raises(ValueError):
        PageJudgement.model_validate({**judgement(), "severity": "high"})
    with pytest.raises(ValueError):
        PageJudgement.model_validate({**judgement(), "confirmed_flags": ["blurry"]})
