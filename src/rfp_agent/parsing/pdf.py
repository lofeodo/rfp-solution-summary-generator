"""PDF to ``ParsedDocument``: pymupdf4llm for markdown, pymupdf for links and images.

Order of work per document:

1. pymupdf4llm renders every page to markdown in one call and returns its layout boxes.
2. Running headers and footers are stripped, then the text is normalised.
3. Code collects tables, images, page flags and referenced documents from the result.

OCR is switched off: output must not depend on whether Tesseract happens to be
installed, and image-only pages are S4's job (flag, judge, escalate to a VLM).
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf
import pymupdf4llm

from rfp_agent.parsing.heuristics import count_words, flag_page, table_blocks
from rfp_agent.parsing.normalize import (
    normalize_text,
    repeated_header_keys,
    strip_headers_footers,
)
from rfp_agent.parsing.references import (
    clean_inline,
    document_lines,
    document_references,
    hyperlinks,
    mark_present,
    parse_heading,
)
from rfp_agent.schemas import ImageBlock, OutlineEntry, Page, PageFlag, ParsedDocument, Table

# Images smaller than this (points, either side) are rules, bullets or spacers.
MIN_IMAGE_SIDE = 20.0
# A caption is the nearest text block within this distance (points) above or below an image.
CAPTION_MAX_GAP = 40.0
# Text blocks may overlap the image edge by this much (points) and still count as captions.
CAPTION_OVERLAP = 5.0
# The metadata title is trusted when this fraction of its words appear on page 1.
TITLE_WORD_OVERLAP = 0.6


def parse_pdf(path: str | Path) -> ParsedDocument:
    """Parse one PDF into the ``ParsedDocument`` contract every later step reads."""
    path = Path(path)
    with pymupdf.open(path) as doc:
        outline = [
            OutlineEntry(level=level, title=clean_inline(normalize_text(title)), page=page)
            for level, title, page, *_ in doc.get_toc()
            if page >= 1 and title.strip()
        ]
        chunks = pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)
        repeated = repeated_header_keys([(c["text"], c["page_boxes"]) for c in chunks])

        pages: list[Page] = []
        tables: list[Table] = []
        images: list[ImageBlock] = []
        flags: list[PageFlag] = []
        annotations: dict[int, list[tuple[str, str]]] = {}

        for number, (fitz_page, chunk) in enumerate(zip(doc, chunks, strict=True), start=1):
            height = fitz_page.rect.height
            raw = strip_headers_footers(chunk["text"], chunk["page_boxes"], repeated, height)
            markdown = normalize_text(raw)
            pages.append(Page(number=number, markdown=markdown, word_count=count_words(markdown)))
            tables.extend(Table(page=number, markdown=t) for t in table_blocks(markdown))

            page_images = _images(fitz_page, number)
            images.extend(page_images)
            page_area = fitz_page.rect.width * height
            flags.extend(
                flag_page(number, markdown, (i.width * i.height / page_area for i in page_images))
            )
            words = fitz_page.get_text("words")
            annotations[number] = [
                (link["uri"], _anchor_text(link["from"], words))
                for link in fitz_page.get_links()
                if link.get("uri")
            ]

        title = pick_title(doc.metadata.get("title"), pages[0].markdown if pages else "")

    lines = document_lines(pages, outline)
    refs = document_references(lines, pages)
    mark_present(refs, lines)
    refs.extend(hyperlinks(lines, annotations))

    return ParsedDocument(
        source_path=str(path),
        title=title,
        outline=outline,
        pages=pages,
        tables=tables,
        images=images,
        referenced_documents=refs,
        flags=flags,
    )


def _images(fitz_page: pymupdf.Page, number: int) -> list[ImageBlock]:
    """Image blocks on the page, clipped to the page, with a nearby caption if any."""
    seen: set[tuple[int, int, int, int]] = set()
    blocks: list[ImageBlock] = []
    text_blocks = [b for b in fitz_page.get_text("blocks") if b[6] == 0]
    for info in fitz_page.get_image_info():
        rect = pymupdf.Rect(info["bbox"]) & fitz_page.rect
        if rect.is_empty or rect.width < MIN_IMAGE_SIDE or rect.height < MIN_IMAGE_SIDE:
            continue
        key = (round(rect.x0), round(rect.y0), round(rect.x1), round(rect.y1))
        if key in seen:
            continue
        seen.add(key)
        blocks.append(
            ImageBlock(
                page=number,
                width=round(rect.width, 1),
                height=round(rect.height, 1),
                caption=_caption(rect, text_blocks),
            )
        )
    return blocks


def _caption(rect: pymupdf.Rect, text_blocks: list) -> str | None:
    """Text of the closest text block just above or below the image, on one line."""
    best: tuple[float, str] | None = None
    for x0, y0, x1, y1, text, *_ in text_blocks:
        if x1 < rect.x0 or x0 > rect.x1:  # no horizontal overlap
            continue
        if y1 <= rect.y0 + CAPTION_OVERLAP:
            gap = max(rect.y0 - y1, 0.0)
        elif y0 >= rect.y1 - CAPTION_OVERLAP:
            gap = max(y0 - rect.y1, 0.0)
        else:
            continue
        caption = clean_inline(normalize_text(text))
        if gap > CAPTION_MAX_GAP or not re.search(r"[A-Za-z]{2}", caption):
            continue  # too far, or a page number / stray symbol
        if best is None or gap < best[0]:
            best = (gap, caption[:200])
    return best[1] if best else None


def _anchor_text(rect: pymupdf.Rect, words: list) -> str:
    """Whole words under a link rectangle (most of each word's height inside it)."""
    picked = []
    for x0, y0, x1, y1, word, *_ in words:
        if x1 <= rect.x0 or x0 >= rect.x1:
            continue
        overlap = min(y1, rect.y1) - max(y0, rect.y0)
        if overlap >= 0.5 * (y1 - y0):
            picked.append(word)
    return normalize_text(" ".join(picked)).strip()


def pick_title(metadata_title: str | None, first_page: str) -> str | None:
    """The PDF metadata title if page 1 confirms it, else the first heading on page 1."""
    if metadata_title and metadata_title.strip():
        title = clean_inline(normalize_text(metadata_title))
        words = re.findall(r"[a-z0-9]+", title.lower())
        page_words = set(re.findall(r"[a-z0-9]+", first_page.lower()))
        if words and sum(w in page_words for w in words) / len(words) >= TITLE_WORD_OVERLAP:
            return title
    for line in first_page.splitlines():
        heading = parse_heading(line)
        if heading:
            return heading[1]
    return None
