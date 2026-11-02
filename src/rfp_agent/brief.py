"""The pursuit brief (ST12a): what the pursuit team tells the drafter that the RFP does
not contain, such as win themes, the bidder's capabilities and credentials, team and
commercial constraints, what the client said informally, and things to avoid.

The brief is split into paragraphs that become citable chunks ``H1``, ``H2``..., shown to
the solution and risk agents next to the RFP evidence. A claim that rests on the brief
cites an ``H`` ID, so the rendered summary tells human-supplied evidence from RFP
evidence and the traceability rule holds for both. No LLM here.
"""

from __future__ import annotations

import re

from rfp_agent.schemas import Brief, BriefChunk, ChunkRef, EvidenceSource

BRIEF_SECTION_TITLE = "Pursuit brief"
NONE_PROVIDED = "None provided."

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
_WHITESPACE = re.compile(r"\s+")


def _is_heading(block: str) -> bool:
    """A one-line block that is a markdown heading or ends with a colon: it labels the
    paragraph that follows rather than saying anything citable on its own."""
    return "\n" not in block and (block.startswith("#") or block.endswith(":"))


def parse_brief(text: str | None) -> Brief | None:
    """Split ``text`` into ``H1..Hn`` chunks, one per paragraph; ``None`` when blank.

    Headings attach to the paragraph that follows them, so "Win themes:" and its bullet
    list are one chunk. A trailing heading with nothing after it is kept as its own
    chunk rather than dropped: the reviewer wrote it, so it stays on record.
    """
    if text is None:
        return None
    normalised = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalised:
        return None
    blocks = [b.strip() for b in _PARAGRAPH_BREAK.split(normalised)]
    blocks = [b for b in blocks if b]
    merged: list[str] = []
    pending_heading: str | None = None
    for block in blocks:
        if _is_heading(block):
            pending_heading = block if pending_heading is None else f"{pending_heading}\n{block}"
            continue
        merged.append(block if pending_heading is None else f"{pending_heading}\n{block}")
        pending_heading = None
    if pending_heading is not None:
        merged.append(pending_heading)
    chunks = [BriefChunk(id=f"H{i}", text=b) for i, b in enumerate(merged, start=1)]
    return Brief(text=normalised, chunks=chunks)


def brief_chunk_ids(brief: Brief | None) -> list[str]:
    return brief.chunk_ids() if brief is not None else []


def brief_chunk_refs(brief: Brief | None) -> list[ChunkRef]:
    """One ``ChunkRef`` per brief chunk, so the assembler and the renderer resolve ``H``
    citations like RFP ones."""
    if brief is None:
        return []
    return [
        ChunkRef(id=c.id, section_title=BRIEF_SECTION_TITLE, source=EvidenceSource.BRIEF)
        for c in brief.chunks
    ]


def format_brief(brief: Brief | None) -> str:
    """``H1: text`` lines for the prompts, or "None provided." when there is no brief."""
    if brief is None:
        return NONE_PROVIDED
    return "\n".join(f"{c.id}: {_WHITESPACE.sub(' ', c.text).strip()}" for c in brief.chunks)
