"""``ParsedDocument`` to ``SplitDocument``: sections from headings, chunks per section.

Section IDs number sections in document order (``S1``, ``S2``, ...); chunk IDs number
chunks within their section (``S3.1``, ``S3.2``). The same parsed document always gives
the same IDs, which is what makes them citable. Text before the first heading becomes a
``Front matter`` section so no line is lost.
"""

from __future__ import annotations

from rfp_agent.parsing.references import is_toc_page
from rfp_agent.schemas import Chunk, ParsedDocument, Section, SectionKind, SplitDocument
from rfp_agent.splitting.chunker import blocks, chunk_blocks
from rfp_agent.splitting.headings import Heading, detect_headings, heading_paths, page_lines
from rfp_agent.splitting.kind import section_kind

FRONT_MATTER = "Front matter"


def _body(
    pages: dict[int, list[str]],
    start: tuple[int, int],
    end: tuple[int, int] | None,
    consumed: set[tuple[int, int]],
) -> list[tuple[int, str]]:
    """Lines from ``start`` (inclusive) to ``end`` (exclusive), minus heading lines."""
    out: list[tuple[int, str]] = []
    for number, lines in pages.items():
        for i, line in enumerate(lines):
            pos = (number, i)
            if pos < start or (end is not None and pos >= end) or pos in consumed:
                continue
            out.append((number, line))
    return out


def split_document(parsed: ParsedDocument) -> SplitDocument:
    pages = page_lines(parsed)
    headings = detect_headings(parsed)
    consumed = {(h.page, ln) for h in headings for ln in h.consumed}
    toc_pages = {p.number for p in parsed.pages if is_toc_page(p.markdown)}

    spans: list[tuple[str, int, list[str], int, list[tuple[int, str]]]] = []
    first = headings[0].pos if headings else None
    front = _body(pages, (0, 0), first, consumed)
    if any(line.strip() for _, line in front):
        spans.append((FRONT_MATTER, 1, [FRONT_MATTER], parsed.pages[0].number, front))
    paths = heading_paths(headings)
    for k, (h, path) in enumerate(zip(headings, paths, strict=True)):
        nxt: Heading | None = headings[k + 1] if k + 1 < len(headings) else None
        body = _body(pages, h.pos, nxt.pos if nxt else None, consumed)
        spans.append((h.title, len(path), path, h.page, body))

    sections: list[Section] = []
    for n, (title, level, path, page, body) in enumerate(spans, start=1):
        sid = f"S{n}"
        chunks = [
            Chunk(
                id=f"{sid}.{k}",
                section_id=sid,
                section_path=path,
                page_start=c.page_start,
                page_end=c.page_end,
                text=c.text,
            )
            for k, c in enumerate(chunk_blocks(blocks(body)), start=1)
        ]
        text = "\n\n".join(c.text for c in chunks)
        body_pages = {pg for pg, line in body if line.strip()}
        on_toc = bool(body_pages) and body_pages <= toc_pages
        kind = SectionKind.NARRATIVE if on_toc else section_kind(text)
        sections.append(
            Section(
                id=sid,
                title=title,
                level=level,
                path=path,
                page_start=page,
                page_end=max([page, *(c.page_end for c in chunks)]),
                kind=kind,
                chunks=chunks,
            )
        )
    _extend_page_ends(sections)
    return SplitDocument(sections=sections)


def _extend_page_ends(sections: list[Section]) -> None:
    """A section ends where its last descendant ends."""
    for i, s in enumerate(sections):
        for d in sections[i + 1 :]:
            if d.level <= s.level:
                break
            s.page_end = max(s.page_end, d.page_end)
