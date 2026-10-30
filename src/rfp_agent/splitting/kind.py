"""Narrative vs requirement-bearing, by cheap text cues.

This is a hint for downstream agents and readers, not a filter: S5 still extracts from
every chunk, so a false positive costs nothing. A section is requirement-bearing when
its own text holds at least one obligation cue: a word that makes an obligation
("shall", "must", "required") or a line that opens with an instruction to the
respondent ("- Describe how ..."). "Will" and "should" are not cues: background prose
uses them for plans and expectations as often as RFPs use them for obligations.
"""

from __future__ import annotations

import re

from rfp_agent.schemas import SectionKind

OBLIGATION_CUES = re.compile(
    r"\b(shall|must|required|requires|requirement|mandatory|at a minimum|no later than"
    r"|responsible for|prohibited)\b",
    re.IGNORECASE,
)
# A line that opens with an instruction to the respondent, after any list marker or
# markup: a proposal-content requirement even without a modal verb.
IMPERATIVE_LINE = re.compile(
    r"^[\W_]*(?:<[^>]+>)*\W*(describe|include|provide|submit|list|identify|explain"
    r"|demonstrate|attach|indicate|complete)\b",
    re.IGNORECASE | re.MULTILINE,
)


def section_kind(text: str) -> SectionKind:
    if OBLIGATION_CUES.search(text) or IMPERATIVE_LINE.search(text):
        return SectionKind.REQUIREMENT_BEARING
    return SectionKind.NARRATIVE
