"""What a scored run looks like on disk (``evals/results/<label>/scores/<rfp>-<k>.json``).

Every per-item record carries the item's own text, so a score file reads without the run
directory it came from. Judge fields are ``None`` when the run was scored with
``--no-judge`` or when the judge call for that batch failed (counted in
``JudgeCost.failures``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rfp_agent.schemas import RunTotals

GroundingVerdictValue = Literal["supported", "partially", "unsupported"]
ChecklistStatus = Literal["covered", "partial", "missing"]
MatchTier = Literal["code", "judge", "none"]


class ScoreModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Requirements
# --------------------------------------------------------------------------------------


class MatchRecord(ScoreModel):
    """One gold requirement and the extracted requirements that state it."""

    gold_id: str
    gold_text: str
    gold_type: str
    gold_strictness: str
    gold_page: int | None = None
    quote_verifiable: bool = True
    matched_ids: list[str] = Field(default_factory=list)
    tier: MatchTier = "none"
    best_id: str | None = Field(default=None, description="Pair used for type/strictness")
    best_type: str | None = None
    best_strictness: str | None = None
    reason: str | None = Field(default=None, description="Judge's reason for a judge-tier match")


class RequirementVerdict(ScoreModel):
    """Precision verdict on one extracted requirement."""

    id: str
    text: str
    type: str
    strictness: str
    chunk_ids: list[str]
    supported: bool | None = None
    is_requirement: bool | None = None
    in_scope: bool | None = None
    reason: str | None = None

    @property
    def correct(self) -> bool | None:
        if self.supported is None or self.is_requirement is None:
            return None
        return self.supported and self.is_requirement


class RequirementScores(ScoreModel):
    extracted: int
    by_type: dict[str, int]
    by_strictness: dict[str, int]
    gold: int
    gold_reachable: int
    matched_gold: int
    matched_gold_reachable: int
    matched_by_code: int
    matched_by_judge: int
    recall: float
    recall_reachable: float
    type_accuracy: float | None
    strictness_accuracy: float | None
    type_confusion: dict[str, dict[str, int]] = Field(
        default_factory=dict, description="gold type -> extracted type -> count"
    )
    precision: float | None = None
    in_scope_share: float | None = None
    judged: int = 0
    unverified_quotes: int = 0
    matches: list[MatchRecord] = Field(default_factory=list)
    verdicts: list[RequirementVerdict] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Grounding
# --------------------------------------------------------------------------------------


class GroundingItem(ScoreModel):
    """One cited assertion: a problem claim, a component claim, an assumption or a risk."""

    where: str = Field(description="e.g. problem.goal[0], solution.C01.claims[0], risks.K01")
    output: Literal["problem", "solution", "risks"]
    text: str
    kind: str = Field(description="fact | inference | assumption | risk")
    cited: list[str] = Field(default_factory=list, description="Chunk and requirement IDs")
    dangling: list[str] = Field(default_factory=list, description="Cited IDs that do not exist")
    missing_entities: list[str] = Field(
        default_factory=list, description="Numbers and names not found in the cited text"
    )
    verdict: GroundingVerdictValue | None = None
    reasonable_inference: bool | None = None
    reason: str | None = None


class GroundingTally(ScoreModel):
    items: int = 0
    uncited: int = 0
    dangling_ids: int = 0
    entity_misses: int = Field(0, description="Items with at least one missing entity")
    judged: int = 0
    supported: int = 0
    partially: int = 0
    unsupported: int = 0
    unreasonable_inferences: int = 0

    @property
    def unsupported_claims(self) -> int:
        """The roadmap's unsupported-claim count: partially plus unsupported."""
        return self.partially + self.unsupported


class GroundingScores(ScoreModel):
    by_output: dict[str, GroundingTally]
    items: list[GroundingItem] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Problem statement, solution, risks
# --------------------------------------------------------------------------------------


class ChecklistVerdict(ScoreModel):
    gold_id: str
    fact: str
    quote_verifiable: bool = True
    status: ChecklistStatus | None = None
    claim: str | None = Field(default=None, description="e.g. goal[2]")
    reason: str | None = None


class ProblemScores(ScoreModel):
    mode: str
    claims: dict[str, int]
    facts: int
    inferences: int
    checklist_total: int
    checklist_covered: int | None = None
    checklist_partial: int | None = None
    checklist_coverage: float | None = None
    checklist: list[ChecklistVerdict] = Field(default_factory=list)


class RubricScore(ScoreModel):
    score: int = Field(ge=1, le=5)
    reason: str


class ComponentRecord(ScoreModel):
    id: str
    title: str
    description: str
    requirement_ids: list[str]


class PairVerdict(ScoreModel):
    """Does the component actually address the requirement it cites?"""

    component_id: str
    requirement_id: str
    requirement_text: str
    in_scope: bool
    addressed: bool | None = None
    reason: str | None = None


class SolutionScores(ScoreModel):
    components: int
    assumptions: int
    rounds: int
    cited_total: int
    cited_covered: int
    cited_coverage: float
    stored_coverage_agrees: bool
    judged_covered: int | None = None
    judged_coverage: float | None = None
    rubric: dict[str, RubricScore] = Field(default_factory=dict)
    calendar_components: list[str] = Field(default_factory=list)
    component_records: list[ComponentRecord] = Field(default_factory=list)
    pairs: list[PairVerdict] = Field(default_factory=list)


class RiskVerdict(ScoreModel):
    id: str
    title: str
    severity: str
    likelihood: str
    source: str
    judge_severity: str | None = None
    judge_likelihood: str | None = None
    reason: str | None = None


class FindingVerdict(ScoreModel):
    id: str = Field(description="F1, F2, ...")
    kind: Literal["conflict", "absent_document", "flagged_page", "uncovered_requirement"]
    label: str
    code_covered: bool
    code_risk_ids: list[str] = Field(default_factory=list)
    judge_covered: bool | None = None
    judge_risk_ids: list[str] = Field(default_factory=list)


class RiskScores(ScoreModel):
    risks: int
    severity: dict[str, int]
    likelihood: dict[str, int]
    source: dict[str, int]
    severity_agreement: float | None = None
    likelihood_agreement: float | None = None
    findings: int = 0
    findings_code_covered: int = 0
    findings_judge_covered: int | None = None
    risk_verdicts: list[RiskVerdict] = Field(default_factory=list)
    finding_verdicts: list[FindingVerdict] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Cost and the whole run
# --------------------------------------------------------------------------------------


class StageCost(ScoreModel):
    stage: str
    status: str
    wall_s: float
    calls: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cost_usd: float
    retries: int


class RetryRecord(ScoreModel):
    node: str
    retries: int
    last_error: str | None = Field(
        default=None, description="None for logs written before the F7 fix"
    )


class CostScores(ScoreModel):
    calls: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cached_share: float
    cost_usd: float
    wall_s: float
    retries: int
    stages: list[StageCost] = Field(default_factory=list)
    retried: list[RetryRecord] = Field(default_factory=list)


class JudgeCost(ScoreModel):
    model: str
    calls: int = 0
    failures: int = Field(0, description="Judge batches that failed after retries")
    totals: RunTotals = Field(default_factory=RunTotals)
    per_node: dict[str, RunTotals] = Field(default_factory=dict)


class RunScores(ScoreModel):
    rfp: str
    run: str = Field(description="Run key within the label, e.g. '1'")
    run_dir: str
    run_id: str
    model: str
    scored_at: datetime
    judged: bool
    requirements: RequirementScores
    problem: ProblemScores
    solution: SolutionScores
    risks: RiskScores
    grounding: GroundingScores
    cost: CostScores
    judge: JudgeCost | None = None

    @property
    def key(self) -> str:
        return f"{self.rfp}-{self.run}"
