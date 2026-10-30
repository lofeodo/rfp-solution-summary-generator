"""Parsing rules on literal strings: fast, no PDF involved."""

from __future__ import annotations

import pytest

from rfp_agent.parsing.heuristics import (
    broken_table_reason,
    count_words,
    flag_page,
    table_blocks,
)
from rfp_agent.parsing.normalize import (
    header_key,
    join_split_urls,
    normalize_text,
    repeated_header_keys,
    strip_headers_footers,
)
from rfp_agent.parsing.pdf import pick_title
from rfp_agent.parsing.quality import escalate
from rfp_agent.parsing.references import (
    DOC_REF_RE,
    document_lines,
    document_references,
    hyperlinks,
    is_toc_page,
    mark_present,
    parse_heading,
)
from rfp_agent.schemas import FlagReason, OutlineEntry, Page, ReferenceKind


def _page(n: int, md: str) -> Page:
    return Page(number=n, markdown=md, word_count=count_words(md))


# --------------------------------------------------------------------------------------
# normalize
# --------------------------------------------------------------------------------------


def test_normalize_quotes_spaces_ligatures():
    raw = "“Offeror’s” pro­posal ﬁnal – dash  \n\n\n\nnext"
    assert normalize_text(raw) == '"Offeror\'s" proposal final – dash\n\nnext\n'


def test_normalize_empty_page():
    assert normalize_text("  \n\n ") == ""


def test_join_split_bold_url_in_table_cell():
    cell = "|at**https://www.modot.org/research-**<br>**requests-proposal**.|"
    assert join_split_urls(cell) == "|at**https://www.modot.org/research-requests-proposal**.|"


def test_join_split_url_leaves_normal_bold_alone():
    text = "**Date**<br>**Action**"
    assert join_split_urls(text) == text


def test_header_key_ignores_digits_and_markup():
    assert header_key("Page **6** of **22**") == header_key("Page **7** of **22**") == "page of"
    assert header_key("13") == ""


def _box(cls: str, start: int, end: int, y0: float, y1: float) -> dict:
    return {"class": cls, "pos": (start, end), "bbox": (50, y0, 550, y1)}


def test_strip_repeated_headers_and_page_numbers():
    header = "City of X - RFP 5 | Page\n"
    body = "Real text on the page.\n"
    footer = "5\n"
    raw = header + body + footer
    boxes = [
        _box("text", 0, len(header), 60, 70),  # misclassified running header, in the margin
        _box("text", len(header), len(header) + len(body), 100, 700),
        _box("page-footer", len(header) + len(body), len(raw), 745, 755),
    ]
    repeated = {header_key("City of X - RFP 9 | Page")}
    assert strip_headers_footers(raw, boxes, repeated, 792) == body


def test_strip_header_merged_with_heading_keeps_heading():
    raw = "City of X – RFP   7 | P a g e **<u>SECTION 4</u>**\n\nBody.\n"
    boxes = [_box("page-header", 0, raw.index("\n\nBody") + 2, 60, 86)]
    repeated = {header_key("City of X – RFP 3 | P a g e")}
    assert strip_headers_footers(raw, boxes, repeated, 792) == "**<u>SECTION 4</u>**\n\nBody.\n"


def test_strip_header_split_into_two_boxes():
    left, right = "City of X – RFP\n\n", "11 | P a g e\n\n"
    raw = left + right + "## Heading\n"
    boxes = [
        _box("page-header", 0, len(left), 60, 71),
        _box("page-header", len(left), len(left) + len(right), 60, 71),
    ]
    repeated = {header_key("City of X – RFP 3 | P a g e")}
    assert strip_headers_footers(raw, boxes, repeated, 792) == "## Heading\n"


def test_strip_keeps_one_off_header_text():
    raw = "A sentence the model called a footer.\n"
    boxes = [_box("page-footer", 0, len(raw), 745, 755)]
    assert strip_headers_footers(raw, boxes, set(), 792) == raw


def test_repeated_header_keys_needs_three_pages():
    pages = [(f"Page {i} of 9\n", [_box("page-footer", 0, 12, 745, 755)]) for i in range(1, 4)]
    assert repeated_header_keys(pages) == {"page of"}
    assert repeated_header_keys(pages[:2]) == set()


# --------------------------------------------------------------------------------------
# heuristics
# --------------------------------------------------------------------------------------


def test_count_words_skips_table_syntax_and_tags():
    md = "|**Date**|**Action**|\n|---|---|\n|6/26/2024|Posts <br> RFP|"
    assert count_words(md) == 5


def test_table_blocks_split_on_non_table_lines():
    md = "intro\n|a|b|\n|---|---|\n|1|2|\n\ntext\n|x|\n|---|\n"
    assert table_blocks(md) == ["|a|b|\n|---|---|\n|1|2|", "|x|\n|---|"]


def test_broken_table_ragged():
    assert "ragged" in broken_table_reason("|a|b|\n|---|---|\n|1|2|3|")


def test_broken_table_merged_one_column():
    table = "|**Cost**|\n|---|\n|**Expenses**<br>**Amount**|\n|Salaries|\n|F&A<br>Cost|"
    assert "merged" in broken_table_reason(table)


def test_good_table_not_broken():
    assert broken_table_reason("|a|b|\n|---|---|\n|1|2|") is None
    assert broken_table_reason("|Only|\n|---|\n|one<br>br|") is None


def test_flag_page_low_words_and_large_image():
    flags = flag_page(19, "## EXHIBIT A\n\nAffidavit form.", [0.54])
    assert [f.reason for f in flags] == [FlagReason.LOW_WORD_COUNT, FlagReason.LARGE_IMAGE_BLOCK]
    assert flags[1].detail == "image covers 54% of the page"


def test_flag_page_small_logo_not_flagged():
    text = " ".join(["word"] * 80)
    assert flag_page(1, text, [0.1]) == []


def test_flag_page_fragmented_lines():
    text = "\n".join(["Name", "Title", "Phone 1", "Email", "Signature", "Date"] + ["word " * 60])
    reasons = [f.reason for f in flag_page(3, text, [])]
    assert reasons == [FlagReason.FRAGMENTED_LINES]


def test_flag_page_broken_table():
    table = "|**Cost**|\n|---|\n|**Expenses**<br>**Amount**|\n|Salaries|\n|F&A<br>Cost|"
    text = table + "\n\n" + "word " * 60
    assert [f.reason for f in flag_page(12, text, [])] == [FlagReason.BROKEN_TABLE]


# --------------------------------------------------------------------------------------
# references
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("see Attachment F for software", [("Attachment", "F")]),
        ("APPENDIX B and Schedule A apply", [("APPENDIX", "B"), ("Schedule", "A")]),
        ("Exhibit A – Pricing", [("Exhibit", "A")]),
        ("Addendum No. 2 was issued", [("Addendum", "2")]),
        ("the Schedule of payments", []),
        ("SCHEDULE OF EVENTS", []),
        ("Addendum to the contract", []),
        ("Attachment A-1", []),
    ],
)
def test_doc_ref_regex(text, expected):
    assert [(m.group(1), m.group(2)) for m in DOC_REF_RE.finditer(text)] == expected


def test_parse_heading_strips_markup():
    assert parse_heading("### **<u><mark>SECTION 3 - SCOPE</mark></u>**") == (
        3,
        "SECTION 3 - SCOPE",
    )
    assert parse_heading("**bold only**") is None


def test_is_toc_page():
    assert is_toc_page("1.0 PURPOSE ........ 4\n2.0 GENERAL ........ 5\nContents")
    assert not is_toc_page("Ordinary text.\nMore text ....... with a leader.\nEnd.")


def _doc_pages() -> list[Page]:
    return [
        _page(1, "Contents\nATTACHMENT A: PRICING ........ 3\nATTACHMENT F: SOFTWARE ........ 4"),
        _page(2, "# Scope\n\nComplete Attachment A and Attachment F. See https://x.gov/a-b-c."),
        _page(3, "# ATTACHMENT A: PRICING\n\n" + "price line words " * 20),
        _page(4, "# ATTACHMENT F: SOFTWARE\n\nThis is a separate document provided by the City."),
    ]


def test_document_references_first_non_toc_occurrence_and_section():
    pages = _doc_pages()
    lines = document_lines(pages)
    refs = {r.name: r for r in document_references(lines, pages)}
    assert set(refs) == {"Attachment A", "Attachment F"}
    assert (refs["Attachment A"].page, refs["Attachment A"].section) == (2, "Scope")
    assert refs["Attachment F"].kind is ReferenceKind.ATTACHMENT


def test_mark_present_needs_heading_and_body():
    pages = _doc_pages()
    lines = document_lines(pages)
    refs = document_references(lines, pages)
    mark_present(refs, lines)
    assert {r.name: r.present for r in refs} == {"Attachment A": True, "Attachment F": False}


def test_section_falls_back_to_outline():
    pages = [_page(1, "No heading here, Exhibit B applies.")]
    outline = [OutlineEntry(level=1, title="Terms", page=1)]
    refs = document_references(document_lines(pages, outline), pages)
    assert refs[0].section == "Terms"


def test_hyperlinks_annotations_plain_text_and_mailto():
    pages = _doc_pages()
    lines = document_lines(pages)
    annotations = {
        2: [("https://x.gov/a-b-c", "x.gov link"), ("mailto:rfp@x.gov", "rfp@x.gov")],
        4: [("https://other.gov/doc.pdf", "")],
    }
    refs = hyperlinks(lines, annotations)
    assert [(r.url, r.name, r.page) for r in refs] == [
        ("https://x.gov/a-b-c", "x.gov link", 2),
        ("https://other.gov/doc.pdf", "https://other.gov/doc.pdf", 4),
    ]
    assert refs[0].section == "Scope"


def test_hyperlinks_drop_mangled_plain_text_duplicate():
    pages = [_page(1, "Form at https://x.gov/file-your-form?redirect"), _page(2, "text")]
    annotations = {2: [("https://x.gov/file-your-form?redirect=legacy", "form")]}
    refs = hyperlinks(document_lines(pages), annotations)
    assert [r.url for r in refs] == ["https://x.gov/file-your-form?redirect=legacy"]


def test_plain_text_url_without_annotation_is_kept():
    pages = [_page(1, "Posted at https://example.org/rfp.")]
    refs = hyperlinks(document_lines(pages), {})
    assert [r.url for r in refs] == ["https://example.org/rfp"]


# --------------------------------------------------------------------------------------
# title and S4 hook
# --------------------------------------------------------------------------------------


def test_pick_title_trusts_confirmed_metadata():
    assert pick_title("Using AI to Write", "Using AI to write things") == "Using AI to Write"


def test_pick_title_falls_back_to_first_heading():
    page = "intro\n# **Request for Proposals ERP**\n## Issued"
    assert pick_title("Describe the specific collection process", page) == (
        "Request for Proposals ERP"
    )
    assert pick_title(None, page) == "Request for Proposals ERP"
    assert pick_title("", "no headings") is None


def test_escalate_stub_returns_none():
    page = _page(19, "x")
    assert escalate(page, flag_page(19, "x", [0.5])) is None
