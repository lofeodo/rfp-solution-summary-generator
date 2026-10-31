"""A section body cut into citable chunks of at most a few hundred words.

Blocks are paragraphs (split on blank lines and page breaks) and tables (a run of ``|``
lines). Blocks are packed greedily up to ``MAX_CHUNK_WORDS``. A prose block over the
cap is cut at sentence ends; a table is never cut. A last chunk under
``MIN_TAIL_WORDS`` joins the previous one. Every chunk after the first repeats the last
sentence of the previous chunk, so a requirement that straddles a cut can still be
quoted from one chunk; a chunk that ends in a table passes nothing on.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from rfp_agent.parsing.heuristics import count_words

MAX_CHUNK_WORDS = 300
MIN_TAIL_WORDS = 50
# The repeated sentence is dropped when it is longer than this.
MAX_OVERLAP_WORDS = 60
BLOCK_SEP = "\n\n"

# Sentence end: terminal punctuation, whitespace, then something that starts a sentence.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"(*\-A-Z0-9])")


@dataclass(frozen=True)
class Block:
    text: str
    page: int
    is_table: bool


@dataclass(frozen=True)
class ChunkText:
    text: str  # what the chunk carries: overlap (if any) then its own text
    own: str  # the text that appears in this chunk only
    page_start: int
    page_end: int


@dataclass(frozen=True)
class _Piece:
    text: str
    words: int
    page: int
    is_table: bool
    sep: str  # joins this piece to the previous one in the same chunk


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def blocks(lines: Sequence[tuple[int, str]]) -> list[Block]:
    """Paragraphs and tables from ``(page, line)`` pairs in reading order."""
    out: list[Block] = []
    current: list[str] = []
    page = 0
    table = False

    def close() -> None:
        if current:
            out.append(Block("\n".join(current), page, table))
            current.clear()

    for number, raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close()
            continue
        line_is_table = _is_table_line(line)
        if current and (number != page or line_is_table != table):
            close()
        if not current:
            page, table = number, line_is_table
        current.append(line.strip() if line_is_table else line)
    close()
    return out


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(text) if s.strip()]


def overlap_of(chunk_text: str) -> str | None:
    """The sentence a chunk passes to the next one: its last sentence of prose."""
    last_line = chunk_text.rstrip().rsplit("\n", 1)[-1]
    if not last_line.strip() or _is_table_line(last_line):
        return None
    tail = sentences(last_line)[-1].strip()
    return tail if count_words(tail) <= MAX_OVERLAP_WORDS else None


def _pieces(block_list: Sequence[Block]) -> list[_Piece]:
    out: list[_Piece] = []
    for b in block_list:
        words = count_words(b.text)
        if b.is_table or words <= MAX_CHUNK_WORDS:
            out.append(_Piece(b.text, words, b.page, b.is_table, BLOCK_SEP))
            continue
        for k, s in enumerate(sentences(b.text)):
            out.append(_Piece(s, count_words(s), b.page, False, BLOCK_SEP if k == 0 else " "))
    return out


def chunk_blocks(block_list: Sequence[Block]) -> list[ChunkText]:
    groups: list[list[_Piece]] = []
    size = 0
    for piece in _pieces(block_list):
        if groups and size + piece.words <= MAX_CHUNK_WORDS:
            groups[-1].append(piece)
            size += piece.words
        else:
            groups.append([piece])
            size = piece.words
    if len(groups) > 1 and sum(p.words for p in groups[-1]) < MIN_TAIL_WORDS:
        groups[-2].extend(groups.pop())

    out: list[ChunkText] = []
    for group in groups:
        own = group[0].text + "".join(p.sep + p.text for p in group[1:])
        carried = overlap_of(out[-1].text) if out else None
        text = f"{carried}{BLOCK_SEP}{own}" if carried else own
        out.append(ChunkText(text, own, group[0].page, group[-1].page))
    return out


def own_text(text: str, previous: str | None) -> str:
    """Strip the sentence repeated from the previous chunk (inverse of the overlap)."""
    if previous is None:
        return text
    carried = overlap_of(previous)
    prefix = f"{carried}{BLOCK_SEP}" if carried else ""
    if prefix and text.startswith(prefix):
        return text[len(prefix) :]
    return text
