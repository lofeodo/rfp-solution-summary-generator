"""Documents the RFP points at: hyperlinks and attachment/appendix/exhibit references.

Nothing is fetched (DECISIONS D10). Each reference records the page and the section
heading it first appears under, and whether its content is actually inside the PDF.
A referenced-but-absent document is a gap for S5 and a risk for S8.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from rfp_agent.parsing.heuristics import count_words
from rfp_agent.schemas import OutlineEntry, Page, ReferencedDocument, ReferenceKind

# A document section counts as present in the PDF when its heading is followed by at
# least this many words before the next heading of the same or higher level. Cover
# pages that say "provided separately" or "intentionally left blank" fall below it.
PRESENT_MIN_WORDS = 40
# A page is a table of contents when this fraction of its non-empty lines has a dot leader.
TOC_LINE_FRACTION = 0.6

_KINDS = {
    "attachment": ReferenceKind.ATTACHMENT,
    "appendix": ReferenceKind.APPENDIX,
    "exhibit": ReferenceKind.EXHIBIT,
    "schedule": ReferenceKind.SCHEDULE,
    "addendum": ReferenceKind.ADDENDUM,
    "addenda": ReferenceKind.ADDENDUM,
}
# The keyword is case-insensitive; the designator must be one capital letter or a
# number, so "Schedule of", "Addendum to" and "SCHEDULE OF" do not match.
DOC_REF_RE = re.compile(
    r"\b(?i:(attachment|appendix|exhibit|schedule|addendum|addenda))s?\s+"
    r"(?:(?i:no)\.?\s*)?([A-Z]|\d{1,2})\b(?![\w-])"
)
URL_RE = re.compile(r"https?://[^\s<>()\[\]*|\"'`]+")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_DOT_LEADER = re.compile(r"\.{5,}")
_MARKUP = re.compile(r"<[^>]+>|[*_`]")


def clean_inline(text: str) -> str:
    """Strip inline markdown and HTML tags and collapse whitespace."""
    return " ".join(_MARKUP.sub(" ", text).split())


def parse_heading(line: str) -> tuple[int, str] | None:
    """``(level, title)`` for a markdown heading line, else None."""
    m = _HEADING_RE.match(line.strip())
    if not m:
        return None
    title = clean_inline(m.group(2))
    return (len(m.group(1)), title) if title else None


def _name_key(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def is_toc_page(markdown: str) -> bool:
    lines = [line for line in markdown.splitlines() if line.strip()]
    if not lines:
        return False
    return sum(1 for line in lines if _DOT_LEADER.search(line)) / len(lines) >= TOC_LINE_FRACTION


@dataclass(frozen=True)
class Line:
    """One line of the document with the section heading in effect where it appears."""

    page: int
    text: str
    section: str | None
    heading: tuple[int, str] | None  # (level, title) when the line is a heading


def document_lines(pages: Sequence[Page], outline: Sequence[OutlineEntry] = ()) -> list[Line]:
    """Every line of the document, tagged with its section.

    The section is the nearest preceding markdown heading; before the first heading it
    falls back to the PDF outline entry in effect for that page.
    """
    lines: list[Line] = []
    current: str | None = None
    for page in pages:
        for raw in page.markdown.splitlines():
            heading = parse_heading(raw)
            if heading:
                current = heading[1]
            section = current or _outline_section(outline, page.number)
            lines.append(Line(page.number, raw, section, heading))
    return lines


def _outline_section(outline: Sequence[OutlineEntry], page: int) -> str | None:
    title = None
    for entry in outline:
        if entry.page <= page:
            title = entry.title
    return title


# --------------------------------------------------------------------------------------
# Attachment / appendix / exhibit / schedule / addendum references
# --------------------------------------------------------------------------------------


def document_references(lines: Sequence[Line], pages: Sequence[Page]) -> list[ReferencedDocument]:
    """One reference per distinct named document, at its first non-TOC occurrence."""
    toc_pages = {p.number for p in pages if is_toc_page(p.markdown)}
    found: dict[str, ReferencedDocument] = {}
    from_toc: set[str] = set()
    for line in lines:
        for m in DOC_REF_RE.finditer(line.text):
            word = m.group(1).lower()
            kind = _KINDS[word]
            name = f"{'Addendum' if kind is ReferenceKind.ADDENDUM else word.title()} {m.group(2)}"
            on_toc = line.page in toc_pages
            if name in found and not (name in from_toc and not on_toc):
                continue
            found[name] = ReferencedDocument(
                name=name, kind=kind, page=line.page, section=line.section
            )
            if on_toc:
                from_toc.add(name)
            else:
                from_toc.discard(name)
    return list(found.values())


def mark_present(refs: Iterable[ReferencedDocument], lines: Sequence[Line]) -> None:
    """Set ``present`` on non-hyperlink references whose section body is in the PDF."""
    for ref in refs:
        if ref.kind is ReferenceKind.HYPERLINK:
            continue
        ref.present = section_word_count(ref.name, lines) >= PRESENT_MIN_WORDS


def section_word_count(name: str, lines: Sequence[Line]) -> int:
    """Most words under any heading titled ``name`` (e.g. "Attachment F: ..."), else 0."""
    key = _name_key(name)
    best = 0
    for i, line in enumerate(lines):
        if not line.heading:
            continue
        level, title = line.heading
        title_key = _name_key(title)
        if title_key != key and not title_key.startswith(key + " "):
            continue
        words = 0
        for nxt in lines[i + 1 :]:
            if nxt.heading and nxt.heading[0] <= level:
                break
            words += count_words(nxt.text)
        best = max(best, words)
    return best


# --------------------------------------------------------------------------------------
# Hyperlinks
# --------------------------------------------------------------------------------------


def _url_key(url: str) -> str:
    """Letters and digits only, lower-cased, scheme dropped.

    Text extraction mangles long URLs at line breaks (a hyphen or a space lost, a
    ``</u>`` inserted); comparing on this key treats those variants as one link.
    """
    return re.sub(r"[^a-z0-9]+", "", url.lower().split("://", 1)[-1])


def _is_http(url: str) -> bool:
    return url.lower().startswith(("http://", "https://"))


def hyperlinks(
    lines: Sequence[Line],
    annotations: dict[int, list[tuple[str, str]]],
) -> list[ReferencedDocument]:
    """One reference per distinct http(s) URL, at its first page.

    ``annotations`` maps page number to ``(uri, anchor_text)`` from the PDF's link
    annotations, which carry the real target. Plain-text URLs in the markdown are added
    only when no annotation anywhere in the document covers them: a plain-text URL whose
    key equals or prefixes an annotated URL's key is the same link, mangled or broken
    across lines. ``mailto:`` and other schemes are skipped: contact addresses are not
    documents.
    """
    by_page: dict[int, list[Line]] = {}
    for line in lines:
        by_page.setdefault(line.page, []).append(line)
    annotated_keys = [
        _url_key(uri) for links in annotations.values() for uri, _ in links if _is_http(uri)
    ]

    found: dict[str, ReferencedDocument] = {}
    pages = sorted(set(by_page) | set(annotations))
    for page in pages:
        page_lines = by_page.get(page, [])
        candidates: list[tuple[str, str]] = [
            (uri.strip(), anchor) for uri, anchor in annotations.get(page, []) if _is_http(uri)
        ]
        for line in page_lines:
            for m in URL_RE.finditer(line.text):
                url = m.group(0).rstrip(".,;:")
                key = _url_key(url)
                if not any(a.startswith(key) for a in annotated_keys):
                    candidates.append((url, ""))
        for url, anchor in candidates:
            key = _url_key(url)
            if key in found:
                continue
            section = _section_for(page_lines, url, anchor)
            name = clean_inline(anchor)[:200] or url
            found[key] = ReferencedDocument(
                name=name, kind=ReferenceKind.HYPERLINK, url=url, page=page, section=section
            )
    return list(found.values())


def _section_for(page_lines: Sequence[Line], url: str, anchor: str) -> str | None:
    """Section of the first line mentioning the URL or its anchor text, else of the page start."""
    needles = [n for n in (url, clean_inline(anchor)[:40]) if n]
    for line in page_lines:
        text = clean_inline(line.text)
        if any(n in text or n in line.text for n in needles):
            return line.section
    return page_lines[0].section if page_lines else None
