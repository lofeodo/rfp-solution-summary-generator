"""Parse-quality escalation hook. S4 owns this file.

S2 flags suspicious pages with code heuristics (``heuristics.flag_page``). S4 replaces
this stub with an LLM judge of each flagged page and, for pages confirmed bad, a VLM
hook that in core only records "would escalate".
"""

from __future__ import annotations

from rfp_agent.schemas import Escalation, Page, PageFlag


def escalate(page: Page, flags: list[PageFlag]) -> Escalation | None:
    """Decide what to do with one flagged page. The S2 stub does nothing."""
    return None
