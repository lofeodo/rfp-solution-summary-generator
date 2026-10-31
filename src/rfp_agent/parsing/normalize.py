"""Text clean-up applied to every page before anything downstream sees it.

Page markdown is the ground truth for chunk text and for verbatim requirement quotes
(S5 checks quotes by string match), so normalisation is deliberately conservative:
it fixes characters that make string matching brittle (curly quotes, exotic spaces,
ligatures) and repairs URLs that pymupdf4llm splits inside table cells, and nothing else.
NFKC is not used because it also rewrites fractions, superscripts and similar symbols.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

_CHAR_MAP = {
    # quotes
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    # hyphens (en and em dashes are kept: they are real punctuation)
    "‐": "-",
    "‑": "-",
    # ligatures
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    # invisible characters
    "­": "",  # soft hyphen
    "​": "",  # zero-width space
    "‌": "",
    "‍": "",
    "﻿": "",
}
# Unicode space separators other than the plain space become a plain space.
_SPACES = "               　"
_CHAR_MAP.update({c: " " for c in _SPACES})
_TRANSLATE = str.maketrans(_CHAR_MAP)

# A bold URL broken across a table-cell line break:
#   **https://www.modot.org/research-**<br>**requests-proposal**
_SPLIT_BOLD_URL = re.compile(r"(https?://[^\s*<>|]*?)\*\*\s*(?:<br>|\n)\s*\*\*([^\s*<>|]+)")
_BLANK_RUN = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """NFC, ASCII quotes and spaces, ligatures expanded, split URLs joined, tidy blank lines."""
    text = unicodedata.normalize("NFC", text).translate(_TRANSLATE)
    text = join_split_urls(text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = _BLANK_RUN.sub("\n\n", text).strip("\n")
    return text + "\n" if text else ""


def join_split_urls(text: str) -> str:
    """Rejoin URLs that pymupdf4llm broke across a ``<br>`` inside a bold table cell."""
    while True:
        joined = _SPLIT_BOLD_URL.sub(r"\1\2", text)
        if joined == text:
            return text
        text = joined


# --------------------------------------------------------------------------------------
# Running headers and footers
# --------------------------------------------------------------------------------------

HEADER_FOOTER_CLASSES = {"page-header", "page-footer"}
MIN_REPEAT_PAGES = 3  # a header/footer text must recur on this many pages to be stripped
MARGIN_FRACTION = 0.12  # top/bottom band where a misclassified running header may sit


def header_key(text: str) -> str:
    """Comparable form of a header/footer: no digits, no markdown, collapsed whitespace."""
    text = re.sub(r"<[^>]+>|[*_#|]", " ", text)
    text = re.sub(r"\d+", " ", text)
    return " ".join(normalize_text(text).split()).lower()


def repeated_header_keys(pages: Sequence[tuple[str, Iterable[Mapping[str, Any]]]]) -> set[str]:
    """Keys of header/footer boxes whose text recurs on at least MIN_REPEAT_PAGES pages.

    ``pages`` holds ``(raw_text, page_boxes)`` per page, as pymupdf4llm returns them.
    """
    counts: Counter[str] = Counter()
    for raw, boxes in pages:
        keys = {
            header_key(raw[b["pos"][0] : b["pos"][1]])
            for b in boxes
            if b.get("class") in HEADER_FOOTER_CLASSES
        }
        counts.update(k for k in keys if k)
    return {k for k, n in counts.items() if n >= MIN_REPEAT_PAGES}


def strip_headers_footers(
    raw: str,
    boxes: Iterable[Mapping[str, Any]],
    repeated: set[str],
    page_height: float,
) -> str:
    """Remove running headers and footers from one page's markdown.

    Only boxes the layout model classed as header/footer, or boxes that start in the top
    or end in the bottom margin band (it sometimes classes the running header as
    ordinary text, merged with the heading below it), are
    candidates. A candidate is removed when its text is a bare page number or a repeated
    header/footer (see ``repeated_header_keys``). Two partial cases are handled too: a
    repeated header merged into the same box as the next heading loses only the header
    prefix, and a header-classed box holding a fragment of a repeated header (the header
    split into two boxes) is removed. A one-off sentence that the model misclassified
    survives, because its text does not repeat.
    """
    spans: list[tuple[int, int]] = []
    band = page_height * MARGIN_FRACTION
    for b in boxes:
        start, end = b["pos"]
        if end <= start:
            continue
        key = header_key(raw[start:end])
        y0, y1 = b["bbox"][1], b["bbox"][3]
        is_hf = b.get("class") in HEADER_FOOTER_CLASSES
        if not (is_hf or y0 <= band or y1 >= page_height - band):
            continue
        if key in repeated or not key or (is_hf and any(key in k for k in repeated)):
            spans.append((start, end))
            continue
        for k in repeated:
            if key.startswith(k + " "):
                m = _header_prefix_re(k).match(raw, start, end)
                if m:
                    spans.append((start, m.end()))
                break
    for start, end in sorted(spans, reverse=True):
        raw = raw[:start] + raw[end:]
    return raw


def _header_prefix_re(key: str) -> re.Pattern[str]:
    """Regex for a header's raw text from its key: its letters in order, anything
    non-letter (digits, markup, punctuation) between them, then trailing spaces, digits
    and pipes."""
    letters = re.findall(r"[a-z]+", key)
    return re.compile(r"\s*" + r"[^a-zA-Z]*".join(letters) + r"[\s\d|]*", re.IGNORECASE)
