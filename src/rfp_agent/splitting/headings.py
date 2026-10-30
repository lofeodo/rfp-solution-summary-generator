"""Section boundaries: where each heading sits in the page markdown and how deep it is.

Three sources, in order of authority:

1. The PDF outline, when the document has one. Outline entries carry a page but no
   position, so each title is located in that page's text (or the next page's). Many
   entries are not rendered as markdown headings at all but as a bold label that opens
   a paragraph (``**(A) Services:** The Offeror shall ...``); those are found too.
2. Markdown ``#`` lines from pymupdf4llm. Over-long lines and lines ending in a period
   are paragraphs that happened to be bold, not headings. A short label-only heading
   followed by another heading of the same level is one title split over two lines.
3. Without an outline only: a bold-only line whose numbering scheme ("SECTION 4",
   "A.") is already used by a detected heading is promoted to a heading at that level.

A heading may *consume* lines (its own title lines, removed from the body) or none (a
run-in label stays in the body, because the rest of the line is content).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from rfp_agent.parsing.references import clean_inline, is_toc_page, parse_heading
from rfp_agent.schemas import OutlineEntry, ParsedDocument

# A markdown heading longer than this, or ending in a period, is a bold paragraph.
MAX_HEADING_WORDS = 20
# A bold-only line longer than this is never promoted to a heading. It is generous
# because promotion already needs a whole-bold line and a numbering scheme in use;
# NYESD fuses two headings into one 33-word bold line ("viii. ...").
MAX_PROMOTED_WORDS = 40
# A bold run that is a prefix of an outline title must cover this share of the title.
MIN_PREFIX_SHARE = 0.6
# Headings that are a table of contents never become parents of what follows.
_TOC_RAW_LEVEL = 99

# A numbering label on its own: "SECTION (1):", "Task 3a", "EXHIBIT A:", "4.2", "IV."
LABEL_RE = re.compile(
    r"^(?:(?:section|task|tab|part|article|exhibit|attachment|appendix|schedule)\s+)?"
    r"(?:\(\w{1,3}\)|\d+(?:\.\d+)*[a-z]?|[IVX]+|[A-Z])[.:)]?:?$",
    re.IGNORECASE,
)
# Numbering schemes, checked in order; the first match names the scheme of a title.
_SCHEMES: list[tuple[str, re.Pattern[str]]] = [
    ("section", re.compile(r"^section\s+\(?\d+\)?", re.IGNORECASE)),
    ("keyword", re.compile(r"^(task|tab|exhibit|attachment|appendix|schedule)\s+\w", re.I)),
    ("paren", re.compile(r"^\([A-Za-z\d]{1,3}\)")),
    ("decimal", re.compile(r"^\d+(?:\.\d+)*\s")),
    ("roman", re.compile(r"^[IVX]+\.\s")),
    ("roman_lower", re.compile(r"^[ivx]+\.\s")),
    ("letter", re.compile(r"^[A-Z]\.\s")),
]
# A bold run at the start of a line, optionally after a list marker and a numbering
# label left outside the bold: "**(A) Services:**", "- (Y) **Information Technology:**".
_BOLD_RUN = re.compile(r"^(?:[-*]\s+)?(\(\w{1,3}\)\s*|\d+[.)]\s*|[A-Za-z][.)]\s*)?\*\*(.+?)\*\*")
_KEY_STRIP = re.compile(r"[^a-z0-9]+")


def title_key(text: str) -> str:
    """Lowercase letters and digits, single-spaced: the comparison key for titles."""
    return " ".join(_KEY_STRIP.sub(" ", clean_inline(text).lower()).split())


def scheme_of(title: str) -> str | None:
    """Numbering scheme of a title ("section", "roman", "keyword:task", ...), or None."""
    for name, pattern in _SCHEMES:
        m = pattern.match(title)
        if m:
            return f"keyword:{m.group(1).lower()}" if name == "keyword" else name
    return None


def is_label(title: str) -> bool:
    return bool(LABEL_RE.match(title.strip()))


def is_toc_title(title: str) -> bool:
    return title_key(title) in {"table of contents", "contents"}


@dataclass(frozen=True)
class Heading:
    """A section boundary at line ``line`` of page ``page`` (0-based line index)."""

    page: int
    line: int
    title: str
    raw_level: int  # outline or markdown level; only relative order matters
    consumed: tuple[int, ...] = field(default=())  # title lines on ``page`` not in the body
    source: str = "markdown"  # markdown | outline | promoted

    @property
    def pos(self) -> tuple[int, int]:
        return (self.page, self.line)


def page_lines(parsed: ParsedDocument) -> dict[int, list[str]]:
    return {p.number: p.markdown.splitlines() for p in parsed.pages}


def _is_table(line: str) -> bool:
    return line.lstrip().startswith("|")


def _next_nonblank(lines: Sequence[str], i: int) -> int | None:
    for j in range(i + 1, len(lines)):
        if lines[j].strip():
            return j
    return None


# --------------------------------------------------------------------------------------
# Markdown headings
# --------------------------------------------------------------------------------------


def _plausible_title(title: str) -> bool:
    """Not a bold paragraph: short, no closing period, starts like a title."""
    return (
        len(title.split()) <= MAX_HEADING_WORDS
        and not title.endswith(".")
        and (title[0].isalnum() or title[0] in '("')
    )


def markdown_headings(pages: dict[int, list[str]]) -> list[Heading]:
    """``#`` lines that are headings, with split titles merged.

    A heading ending in a colon with no numbering scheme ("Name of Respondent:") is a
    form label, not a heading, unless it merges with the next heading line.
    """
    out: list[Heading] = []
    for number, lines in pages.items():
        parsed = {}
        for i, raw in enumerate(lines):
            h = parse_heading(raw)
            if h and _plausible_title(h[1]):
                parsed[i] = h
        skip: set[int] = set()
        for i, (level, title) in parsed.items():
            if i in skip:
                continue
            consumed = [i]
            j = _next_nonblank(lines, i)
            if (
                j is not None
                and j in parsed
                and parsed[j][0] == level
                and (is_label(title) or title.endswith(":"))
                and len(title.split()) <= 4
            ):
                second = parsed[j][1]
                title = f"{title} {second}" if title.endswith(":") else f"{title}: {second}"
                consumed.append(j)
                skip.add(j)
            elif title.endswith(":") and scheme_of(title) is None:
                continue
            out.append(Heading(number, i, title, level, tuple(consumed)))
    return out


# --------------------------------------------------------------------------------------
# Outline entries located in the text
# --------------------------------------------------------------------------------------


def _bold_run(line: str) -> str | None:
    m = _BOLD_RUN.match(line.strip())
    return clean_inline((m.group(1) or "") + m.group(2)) if m else None


def _is_whole_bold(line: str) -> bool:
    bold = _bold_run(line)
    return bold is not None and title_key(bold) == title_key(line)


def _prefix_match(candidate: str, entry: str) -> bool:
    """Candidate key starts with the entry key, or covers most of it as a prefix."""
    if not candidate or not entry:
        return False
    if candidate.startswith(entry):
        return True
    return entry.startswith(candidate) and len(candidate) >= MIN_PREFIX_SHARE * len(entry)


def _match_line(
    entry: str, lines: Sequence[str], i: int, md: dict[int, Heading]
) -> tuple[int, ...] | None:
    """Consumed lines if outline key ``entry`` matches at line ``i``, else None."""
    line = lines[i]
    if not line.strip() or _is_table(line):
        return None
    if i in md:
        hk = title_key(md[i].title)
        if hk.startswith(entry) or (entry.startswith(hk) and is_label(md[i].title)):
            return md[i].consumed
        return None
    bold = _bold_run(line)
    if bold is not None:
        bk = title_key(bold)
        whole = bk == title_key(line)
        if _prefix_match(bk, entry):
            return (i,) if whole else ()
        j = _next_nonblank(lines, i)
        if whole and j is not None and _is_whole_bold(lines[j]):
            if title_key(f"{bold} {_bold_run(lines[j])}").startswith(entry):
                return (i, j)
    if title_key(line) == entry:
        return (i,)
    return None


def locate_outline(
    outline: Sequence[OutlineEntry],
    pages: dict[int, list[str]],
    md: Sequence[Heading],
    toc_pages: set[int],
) -> list[Heading]:
    """Outline entries found in the text, in order. Entries not found are dropped.

    Each entry is searched on its page, then the next, strictly after the previous
    match, never in table rows or on table-of-contents pages.
    """
    md_at = {(h.page, h.line): h for h in md}
    found: list[Heading] = []
    last = (0, -1)
    for entry in outline:
        key = title_key(entry.title)
        hit = None
        for number in (entry.page, entry.page + 1):
            if number not in pages or number in toc_pages or number < last[0]:
                continue
            lines = pages[number]
            md_here = {ln: h for (pg, ln), h in md_at.items() if pg == number}
            start = last[1] + 1 if number == last[0] else 0
            for i in range(start, len(lines)):
                consumed = _match_line(key, lines, i, md_here)
                if consumed is not None:
                    hit = Heading(number, i, entry.title, entry.level, consumed, "outline")
                    break
            if hit:
                break
        if hit:
            found.append(hit)
            last = hit.pos
    return found


# --------------------------------------------------------------------------------------
# Bold-line promotion (documents without an outline)
# --------------------------------------------------------------------------------------


def promote_bold_lines(pages: dict[int, list[str]], headings: Sequence[Heading]) -> list[Heading]:
    """Bold-only lines numbered like an existing heading, at that heading's level."""
    taken = {(h.page, ln) for h in headings for ln in (h.line, *h.consumed)}
    by_scheme: dict[str, list[Heading]] = {}
    for h in sorted(headings, key=lambda h: h.pos):
        s = scheme_of(h.title)
        if s:
            by_scheme.setdefault(s, []).append(h)
    out: list[Heading] = []
    for number, lines in pages.items():
        for i, line in enumerate(lines):
            if (number, i) in taken or _is_table(line) or not _is_whole_bold(line):
                continue
            title = _bold_run(line) or ""
            title = title.rstrip(":").strip()
            if not title or len(title.split()) > MAX_PROMOTED_WORDS:
                continue
            peers = by_scheme.get(scheme_of(title) or "", [])
            if not peers:
                continue
            before = [h for h in peers if h.pos < (number, i)]
            level = (before[-1] if before else peers[0]).raw_level
            out.append(Heading(number, i, title, level, (i,), "promoted"))
    return out


# --------------------------------------------------------------------------------------
# All headings
# --------------------------------------------------------------------------------------


def detect_headings(parsed: ParsedDocument) -> list[Heading]:
    """Every section boundary in document order."""
    pages = page_lines(parsed)
    md = markdown_headings(pages)
    if not parsed.outline:
        md = [
            Heading(h.page, h.line, h.title, _TOC_RAW_LEVEL, h.consumed, h.source)
            if is_toc_title(h.title)
            else h
            for h in md
        ]
        promoted = promote_bold_lines(pages, md)
        return sorted([*md, *promoted], key=lambda h: h.pos)

    toc_pages = {p.number for p in parsed.pages if is_toc_page(p.markdown)}
    located = locate_outline(parsed.outline, pages, md, toc_pages)
    replaced = {h.pos for h in located}
    covered = {(h.page, ln) for h in located for ln in h.consumed}
    extras = [h for h in md if h.pos not in replaced and h.pos not in covered]
    # A markdown heading missing from the outline nests one level under the outline
    # entry in effect where it appears.
    merged: list[Heading] = []
    current_level = 0
    for h in sorted([*located, *extras], key=lambda h: h.pos):
        if h.source == "outline":
            current_level = h.raw_level
            merged.append(h)
        else:
            merged.append(Heading(h.page, h.line, h.title, current_level + 1, h.consumed, h.source))
    return merged


def heading_paths(headings: Sequence[Heading]) -> list[list[str]]:
    """Title path from root to each heading; levels may skip, paths never do."""
    stack: list[Heading] = []
    paths: list[list[str]] = []
    for h in headings:
        while stack and stack[-1].raw_level >= h.raw_level:
            stack.pop()
        stack.append(h)
        paths.append([s.title for s in stack])
    return paths
