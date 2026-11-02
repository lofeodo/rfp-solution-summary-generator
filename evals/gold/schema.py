"""Gold-label format.

Gold labels are the reference S12 scores the pipeline against. They are a separate schema
from the pipeline's ``Requirement``: gold has no chunk IDs (chunking may change, gold must
not), records where each label came from, and uses its own ID prefix (``GR``/``GC``) so a
gold ID can never be confused with a pipeline ``R001``.

Scope is "core only" (DECISIONS D23): requirements that shape the solution. S12 therefore
measures recall against gold and precision with a judge.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from rfp_agent.schemas import RequirementType, StrictModel, Strictness

GOLD_REQUIREMENT_ID_RE = r"^GR\d{3,}$"
GOLD_CHECKLIST_ID_RE = r"^GC\d{2,}$"
CHECKLIST_MIN, CHECKLIST_MAX = 8, 12


class GoldSource(StrEnum):
    DRAFT = "draft"  # as drafted by the model, unchanged
    CORRECTED = "corrected"  # drafted, then edited by hand
    HAND = "hand"  # added by hand (missed by the draft, or image-only content)


class GoldRequirement(StrictModel):
    id: str = Field(pattern=GOLD_REQUIREMENT_ID_RE)
    text: str = Field(description="Normalised statement of the requirement")
    type: RequirementType
    strictness: Strictness
    quote: str = Field(description="Verbatim span of the parsed RFP text")
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    source: GoldSource = GoldSource.DRAFT
    quote_verifiable: bool = Field(
        default=True,
        description="False only when the content is not in the parsed text (image-only)",
    )
    note: str | None = None


class GoldChecklistItem(StrictModel):
    id: str = Field(pattern=GOLD_CHECKLIST_ID_RE)
    fact: str = Field(description="A fact a correct problem statement must mention")
    quote: str | None = Field(default=None, description="Verbatim supporting span")
    page: int | None = Field(default=None, ge=1)
    source: GoldSource = GoldSource.DRAFT
    quote_verifiable: bool = True
    note: str | None = None


class GoldSet(StrictModel):
    rfp: str = Field(description="File stem under data/rfps/")
    source_pdf: str
    drafted_with: str | None = Field(default=None, description="provider:model of the draft")
    drafted_at: str | None = None
    requirements: list[GoldRequirement] = Field(default_factory=list)
    checklist: list[GoldChecklistItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> GoldSet:
        for label, ids in (
            ("requirement", [r.id for r in self.requirements]),
            ("checklist", [c.id for c in self.checklist]),
        ):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                raise ValueError(f"duplicate {label} ids: {dupes}")
        return self

    def checklist_size_ok(self) -> bool:
        """Final gold has 8 to 12 checklist items; drafts and partial files may not."""
        return CHECKLIST_MIN <= len(self.checklist) <= CHECKLIST_MAX


def requirement_id(n: int) -> str:
    return f"GR{n:03d}"


def checklist_id(n: int) -> str:
    return f"GC{n:02d}"
