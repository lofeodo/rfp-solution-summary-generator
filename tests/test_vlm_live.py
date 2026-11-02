"""Live vision-model transcription (ST2). Paid: run with ``pytest -m llm``.

Federal Way page 5 holds the ERP environment table as an image; the library parser
yields only the surrounding prose. Missouri's affidavit pages 19 and 20 carry two
outline entries that the splitter locates by their text, so a transcription that
dropped the headings would merge sections. About $0.05 on Claude Sonnet.
"""

import pytest

from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.quality import run_quality_pass
from rfp_agent.parsing.vlm import get_vlm_model, make_vlm_hook, render_page_png, transcribe_page
from rfp_agent.splitting import split_document

pytestmark = pytest.mark.llm

SETTINGS = Settings()
needs_vlm_key = pytest.mark.skipif(
    SETTINGS.vlm_model.split(":")[0] != "anthropic" or not SETTINGS.anthropic_api_key,
    reason="needs an Anthropic VLM and ANTHROPIC_API_KEY",
)


@needs_vlm_key
def test_federal_way_page_5_table_is_transcribed(tmp_path):
    parsed = parse_pdf(DATA_DIR / "rfps" / "federal_way.pdf")
    page = parsed.pages[4]
    rec = RunRecorder("federal_way.pdf", SETTINGS.vlm_model, 0.0, runs_dir=tmp_path)
    with rec.activate():
        out = transcribe_page(
            render_page_png(DATA_DIR / "rfps" / "federal_way.pdf", 5, dpi=SETTINGS.vlm_dpi),
            page,
            reason="The environment table is inside an image.",
            title=parsed.title or "Federal Way",
            page_count=parsed.page_count,
            model=get_vlm_model(SETTINGS),
            settings=SETTINGS,
        )
    print(f"\n{out.markdown}\n-- notes: {out.notes}")
    assert "Eden" in out.markdown and "Quadrant" in out.markdown
    rows = [ln for ln in out.markdown.splitlines() if ln.lstrip().startswith("|")]
    assert len(rows) >= 5  # header, separator, at least three systems
    assert "Scope" in out.markdown  # the page's heading survived
    assert rec.totals().cost_usd > 0


@needs_vlm_key
@pytest.mark.skipif(not SETTINGS.deepseek_api_key, reason="the judge needs DEEPSEEK_API_KEY")
def test_missouri_sections_survive_the_affidavit_rewrites(tmp_path):
    pdf = DATA_DIR / "rfps" / "missouri.pdf"
    parsed = parse_pdf(pdf)
    before = split_document(parsed)
    rec = RunRecorder("missouri.pdf", SETTINGS.model, 0.0, runs_dir=tmp_path)
    with rec.activate():
        hook = make_vlm_hook(
            pdf,
            title=parsed.title or "Missouri",
            page_count=parsed.page_count,
            model=get_vlm_model(SETTINGS),
            settings=SETTINGS,
        )
        out, report = run_quality_pass(parsed, settings=SETTINGS, hook=hook)
    after = split_document(out)
    print(f"\n{[(t.page, t.library_words, t.vlm_words) for t in report.transcriptions]}")
    assert {t.page for t in report.transcriptions} <= {12, 19, 20}
    # No section is lost. More is fine: the first live run gained "APPLICANT AFFIDAVIT
    # FOR SOLE-PROPRIETORSHIP OR PARTNERSHIP" because the transcription of page 20
    # carries the heading the library text (an image) never had.
    titles_before = [s.title for s in before.sections]
    titles_after = [s.title for s in after.sections]
    print(f"sections {len(titles_before)} -> {len(titles_after)}")
    assert set(titles_before) <= set(titles_after)
    assert len(titles_after) >= len(titles_before)
