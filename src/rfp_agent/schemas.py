"""Pydantic v2 schemas: the contract between every stage of the pipeline.

Conventions
-----------
- Every model forbids unknown fields, so a hallucinated key from an LLM fails validation
  and triggers the structured-call retry instead of being silently dropped.
- Closed sets are ``StrEnum``s so they serialise as plain strings.
- IDs are deterministic strings with a fixed shape, checked by regex:

  ======================  =========  ===========================================
  Artefact                Shape      Assigned by
  ======================  =========  ===========================================
  Section                 ``S3``     splitter, document order
  Chunk                   ``S3.2``   splitter: section ordinal, chunk ordinal
  Requirement             ``R001``   requirements extractor (after merge)
  Ambiguity               ``A01``    requirements extractor
  Gap                     ``G01``    requirements extractor
  Solution component      ``C01``    solution generator
  Risk                    ``K01``    risk assessor
  ======================  =========  ===========================================

- Traceability: every factual claim about the client or project is a ``Claim`` that
  cites at least one chunk ID, or is labelled an inference with the chunk IDs it was
  drawn from. Judgments (solution components, risks) cite the requirement or chunk IDs
  they respond to. ``validate_ids_exist`` is the helper agents use to enforce this.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------------------
# ID formats
# --------------------------------------------------------------------------------------

SECTION_ID_RE = r"^S\d+$"
CHUNK_ID_RE = r"^S\d+\.\d+$"
REQUIREMENT_ID_RE = r"^R\d{3,}$"
AMBIGUITY_ID_RE = r"^A\d{2,}$"
GAP_ID_RE = r"^G\d{2,}$"
COMPONENT_ID_RE = r"^C\d{2,}$"
RISK_ID_RE = r"^K\d{2,}$"

_CHUNK_ID = re.compile(CHUNK_ID_RE)


def validate_ids_exist(ids: Iterable[str], known: Iterable[str]) -> list[str]:
    """Return the IDs in ``ids`` that are not in ``known``, in first-seen order.

    Agents call this after an LLM response to reject citations of chunk or requirement
    IDs that do not exist. An empty list means every citation resolves.
    """
    known_set = set(known)
    unknown: list[str] = []
    for i in ids:
        if i not in known_set and i not in unknown:
            unknown.append(i)
    return unknown


# --------------------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------------------


class RequirementType(StrEnum):
    FUNCTIONAL = "functional"
    TECHNICAL = "technical"
    SECURITY_COMPLIANCE = "security_compliance"
    LEGAL_CONTRACTUAL = "legal_contractual"
    TIMELINE = "timeline"
    BUDGET_PRICING = "budget_pricing"
    SUBMISSION = "submission"
    OTHER = "other"


class Strictness(StrEnum):
    MANDATORY = "mandatory"  # shall / must / required
    DESIRED = "desired"  # should / preferred
    OPTIONAL = "optional"  # may / nice to have


STRICTNESS_RANK = {Strictness.OPTIONAL: 0, Strictness.DESIRED: 1, Strictness.MANDATORY: 2}


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Likelihood(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimKind(StrEnum):
    FACT = "fact"  # stated in the cited chunks
    INFERENCE = "inference"  # derived from the cited chunks, not stated


class SectionKind(StrEnum):
    NARRATIVE = "narrative"
    REQUIREMENT_BEARING = "requirement_bearing"


class FlagReason(StrEnum):
    LOW_WORD_COUNT = "low_word_count"
    LARGE_IMAGE_BLOCK = "large_image_block"
    BROKEN_TABLE = "broken_table"
    FRAGMENTED_LINES = "fragmented_lines"
    OTHER = "other"


class ReferenceKind(StrEnum):
    ATTACHMENT = "attachment"
    APPENDIX = "appendix"
    EXHIBIT = "exhibit"
    SCHEDULE = "schedule"
    ADDENDUM = "addendum"
    HYPERLINK = "hyperlink"
    OTHER = "other"


class RiskSource(StrEnum):
    RFP = "rfp"  # inherent in the RFP (timeline, vagueness, missing documents)
    SOLUTION = "solution"  # created by the proposed approach


class EscalationTrigger(StrEnum):
    CODE = "code"  # a heuristic flagged the page
    MODEL = "model"  # the LLM judge confirmed or raised it


class PageKind(StrEnum):
    """What a flagged page is, as the parse-quality judge sees it (S4)."""

    COVER = "cover"
    CONTENTS = "contents"
    FORM = "form"
    TABLE = "table"
    NARRATIVE = "narrative"
    BLANK = "blank"
    OTHER = "other"


# --------------------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------------------


class StrictModel(BaseModel):
    """Base for every schema: unknown fields are an error."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Parsing (S2, S4)
# --------------------------------------------------------------------------------------


class OutlineEntry(StrictModel):
    level: int = Field(ge=1)
    title: str
    page: int = Field(ge=1)


class Page(StrictModel):
    number: int = Field(ge=1, description="1-based page number")
    markdown: str
    word_count: int = Field(ge=0)


class Table(StrictModel):
    page: int = Field(ge=1)
    markdown: str


class ImageBlock(StrictModel):
    page: int = Field(ge=1)
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    caption: str | None = None


class ReferencedDocument(StrictModel):
    """A document the RFP points at but which is not inside the PDF."""

    name: str
    kind: ReferenceKind
    url: str | None = None
    page: int = Field(ge=1)
    section: str | None = None
    present: bool = Field(default=False, description="True if the content is in the PDF")


class PageFlag(StrictModel):
    page: int = Field(ge=1)
    reason: FlagReason
    detail: str | None = None


class ParsedDocument(StrictModel):
    source_path: str
    title: str | None = None
    outline: list[OutlineEntry] = Field(default_factory=list)
    pages: list[Page]
    tables: list[Table] = Field(default_factory=list)
    images: list[ImageBlock] = Field(default_factory=list)
    referenced_documents: list[ReferencedDocument] = Field(default_factory=list)
    flags: list[PageFlag] = Field(default_factory=list)

    @property
    def full_markdown(self) -> str:
        return "\n\n".join(p.markdown for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class PageJudgement(StrictModel):
    """The parse-quality judge's verdict on one flagged page (S4 LLM output contract)."""

    text_usable: bool = Field(
        description="True if the extracted text faithfully represents the text the page shows"
    )
    content_missing: bool = Field(
        description="True if the page likely holds content (an image of a table, a filled "
        "form, a chart) that the extracted text does not contain"
    )
    page_kind: PageKind
    confirmed_flags: list[FlagReason] = Field(
        default_factory=list,
        description="The heuristic flags on this page that describe a real problem",
    )
    reason: str = Field(description="One sentence explaining the verdict")

    @property
    def bad(self) -> bool:
        return not self.text_usable or self.content_missing


class ParseQualityReport(StrictModel):
    """What the parse-quality pass did (S4): one judgement per judged page and one
    escalation per flagged page. Pages whose judge call failed have no judgement."""

    judged_pages: list[int] = Field(default_factory=list)
    judgements: dict[int, PageJudgement] = Field(default_factory=dict)
    escalations: list[Escalation] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Splitting (S3)
# --------------------------------------------------------------------------------------


class Chunk(StrictModel):
    id: str = Field(pattern=CHUNK_ID_RE)
    section_id: str = Field(pattern=SECTION_ID_RE)
    section_path: list[str] = Field(min_length=1, description="Titles from root to leaf")
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text: str


class Section(StrictModel):
    id: str = Field(pattern=SECTION_ID_RE)
    title: str
    level: int = Field(ge=1)
    path: list[str] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    kind: SectionKind
    chunks: list[Chunk] = Field(default_factory=list)


class SplitDocument(StrictModel):
    sections: list[Section]

    def chunks(self) -> list[Chunk]:
        return [c for s in self.sections for c in s.chunks]

    def chunk_ids(self) -> list[str]:
        return [c.id for c in self.chunks()]

    def chunk_by_id(self, chunk_id: str) -> Chunk | None:
        for c in self.chunks():
            if c.id == chunk_id:
                return c
        return None


# --------------------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------------------


class Claim(StrictModel):
    """One factual assertion with its supporting chunk IDs."""

    text: str
    kind: ClaimKind = ClaimKind.FACT
    chunk_ids: list[str] = Field(min_length=1)


# --------------------------------------------------------------------------------------
# Requirements (S5)
# --------------------------------------------------------------------------------------


class Requirement(StrictModel):
    id: str = Field(pattern=REQUIREMENT_ID_RE)
    text: str = Field(description="Normalised statement of the requirement")
    type: RequirementType
    strictness: Strictness
    quote: str = Field(description="Verbatim quote from the RFP")
    chunk_ids: list[str] = Field(min_length=1)
    quote_verified: bool = Field(
        default=False, description="True once code found the quote in a cited chunk"
    )
    merged_from: list[str] = Field(
        default_factory=list, description="Pre-dedupe requirement IDs folded into this one"
    )
    conflicts_with: list[str] = Field(
        default_factory=list, description="Requirement IDs this one contradicts"
    )


class Ambiguity(StrictModel):
    id: str = Field(pattern=AMBIGUITY_ID_RE)
    description: str
    chunk_ids: list[str] = Field(min_length=1)
    requirement_ids: list[str] = Field(default_factory=list)


class Gap(StrictModel):
    """Something the RFP needs but does not provide, e.g. a referenced-but-absent document."""

    id: str = Field(pattern=GAP_ID_RE)
    description: str
    chunk_ids: list[str] = Field(default_factory=list)
    referenced_document: str | None = None


class RequirementsOutput(StrictModel):
    requirements: list[Requirement] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)

    def requirement_ids(self) -> list[str]:
        return [r.id for r in self.requirements]

    def mandatory(self) -> list[Requirement]:
        return [r for r in self.requirements if r.strictness is Strictness.MANDATORY]


# LLM output contracts for the extractor (S5). IDs and chunk citations are assigned by
# code, so the per-chunk reply carries none; the single-call reply cites chunk IDs, which
# code checks against the split document.


class ExtractedRequirement(StrictModel):
    text: str = Field(description="The requirement as one self-contained sentence")
    type: RequirementType
    strictness: Strictness
    quote: str = Field(description="Shortest verbatim span of the chunk stating it")


class ExtractedAmbiguity(StrictModel):
    description: str = Field(description="What is unclear and what a bidder would ask")
    requirement_indexes: list[int] = Field(
        default_factory=list,
        description="0-based positions in `requirements` of this reply that it affects",
    )


class ExtractedGap(StrictModel):
    description: str = Field(description="What the RFP needs that this text does not provide")
    referenced_document: str | None = Field(
        default=None, description="Name of the absent document, if the gap is one"
    )


class ChunkExtraction(StrictModel):
    """Reply for one chunk (per-chunk path)."""

    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    ambiguities: list[ExtractedAmbiguity] = Field(default_factory=list)
    gaps: list[ExtractedGap] = Field(default_factory=list)


class CitedRequirement(ExtractedRequirement):
    chunk_id: str = Field(pattern=CHUNK_ID_RE, description="The chunk the quote is from")


class CitedAmbiguity(ExtractedAmbiguity):
    chunk_ids: list[str] = Field(min_length=1)


class CitedGap(ExtractedGap):
    chunk_ids: list[str] = Field(default_factory=list)


class DocumentExtraction(StrictModel):
    """Reply for the whole document (single-call ablation path)."""

    requirements: list[CitedRequirement] = Field(default_factory=list)
    ambiguities: list[CitedAmbiguity] = Field(default_factory=list)
    gaps: list[CitedGap] = Field(default_factory=list)


class DedupeGroup(StrictModel):
    representative_id: str = Field(description="The most specific statement; kept")
    member_ids: list[str] = Field(
        min_length=1, description="Requirements folded into the representative"
    )


class RequirementConflict(StrictModel):
    requirement_ids: list[str] = Field(min_length=2)
    reason: str = Field(description="One sentence on how they contradict")


class DedupeOutput(StrictModel):
    """Reply of the fuzzy-dedupe grouping pass. Code merges and checks it (D6)."""

    groups: list[DedupeGroup] = Field(default_factory=list)
    conflicts: list[RequirementConflict] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Problem statement (S6)
# --------------------------------------------------------------------------------------


class ChunkSummaryDraft(StrictModel):
    """Stage-one LLM output contract (S6): what one chunk says about what is being built,
    for whom, why and under what constraints. The chunk ID is attached by code, never
    written by the model."""

    relevant: bool = Field(
        description="True if the chunk says anything about the client, the need, the "
        "deliverables, dates, money, constraints, evaluation or referenced documents"
    )
    summary: str = Field(
        description="Compact factual summary keeping every number, date, amount, name and "
        "referenced document; empty when the chunk is not relevant"
    )


class ChunkSummary(StrictModel):
    """Stage-one output for one chunk, tagged by code with the chunk ID. ``error`` holds
    the failure text when the summarising call failed after its retries; such a chunk is
    kept as not relevant so one flaky call cannot stop the stage."""

    chunk_id: str = Field(pattern=CHUNK_ID_RE)
    summary: str
    relevant: bool = True
    error: str | None = None


class ProblemStatement(StrictModel):
    client_situation: list[Claim] = Field(default_factory=list)
    goal: list[Claim] = Field(default_factory=list)
    success_criteria: list[Claim] = Field(default_factory=list)
    constraints: list[Claim] = Field(default_factory=list)

    def claims(self) -> list[Claim]:
        return self.client_situation + self.goal + self.success_criteria + self.constraints


# --------------------------------------------------------------------------------------
# Solution (S7)
# --------------------------------------------------------------------------------------


class SolutionComponent(StrictModel):
    id: str = Field(pattern=COMPONENT_ID_RE)
    title: str
    description: str
    requirement_ids: list[str] = Field(
        default_factory=list, description="Requirements this component addresses"
    )
    claims: list[Claim] = Field(default_factory=list)


class Coverage(StrictModel):
    """Computed by code from components' requirement_ids, never by the LLM."""

    mandatory_total: int = Field(ge=0)
    mandatory_covered: int = Field(ge=0)
    uncovered_requirement_ids: list[str] = Field(default_factory=list)


class Solution(StrictModel):
    summary: str = Field(description="Short narrative of the approach (a judgment)")
    components: list[SolutionComponent] = Field(default_factory=list)
    assumptions: list[Claim] = Field(default_factory=list)
    coverage: Coverage


# LLM output contract for the generator (S7). Component IDs and coverage are assigned by
# code; the per-call subclass built in ``agents/solution.py`` checks the cited IDs.


class ComponentDraft(StrictModel):
    title: str = Field(description="Short name of the component")
    description: str = Field(
        description="What is delivered and how it meets the requirements it addresses"
    )
    requirement_ids: list[str] = Field(
        default_factory=list,
        description="IDs of every requirement this component satisfies, copied from the list",
    )
    claims: list[Claim] = Field(
        default_factory=list,
        description="Facts about the client or project this component relies on, each "
        "citing chunk IDs shown in the problem statement or requirements",
    )


class SolutionDraft(StrictModel):
    summary: str = Field(description="Three to six sentences on the overall approach")
    components: list[ComponentDraft] = Field(default_factory=list)
    assumptions: list[Claim] = Field(
        default_factory=list,
        description="Inferences the approach rests on where the RFP is ambiguous or "
        "incomplete, each citing the chunk IDs of the ambiguity or gap it resolves",
    )


# --------------------------------------------------------------------------------------
# Risks (S8)
# --------------------------------------------------------------------------------------


class Risk(StrictModel):
    id: str = Field(pattern=RISK_ID_RE)
    title: str
    description: str
    severity: Severity
    likelihood: Likelihood
    justification: str
    source: RiskSource
    requirement_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    mitigation: str | None = None


class RiskAssessment(StrictModel):
    risks: list[Risk] = Field(default_factory=list)


# LLM output contract for the risk assessor (S8). Risk IDs are assigned by code after a
# severity/likelihood sort; the per-call subclass built in ``agents/risk.py`` checks the
# cited IDs, the count band and that every uncovered mandatory requirement is addressed.


class RiskDraft(StrictModel):
    title: str = Field(description="Short name of the risk")
    description: str = Field(description="What could go wrong and its consequence")
    severity: Severity = Field(description="Impact if it happens: low, medium or high")
    likelihood: Likelihood = Field(
        description="Chance it happens given the RFP and the solution as written"
    )
    justification: str = Field(description="Why this severity and likelihood")
    source: RiskSource = Field(
        description="rfp when the risk is inherent in the RFP, solution when the "
        "proposed approach creates it"
    )
    requirement_ids: list[str] = Field(
        default_factory=list,
        description="Requirement IDs the risk relates to, copied from the list",
    )
    chunk_ids: list[str] = Field(
        default_factory=list, description="Chunk IDs shown in the inputs that support the risk"
    )
    mitigation: str | None = Field(default=None, description="What the bidder would do about it")


class RiskAssessmentDraft(StrictModel):
    risks: list[RiskDraft] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Final assembly (S9)
# --------------------------------------------------------------------------------------


class ChunkRef(StrictModel):
    """Enough of a chunk to render a citation as 'section title, page'."""

    id: str = Field(pattern=CHUNK_ID_RE)
    section_title: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)


class SolutionSummary(StrictModel):
    """The JSON source of truth; markdown is rendered from this by code."""

    run_id: str
    source_path: str
    document_title: str | None = None
    generated_at: datetime
    model: str = Field(description="provider:model_id used for generation")
    chunks: list[ChunkRef] = Field(default_factory=list)
    requirements: RequirementsOutput
    problem_statement: ProblemStatement
    solution: Solution
    risks: RiskAssessment
    referenced_documents: list[ReferencedDocument] = Field(default_factory=list)
    flags: list[PageFlag] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Observability (S1)
# --------------------------------------------------------------------------------------


class NodeMetrics(StrictModel):
    node: str
    model: str
    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    cached_input_tokens: int = Field(ge=0, default=0)
    cost_usd: float = Field(ge=0, default=0.0)
    latency_s: float = Field(ge=0, default=0.0)
    retries: int = Field(ge=0, default=0, description="Structured-output retries used")
    started_at: datetime


class Escalation(StrictModel):
    page: int = Field(ge=1)
    triggered_by: EscalationTrigger
    confirmed_bad: bool
    action: str = Field(description="What happened, e.g. 'would escalate to VLM'")


class RunTotals(StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    retries: int = 0


class RunLog(StrictModel):
    run_id: str
    source_path: str
    started_at: datetime
    finished_at: datetime | None = None
    model: str
    temperature: float
    prompt_hashes: dict[str, str] = Field(
        default_factory=dict, description="prompt file name -> sha256"
    )
    nodes: list[NodeMetrics] = Field(default_factory=list)
    escalations: list[Escalation] = Field(default_factory=list)
    langfuse_trace_url: str | None = None

    def totals(self) -> RunTotals:
        t = RunTotals()
        for n in self.nodes:
            t.input_tokens += n.input_tokens
            t.output_tokens += n.output_tokens
            t.cached_input_tokens += n.cached_input_tokens
            t.cost_usd += n.cost_usd
            t.latency_s += n.latency_s
            t.retries += n.retries
        return t
