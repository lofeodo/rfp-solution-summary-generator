"""Cheap code heuristics that flag pages whose extracted text may be unusable.

Flags are suspicions, not verdicts: S4 sends each flagged page to an LLM judge. The
thresholds below were set by inspecting the four RFPs in ``data/rfps/`` (see
``docs/DECISIONS.md`` D16); they are constants so a reviewer can change them live.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from rfp_agent.schemas import FlagReason, PageFlag

# Fewer words than this on a page is suspicious (blank forms, cover sheets, image pages).
LOW_WORD_COUNT = 50
# An image covering at least this fraction of the page area probably holds content
# the text layer does not (Missouri p19-20 forms 0.54, Federal Way p5 table 0.42;
# cover logos are 0.08 to 0.14).
LARGE_IMAGE_FRACTION = 0.25
# Fragmented text: at least FRAGMENTED_MIN_LINES prose lines of at most
# FRAGMENTED_SHORT_WORDS words, making up at least FRAGMENTED_FRACTION of prose lines.
FRAGMENTED_MIN_LINES = 6
FRAGMENTED_SHORT_WORDS = 2
FRAGMENTED_FRACTION = 0.5
# A one-column table with at least this many rows, of which at least
# MERGED_CELL_MIN_BR contain <br>, is a multi-column table whose cells were merged.
MERGED_TABLE_MIN_ROWS = 3
MERGED_CELL_MIN_BR = 2

_TAG = re.compile(r"<[^>]+>")


def count_words(markdown: str) -> int:
    """Words in page markdown, ignoring HTML tags, table pipes and separator rows."""
    tokens = _TAG.sub(" ", markdown).replace("|", " ").split()
    return sum(1 for t in tokens if any(c.isalnum() for c in t))


def table_blocks(markdown: str) -> list[str]:
    """Contiguous runs of lines starting with ``|``: one markdown table each."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.lstrip().startswith("|"):
            current.append(line.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return ["\n".join(b) for b in blocks]


def _row_width(row: str) -> int:
    return max(row.count("|") - 1, 1)


def broken_table_reason(table: str) -> str | None:
    """Why a markdown table looks broken, or None if it looks fine."""
    rows = table.splitlines()
    widths = {_row_width(r) for r in rows}
    if len(widths) > 1:
        return f"ragged table: {len(rows)} rows with column counts {sorted(widths)}"
    merged = sum(1 for r in rows if "<br>" in r)
    if widths == {1} and len(rows) >= MERGED_TABLE_MIN_ROWS and merged >= MERGED_CELL_MIN_BR:
        return f"one-column table of {len(rows)} rows with {merged} merged cells"
    return None


def fragmented_lines_ratio(markdown: str) -> tuple[int, int]:
    """``(short_lines, prose_lines)`` over lines that are neither tables nor headings."""
    prose = [
        line.strip()
        for line in markdown.splitlines()
        if line.strip() and not line.lstrip().startswith(("|", "#"))
    ]
    short = [line for line in prose if count_words(line) <= FRAGMENTED_SHORT_WORDS]
    return len(short), len(prose)


def flag_page(page: int, markdown: str, image_fractions: Iterable[float]) -> list[PageFlag]:
    """Every heuristic flag that applies to one page, at most one per reason.

    ``image_fractions`` holds, for each image on the page, its area as a fraction of the
    page area.
    """
    flags: list[PageFlag] = []

    words = count_words(markdown)
    if words < LOW_WORD_COUNT:
        flags.append(PageFlag(page=page, reason=FlagReason.LOW_WORD_COUNT, detail=f"{words} words"))

    largest = max(image_fractions, default=0.0)
    if largest >= LARGE_IMAGE_FRACTION:
        flags.append(
            PageFlag(
                page=page,
                reason=FlagReason.LARGE_IMAGE_BLOCK,
                detail=f"image covers {largest:.0%} of the page",
            )
        )

    reasons = [r for t in table_blocks(markdown) if (r := broken_table_reason(t))]
    if reasons:
        flags.append(PageFlag(page=page, reason=FlagReason.BROKEN_TABLE, detail="; ".join(reasons)))

    short, prose = fragmented_lines_ratio(markdown)
    if short >= FRAGMENTED_MIN_LINES and short / prose >= FRAGMENTED_FRACTION:
        flags.append(
            PageFlag(
                page=page,
                reason=FlagReason.FRAGMENTED_LINES,
                detail=f"{short} of {prose} prose lines have at most "
                f"{FRAGMENTED_SHORT_WORDS} words",
            )
        )
    return flags
