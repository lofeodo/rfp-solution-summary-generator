"""Quote matching that tolerates the markdown and typography the parser leaves behind.

The same ``normalise`` runs on both sides of every comparison, so a quote matches when it
is the same words in the same order, whatever the emphasis markers, table pipes, ``<br>``
tags (any HTML tag), quote style, dash style, case or whitespace.
"""

from __future__ import annotations

import re
import unicodedata

_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
    }
)
_TAG = re.compile(r"</?[A-Za-z][^>]*>")  # <br>, <u>, <mark>, <sup> left by the parser
_MARKUP = re.compile(r"[*_`|#>]+")
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    text = _TAG.sub(" ", text)
    text = _MARKUP.sub(" ", text)
    return _SPACE.sub(" ", text).strip().lower()


def find_quote(document: str, quote: str) -> bool:
    """True when ``quote`` occurs in ``document`` after normalising both."""
    q = normalise(quote)
    return bool(q) and q in normalise(document)
