"""Splitting rules on literal strings: headings, outline location, promotion, chunks, kinds."""

from __future__ import annotations

import pytest

from rfp_agent.parsing.heuristics import count_words
from rfp_agent.schemas import CHUNK_ID_RE, OutlineEntry, Page, ParsedDocument, SectionKind
from rfp_agent.splitting import split_document
from rfp_agent.splitting.chunker import (
    MAX_CHUNK_WORDS,
    MIN_TAIL_WORDS,
    Block,
    blocks,
    chunk_blocks,
    overlap_of,
    own_text,
)
from rfp_agent.splitting.headings import (
    detect_headings,
    heading_paths,
    markdown_headings,
    scheme_of,
    title_key,
)
from rfp_agent.splitting.kind import section_kind


def doc(*pages: str, outline: list[OutlineEntry] | None = None) -> ParsedDocument:
    return ParsedDocument(
        source_path="x.pdf",
        pages=[
            Page(number=i, markdown=md, word_count=count_words(md))
            for i, md in enumerate(pages, start=1)
        ],
        outline=outline or [],
    )


def sentence(n: int, word: str = "word") -> str:
    """A sentence of exactly ``n`` words."""
    return "Start " + " ".join([word] * (n - 2)) + " end."


# --------------------------------------------------------------------------------------
# Headings
# --------------------------------------------------------------------------------------


def test_title_key_and_scheme():
    assert title_key("**(A) Services:**") == "a services"
    assert scheme_of("SECTION 4 – RFP EVALUATION") == "section"
    assert scheme_of("SECTION (1): GENERAL") == "section"
    assert scheme_of("(Y) Information Technology") == "paren"
    assert scheme_of("4.2 PROPOSAL CONTENTS") == "decimal"
    assert scheme_of("IV. SCOPE OF WORK") == "roman"
    assert scheme_of("iii. State Finance Law") == "roman_lower"
    assert scheme_of("B. Experience (25 Points)") == "letter"
    assert scheme_of("Task 3a: Offeror") == "keyword:task"
    assert scheme_of("Background") is None


@pytest.mark.parametrize(
    "line",
    [
        "## " + " ".join(["word"] * 21),  # too long
        "## This is a bold sentence.",  # ends with a period
        "#### **{In case of complex cost structure}**",  # does not start like a title
        "## **Name of Respondent:**",  # form label
    ],
)
def test_markdown_heading_demoted(line):
    assert markdown_headings({1: [line]}) == []


def test_numbered_heading_with_colon_kept():
    hs = markdown_headings({1: ["## **(A) SUBMISSION OF PROPOSALS:**"]})
    assert [h.title for h in hs] == ["(A) SUBMISSION OF PROPOSALS:"]


@pytest.mark.parametrize(
    "first,second,title",
    [
        ("## **SECTION (1):**", "## **GENERAL BACKGROUND**", "SECTION (1): GENERAL BACKGROUND"),
        ("## <u>Task 1</u>", "## **Project Management**", "Task 1: Project Management"),
        ("#### **Request for Proposals:**", "#### **Software**", "Request for Proposals: Software"),
    ],
)
def test_split_title_merged(first, second, title):
    hs = markdown_headings({1: [first, "", second, "", "Body text."]})
    assert [(h.title, h.consumed) for h in hs] == [(title, (0, 2))]


def test_split_title_needs_same_level_and_short_label():
    hs = markdown_headings({1: ["## Issued: August 8, 2025", "", "## Deadline: October 1"]})
    assert len(hs) == 2
    hs = markdown_headings({1: ["## SECTION (1):", "", "### Background"]})
    assert len(hs) == 2


def test_outline_located_on_heading_run_in_and_split_lines():
    page = "\n".join(
        [
            "## **SECTION (2): SCOPE**",
            "",
            "**(A) Services:** The Offeror shall provide services.",
            "",
            "- (B) **Specific Requirements:** The Offeror will report.",
            "",
            "|Expenses|",
            "|---|",
            "",
            "**EXHIBIT A:**",
            "",
            "**ANNUAL AFFIDAVIT**",
            "",
            "Form text here.",
        ]
    )
    outline = [
        OutlineEntry(level=1, title="SECTION (2): SCOPE", page=1),
        OutlineEntry(level=2, title="(A) Services", page=1),
        OutlineEntry(level=2, title="(B) Specific Requirements", page=1),
        OutlineEntry(level=1, title="Expenses", page=1),
        OutlineEntry(level=1, title="EXHIBIT A: ANNUAL AFFIDAVIT", page=1),
    ]
    hs = detect_headings(doc(page, outline=outline))
    assert [(h.title, h.line, h.consumed, h.raw_level) for h in hs] == [
        ("SECTION (2): SCOPE", 0, (0,), 1),
        ("(A) Services", 2, (), 2),  # run-in label: the line stays in the body
        ("(B) Specific Requirements", 4, (), 2),
        ("EXHIBIT A: ANNUAL AFFIDAVIT", 9, (9, 11), 1),  # "Expenses" is a table cell
    ]


def test_outline_entry_found_on_next_page_and_markdown_extras_nest():
    outline = [OutlineEntry(level=1, title="Scope of Work", page=1)]
    page2 = "## Scope of Work\n\n## Task 1\n\nText."
    hs = detect_headings(doc("Intro text.", page2, outline=outline))
    assert [(h.title, h.page, h.raw_level, h.source) for h in hs] == [
        ("Scope of Work", 2, 1, "outline"),
        ("Task 1", 2, 2, "markdown"),
    ]


def test_outline_search_skips_toc_pages():
    toc = "\n".join(f"Scope of Work ........ {i}" for i in range(5))
    outline = [OutlineEntry(level=1, title="Scope of Work", page=1)]
    hs = detect_headings(doc(toc, "**Scope of Work**\n\nText.", outline=outline))
    assert [(h.page, h.line) for h in hs] == [(2, 0)]


def test_bold_line_promoted_only_with_a_scheme_in_use():
    page = "\n".join(
        [
            "### **SECTION 3 - SCOPE**",
            "",
            "Scope text.",
            "",
            "**<u><mark>SECTION 4 - EVALUATION</mark></u>**",
            "",
            "**Not numbered bold line**",
            "",
            "- **A. Firm Qualifications**",
            "",
            "#### **B. Experience**",
        ]
    )
    hs = detect_headings(doc(page))
    assert [(h.title, h.raw_level, h.source) for h in hs] == [
        ("SECTION 3 - SCOPE", 3, "markdown"),
        ("SECTION 4 - EVALUATION", 3, "promoted"),
        ("A. Firm Qualifications", 4, "promoted"),  # takes the level of the next "B."
        ("B. Experience", 4, "markdown"),
    ]


def test_no_promotion_when_document_has_an_outline():
    outline = [OutlineEntry(level=1, title="SECTION 3 - SCOPE", page=1)]
    page = "## SECTION 3 - SCOPE\n\n**SECTION 4 - EVALUATION**\n\nText."
    assert [h.title for h in detect_headings(doc(page, outline=outline))] == ["SECTION 3 - SCOPE"]


def test_paths_skip_levels_and_toc_never_parents():
    hs = detect_headings(doc("# Title\n\n## TABLE OF CONTENTS\n\n### SECTION 1 - A\n\n#### Sub"))
    assert heading_paths(hs) == [
        ["Title"],
        ["Title", "TABLE OF CONTENTS"],
        ["Title", "SECTION 1 - A"],
        ["Title", "SECTION 1 - A", "Sub"],
    ]


# --------------------------------------------------------------------------------------
# Chunks
# --------------------------------------------------------------------------------------


def test_blocks_split_on_blank_lines_pages_and_tables():
    lines = [(1, "Para one."), (1, ""), (1, "|a|b|"), (1, "|---|---|"), (1, "After."), (2, "Next")]
    assert blocks(lines) == [
        Block("Para one.", 1, False),
        Block("|a|b|\n|---|---|", 1, True),
        Block("After.", 1, False),
        Block("Next", 2, False),
    ]


def test_chunks_respect_cap_and_carry_one_sentence():
    paras = [
        Block(f"{sentence(50, f'a{i}')} {sentence(50, f'b{i}')}", 1 + i // 2, False)
        for i in range(5)
    ]
    chunks = chunk_blocks(paras)
    assert [count_words(c.own) for c in chunks] == [300, 200]
    assert chunks[0].text == chunks[0].own
    assert chunks[1].text == f"{sentence(50, 'b2')}\n\n{chunks[1].own}"
    assert (chunks[0].page_start, chunks[0].page_end, chunks[1].page_start) == (1, 2, 2)
    assert own_text(chunks[1].text, chunks[0].text) == chunks[1].own


def test_short_tail_merges_into_previous_chunk():
    chunks = chunk_blocks([Block(sentence(290), 1, False), Block(sentence(30), 1, False)])
    assert len(chunks) == 1
    assert count_words(chunks[0].own) == 320 <= MAX_CHUNK_WORDS + MIN_TAIL_WORDS


def test_long_paragraph_cut_at_sentences():
    para = " ".join(sentence(40, f"s{i}") for i in range(10))  # 400 words
    chunks = chunk_blocks([Block(para, 1, False)])
    assert [count_words(c.own) for c in chunks] == [280, 120]
    assert chunks[1].own.startswith("Start s7")


def test_table_never_cut_and_passes_no_overlap():
    table = "\n".join(["|h|", "|---|"] + [f"|{' '.join(['cell'] * 20)}|" for _ in range(20)])
    chunks = chunk_blocks([Block(table, 1, True), Block(sentence(80), 1, False)])
    assert chunks[0].own == table
    assert overlap_of(chunks[0].text) is None
    assert chunks[1].text == chunks[1].own


def test_overlap_skips_overlong_sentence():
    assert overlap_of("Short one. " + sentence(70)) is None
    assert overlap_of("First. Second sentence here.") == "Second sentence here."


# --------------------------------------------------------------------------------------
# Kinds
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,kind",
    [
        ("The Offeror shall provide a work plan. " * 3, SectionKind.REQUIREMENT_BEARING),
        ("- Describe your approach.\n- Include a timeline.\n- List staff.", "req"),
        ("The City was founded in 1850 and has a population of 2,000 people. " * 5, "nar"),
        ("", "nar"),
    ],
)
def test_section_kind(text, kind):
    kind = {"req": SectionKind.REQUIREMENT_BEARING, "nar": SectionKind.NARRATIVE}.get(kind, kind)
    assert section_kind(text) is kind


# --------------------------------------------------------------------------------------
# Whole documents
# --------------------------------------------------------------------------------------


def test_split_document_ids_paths_front_matter_and_containers():
    split = split_document(
        doc(
            "Cover text.\n\n# SECTION 1 - SCOPE\n\n## (A) Services\n\nThe Offeror shall work.",
            "## (B) Reports\n\nReports are due monthly.",
        )
    )
    assert [(s.id, s.title, s.level, len(s.chunks)) for s in split.sections] == [
        ("S1", "Front matter", 1, 1),
        ("S2", "SECTION 1 - SCOPE", 1, 0),  # container with no own body
        ("S3", "(A) Services", 2, 1),
        ("S4", "(B) Reports", 2, 1),
    ]
    s2, s4 = split.sections[1], split.sections[3]
    assert (s2.page_start, s2.page_end) == (1, 2)
    assert s4.chunks[0].id == "S4.1"
    assert s4.chunks[0].section_path == ["SECTION 1 - SCOPE", "(B) Reports"]
    assert all(__import__("re").match(CHUNK_ID_RE, c) for c in split.chunk_ids())


def test_document_without_headings_is_all_front_matter():
    split = split_document(doc("Just text.", "More text."))
    assert [(s.title, s.page_start, s.page_end) for s in split.sections] == [("Front matter", 1, 2)]
