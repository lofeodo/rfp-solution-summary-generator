"""Splitting on the four committed RFPs. Each PDF is parsed once per session (~8 s each)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from rfp_agent.config import DATA_DIR
from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.heuristics import count_words
from rfp_agent.schemas import CHUNK_ID_RE, ParsedDocument, SectionKind, SplitDocument
from rfp_agent.splitting import split_document
from rfp_agent.splitting.chunker import MAX_CHUNK_WORDS, MIN_TAIL_WORDS, own_text, sentences
from rfp_agent.splitting.headings import detect_headings

RFPS = ["missouri", "NYESD", "colfax", "federal_way"]
GOLDEN = ["missouri", "NYESD"]  # one outlined, one not
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def parsed() -> dict[str, ParsedDocument]:
    return {name: parse_pdf(DATA_DIR / "rfps" / f"{name}.pdf") for name in RFPS}


@pytest.fixture(scope="session")
def split(parsed) -> dict[str, SplitDocument]:
    return {name: split_document(doc) for name, doc in parsed.items()}


def _section(split: SplitDocument, title: str):
    matches = [s for s in split.sections if s.title == title]
    assert len(matches) == 1, f"{title!r}: {len(matches)} sections"
    return matches[0]


def _children(split: SplitDocument, parent) -> list:
    return [s for s in split.sections if s.path[:-1] == parent.path and s.level == parent.level + 1]


def _own_texts(split: SplitDocument) -> list[str]:
    out = []
    for s in split.sections:
        for k, c in enumerate(s.chunks):
            out.append(own_text(c.text, s.chunks[k - 1].text if k else None))
    return out


@pytest.mark.parametrize("name", RFPS)
def test_deterministic_and_round_trips(parsed, split, name):
    again = split_document(parsed[name])
    assert again.model_dump_json() == split[name].model_dump_json()
    assert SplitDocument.model_validate_json(again.model_dump_json()) == again


@pytest.mark.parametrize("name", RFPS)
def test_every_word_lands_exactly_once(parsed, split, name):
    """Document words = heading-line words + chunk words, with the overlap removed."""
    doc = parsed[name]
    lines = {p.number: p.markdown.splitlines() for p in doc.pages}
    consumed = [
        lines[h.page][i] for h in detect_headings(doc) for i in h.consumed
    ]  # fmt: skip
    expected = Counter(w for p in doc.pages for w in p.markdown.split())
    got = Counter(w for line in consumed for w in line.split())
    got += Counter(w for text in _own_texts(split[name]) for w in text.split())
    assert got == expected


@pytest.mark.parametrize("name", RFPS)
def test_ids_pages_and_paths(split, name):
    doc = split[name]
    assert [s.id for s in doc.sections] == [f"S{i}" for i in range(1, len(doc.sections) + 1)]
    for s in doc.sections:
        assert s.level == len(s.path) and s.path[-1] == s.title
        assert [c.id for c in s.chunks] == [f"{s.id}.{k}" for k in range(1, len(s.chunks) + 1)]
        for c in s.chunks:
            assert re.match(CHUNK_ID_RE, c.id) and c.section_id == s.id
            assert c.section_path == s.path
            assert s.page_start <= c.page_start <= c.page_end <= s.page_end
            assert c.text.strip()
    starts = [s.page_start for s in doc.sections]
    assert starts == sorted(starts)


@pytest.mark.parametrize("name", RFPS)
def test_chunk_size_bound(split, name):
    """Over the cap only by a short merged tail, or when one table or sentence is longer."""
    for text in _own_texts(split[name]):
        words = count_words(text)
        if words <= MAX_CHUNK_WORDS + MIN_TAIL_WORDS:
            continue
        has_table = any(line.startswith("|") for line in text.splitlines())
        assert has_table or len(sentences(text)) == 1, (words, text[:200])


def test_missouri_outline_sections(parsed, split):
    doc = split["missouri"]
    located = [h for h in detect_headings(parsed["missouri"]) if h.source == "outline"]
    assert len(located) == 63  # of 64: "Expenses" is a table cell
    assert not [s for s in doc.sections if s.title == "Expenses"]
    sec5 = _section(doc, "SECTION (5): AGREEMENT REQUIREMENTS")
    kids = _children(doc, sec5)
    assert sec5.level == 1 and len(kids) == 25
    assert kids[0].title == "(A) MHTC's Representative"
    assert kids[-1].title == "(Y) Information Technology"
    assert (sec5.page_start, sec5.page_end) == (13, 18)
    reqs = sum(k.kind is SectionKind.REQUIREMENT_BEARING for k in kids)
    assert reqs >= 20  # 21 today; MBE/WBE, Cancellation, Venue and (X)'s preamble use "may"
    assert _section(doc, "SECTION (1): GENERAL DESCRIPTION AND BACKGROUND").chunks == []
    task = _section(doc, "Task 1: Project Management")
    assert task.path == [
        "SECTION (2): SCOPE OF WORK",
        "(B) Specific Requirements",
        "Task 1: Project Management",
    ]
    assert doc.sections[0].title == "Front matter"
    # A run-in label stays in the body: the chunk opens with it.
    assert _section(doc, "(A) Services").chunks[0].text.startswith("**(A) Services:**")


def test_colfax_outline_and_tabs(split):
    doc = split["colfax"]
    kids = [s.title for s in _children(doc, _section(doc, "4.2 PROPOSAL CONTENTS"))]
    assert kids[:3] == [
        "Tab 1: Response to Project Goals and Scope",
        "Tab 2: Proposed Strategy and Technical Approach",
        "Tab 3: Firm Information and Qualifications",
    ]
    # Form labels ("Name of Respondent:", "Reference 1 :") are body text, not sections.
    assert not [s for s in doc.sections if s.title.endswith(":")]
    assert _section(doc, "1.1 ORGANIZATION BACKGROUND").kind is SectionKind.NARRATIVE


def test_nyesd_headings_without_outline(split):
    doc = split["NYESD"]
    contractual = _section(doc, "X. CONTRACTUAL REQUIREMENTS")
    kids = [s.title.split(".")[0] for s in _children(doc, contractual)]
    assert kids == "i ii iii iv v vi vii viii ix x xi xii xiii xiv".split()
    criteria = [s.title for s in _children(doc, _section(doc, "VI. SELECTION CRITERIA"))]
    assert criteria[:5] == [
        "A. Firm Qualifications (15 Points)",
        "B. Experience (25 Points)",
        "C. Project Plan (30 Points)",
        "D. Cost of Services (20 Points)",
        "E. Diversity Practices (10 pts)",
    ]
    assert not [s for s in doc.sections if s.title.startswith("{")]
    assert _section(doc, "C. Project Plan (30 Points)").kind is SectionKind.REQUIREMENT_BEARING


def test_federal_way_promoted_section_4(split):
    doc = split["federal_way"]
    numbered = [s for s in doc.sections if s.title.startswith("SECTION ")]
    assert [s.title.split()[1] for s in numbered] == ["1", "2", "3", "4", "5", "6", "7"]
    assert len({s.level for s in numbered}) == 1
    assert _section(doc, "SECTION 2 - BACKGROUND").kind is SectionKind.NARRATIVE
    assert _section(doc, "SECTION 6 – REQUIREMENTS").kind is SectionKind.REQUIREMENT_BEARING


@pytest.mark.parametrize("name", GOLDEN)
def test_golden(split, name, request):
    path = FIXTURES / f"split_{name}.json"
    actual = split[name].model_dump_json(indent=2) + "\n"
    if request.config.getoption("--update-golden"):
        path.write_text(actual, encoding="utf-8", newline="\n")
    assert path.read_text(encoding="utf-8") == actual
