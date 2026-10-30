"""Parsing on the four committed RFPs. Each PDF is parsed once per session (~8 s each)."""

from __future__ import annotations

import re

import pytest

from rfp_agent.config import DATA_DIR
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.heuristics import count_words
from rfp_agent.schemas import FlagReason, ParsedDocument, ReferenceKind

RFPS = ["missouri", "NYESD", "colfax", "federal_way"]


@pytest.fixture(scope="session")
def parsed() -> dict[str, ParsedDocument]:
    return {name: parse_pdf(DATA_DIR / "rfps" / f"{name}.pdf") for name in RFPS}


def _flags(doc: ParsedDocument) -> dict[int, set[FlagReason]]:
    out: dict[int, set[FlagReason]] = {}
    for f in doc.flags:
        out.setdefault(f.page, set()).add(f.reason)
    return out


def _refs(doc: ParsedDocument) -> dict[str, bool]:
    return {
        r.name: r.present for r in doc.referenced_documents if r.kind is not ReferenceKind.HYPERLINK
    }


def _links(doc: ParsedDocument) -> list[str]:
    return [r.url for r in doc.referenced_documents if r.kind is ReferenceKind.HYPERLINK]


@pytest.mark.parametrize(
    "name,pages,outline,tables",
    [
        ("missouri", 20, 64, 8),
        ("NYESD", 27, 0, 2),
        ("colfax", 22, 29, 4),
        ("federal_way", 16, 0, 10),
    ],
)
def test_counts(parsed, name, pages, outline, tables):
    doc = parsed[name]
    assert (doc.page_count, len(doc.outline), len(doc.tables)) == (pages, outline, tables)


@pytest.mark.parametrize("name", RFPS)
def test_round_trip_and_invariants(parsed, name):
    doc = parsed[name]
    assert ParsedDocument.model_validate_json(doc.model_dump_json()) == doc
    assert [p.number for p in doc.pages] == list(range(1, doc.page_count + 1))
    for p in doc.pages:
        assert p.word_count == count_words(p.markdown)
        assert not re.search("[‘’“” ]", p.markdown)
    assert all(1 <= f.page <= doc.page_count for f in doc.flags)
    assert all(1 <= r.page <= doc.page_count for r in doc.referenced_documents)


def test_missouri_flags_images_and_references(parsed):
    doc = parsed["missouri"]
    flags = _flags(doc)
    assert flags[19] >= {FlagReason.LARGE_IMAGE_BLOCK, FlagReason.LOW_WORD_COUNT}
    assert flags[20] >= {FlagReason.LARGE_IMAGE_BLOCK, FlagReason.LOW_WORD_COUNT}
    assert FlagReason.BROKEN_TABLE in flags[12]  # merged-cell cost estimate table
    big = {i.page: i for i in doc.images if i.height > 400}
    assert set(big) == {19, 20}
    assert "AFFIDAVIT" in (big[19].caption or "")
    # Exhibits A and B are image-only forms: referenced, not present as text.
    assert _refs(doc) == {"Exhibit A": False, "Exhibit B": False}
    # The bold URL split across a table-cell line break is rejoined.
    assert "https://www.modot.org/research-requests-proposal" in doc.pages[5].markdown
    assert "https://www.w3.org/TR/WCAG21/" in _links(doc)
    assert doc.title == "TR202504 RFP Using AI /ML to Write Legal Land Descriptions"


def test_nyesd_references_and_no_flags(parsed):
    doc = parsed["NYESD"]
    assert doc.flags == []
    refs = _refs(doc)
    assert {"Schedule A", "Schedule B", "Appendix A", "Appendix B"} <= set(refs)
    links = _links(doc)
    assert len(links) >= 30
    assert len({re.sub(r"[^a-z0-9]", "", u.lower()) for u in links}) == len(links)
    assert doc.title.startswith("Request for Proposals Artificial Intelligence")


def test_colfax_attachments(parsed):
    doc = parsed["colfax"]
    assert _refs(doc) == {
        "Attachment A": True,
        "Attachment B": True,
        "Attachment C": True,
        "Attachment D": True,
        "Attachment E": False,
        "Attachment F": False,  # software requirements: "a separate document"
        "Attachment G": False,
    }
    assert {20, 21, 22} <= {p for p, r in _flags(doc).items() if FlagReason.LOW_WORD_COUNT in r}
    assert not any(re.search(r"Page \**\d+\** of \**22", p.markdown) for p in doc.pages)
    assert doc.title


def test_federal_way_image_table_and_headers(parsed):
    doc = parsed["federal_way"]
    flags = _flags(doc)
    assert FlagReason.LARGE_IMAGE_BLOCK in flags[5]  # ERP environment table is an image
    assert FlagReason.BROKEN_TABLE in flags[14]  # pricing template, merged cells
    assert [i.page for i in doc.images if i.height > 400] == [5]
    assert _refs(doc) == {"Exhibit A": True, "Exhibit B": True}
    assert not any("RFP for ERP Software" in p.markdown for p in doc.pages[1:])
    assert doc.pages[4].markdown.startswith("### **<u><mark>SECTION 3")
    assert doc.title.startswith("Request for Proposals Enterprise Resource Planning")


@pytest.mark.parametrize("name", RFPS)
def test_no_mailto_and_no_markup_in_urls(parsed, name):
    for url in _links(parsed[name]):
        assert url.startswith(("http://", "https://"))
        assert "**" not in url and "<" not in url
