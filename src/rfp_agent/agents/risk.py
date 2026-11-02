"""Risk assessor (S8): risks inherent in the RFP and risks created by the solution.

The model sees the problem statement (S6), the requirements, ambiguities and gaps (S5),
the solution with its coverage (S7) and a block of findings that code detected for
certain; never the RFP text. It returns a ``RiskAssessmentDraft``. Three things are
owned by code:

- **Findings.** ``detect_findings`` collects the mandatory requirements the solution
  left uncovered, the requirement conflict pairs, the referenced documents that are not
  in the PDF (hyperlinks excluded) and the parse flags the caller passes, plus the number
  of budget requirements. They are shown to the model under their own heading.
- **Validation.** The schema of the call is a per-call subclass of
  ``RiskAssessmentDraft`` whose validator rejects fewer than ``MIN_RISKS`` or more than
  ``MAX_RISKS`` risks, a requirement ID outside the list, a chunk ID outside the
  evidence, and a draft in which some uncovered mandatory requirement is cited by no
  risk, so ``structured_call`` feeds the exact problem back and retries (the S6/S7
  pattern). Conflicts, absent documents and flagged pages are advice only: a ``Risk``
  has no field that can cite them.
- **Numbering.** Risks are stably sorted by severity then likelihood, both descending,
  and numbered ``K01…``, so K01 is the top risk and the JSON order equals the rendered
  table order (S9 sorts the same way).

One structured call, node ``risk_assess``; no revision loop.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from pydantic import Field, create_model, model_validator

from rfp_agent.agents.solution import (
    NONE,
    claim_line,
    format_ambiguities,
    format_gaps,
    format_problem,
    format_requirements,
)
from rfp_agent.agents.solution import allowed_chunk_ids as _solution_chunk_ids
from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import Prompt, get_chat_model, load_prompt, structured_call
from rfp_agent.observability import current_recorder
from rfp_agent.schemas import (
    Likelihood,
    PageFlag,
    ProblemStatement,
    ReferencedDocument,
    ReferenceKind,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Risk,
    RiskAssessment,
    RiskAssessmentDraft,
    Severity,
    Solution,
    StrictModel,
    validate_ids_exist,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODE = "risk_assess"
PROMPT = "risk"
MIN_RISKS = 3
MAX_RISKS = 15
SUBMISSION_HEADING = "Submission requirements (how and when the proposal is delivered)"

_LEVEL_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


class Findings(StrictModel):
    """What code knows for certain before the model is asked; shown in the prompt and
    kept in the result for the CLI and the UI."""

    uncovered_requirement_ids: list[str] = Field(default_factory=list)
    conflicts: list[list[str]] = Field(
        default_factory=list, description="Each conflicting pair once, IDs sorted"
    )
    absent_documents: list[ReferencedDocument] = Field(default_factory=list)
    flags: list[PageFlag] = Field(default_factory=list)
    budget_requirement_count: int = 0


class RiskResult(StrictModel):
    assessment: RiskAssessment
    findings: Findings


# --------------------------------------------------------------------------------------
# Findings (pure)
# --------------------------------------------------------------------------------------


def detect_findings(
    requirements: RequirementsOutput,
    solution: Solution,
    *,
    referenced_documents: Iterable[ReferencedDocument] = (),
    flags: Iterable[PageFlag] = (),
) -> Findings:
    """Uncovered mandatory IDs from the solution's coverage, conflict pairs once each in
    requirement order, non-hyperlink references not present in the PDF, the flags as
    given, and the count of ``budget_pricing`` requirements."""
    pairs: dict[tuple[str, ...], None] = {}
    for r in requirements.requirements:
        for other in r.conflicts_with:
            pairs.setdefault(tuple(sorted((r.id, other))), None)
    absent = [
        d for d in referenced_documents if not d.present and d.kind is not ReferenceKind.HYPERLINK
    ]
    budget = sum(1 for r in requirements.requirements if r.type is RequirementType.BUDGET_PRICING)
    return Findings(
        uncovered_requirement_ids=list(solution.coverage.uncovered_requirement_ids),
        conflicts=[list(p) for p in pairs],
        absent_documents=absent,
        flags=list(flags),
        budget_requirement_count=budget,
    )


# --------------------------------------------------------------------------------------
# Evidence formatting
# --------------------------------------------------------------------------------------


def _ids(ids: Sequence[str]) -> str:
    return ", ".join(ids)


def format_solution(solution: Solution) -> str:
    cov = solution.coverage
    parts = [f"### Summary\n{solution.summary.strip()}"]
    comps: list[str] = []
    for c in solution.components:
        lines = [f"{c.id} {c.title.strip()} ({_ids(c.requirement_ids) or 'no requirement'})"]
        lines.append(f"  {c.description.strip()}")
        lines += [f"  {claim_line(cl)}" for cl in c.claims]
        comps.append("\n".join(lines))
    parts.append("### Components\n" + ("\n".join(comps) or NONE))
    parts.append(
        "### Assumptions\n" + ("\n".join(claim_line(a) for a in solution.assumptions) or NONE)
    )
    uncovered = _ids(cov.uncovered_requirement_ids) or "none"
    parts.append(
        "### Coverage\n"
        f"Mandatory requirements addressed by at least one component: "
        f"{cov.mandatory_covered} of {cov.mandatory_total}. Not addressed: {uncovered}."
    )
    return "\n\n".join(parts)


def format_findings(findings: Findings, requirements: Iterable[Requirement]) -> str:
    by_id = {r.id: r for r in requirements}

    def text(rid: str) -> str:
        r = by_id.get(rid)
        return f"{rid} {r.text.strip()}" if r else rid

    uncovered = "\n".join(text(i) for i in findings.uncovered_requirement_ids) or NONE
    conflicts = (
        "\n".join(f"{a} <-> {b}: {text(a)} | {text(b)}" for a, b in findings.conflicts) or NONE
    )
    documents = (
        "\n".join(
            f"{d.name} ({d.kind.value}, p. {d.page}" + (f", {d.section}" if d.section else "") + ")"
            for d in findings.absent_documents
        )
        or NONE
    )
    flags = (
        "\n".join(
            f"p. {f.page}: {f.reason.value}" + (f" ({f.detail})" if f.detail else "")
            for f in findings.flags
        )
        or NONE
    )
    n = findings.budget_requirement_count
    budget = (
        f"{n} budget or pricing requirement(s) extracted"
        if n
        else "no budget or pricing requirement was extracted; the RFP may not state a budget"
    )
    return (
        f"### Mandatory requirements the solution does not address\n{uncovered}\n\n"
        f"### Conflicting requirements\n{conflicts}\n\n"
        f"### Referenced documents not in the PDF\n{documents}\n\n"
        f"### Pages whose text could not be parsed\n{flags}\n\n"
        f"### Budget\n{budget}"
    )


def allowed_chunk_ids(
    requirements: RequirementsOutput, problem: ProblemStatement, solution: Solution
) -> list[str]:
    """S7's union plus every chunk ID labelled in the solution's claims and assumptions."""
    seen = dict.fromkeys(_solution_chunk_ids(requirements, problem))
    for c in solution.components:
        for cl in c.claims:
            seen.update(dict.fromkeys(cl.chunk_ids))
    for a in solution.assumptions:
        seen.update(dict.fromkeys(a.chunk_ids))
    return list(seen)


def render_prompt(
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    solution: Solution,
    findings: Findings,
    *,
    title: str,
    prompt: Prompt | None = None,
) -> str:
    prompt = prompt or load_prompt(PROMPT)
    return prompt.render(
        title=title,
        findings=format_findings(findings, requirements.requirements),
        solution=format_solution(solution),
        problem=format_problem(problem),
        requirements=format_requirements(
            requirements.requirements, submission_heading=SUBMISSION_HEADING
        ),
        ambiguities=format_ambiguities(requirements.ambiguities),
        gaps=format_gaps(requirements.gaps),
    )


# --------------------------------------------------------------------------------------
# Per-call schema: citations, count band and must-cite checked inside the retry loop
# --------------------------------------------------------------------------------------


def risk_schema(
    requirement_ids: Iterable[str], chunk_ids: Iterable[str], must_cite: Iterable[str] = ()
) -> type[RiskAssessmentDraft]:
    """A ``RiskAssessmentDraft`` subclass for one call whose validator rejects a count
    outside ``MIN_RISKS..MAX_RISKS``, any requirement or chunk ID outside the inputs,
    and a draft in which an ID from ``must_cite`` is cited by no risk. Named
    ``RiskAssessmentDraft`` so the tool name is unchanged."""
    allowed_reqs = list(requirement_ids)
    allowed_chunks = list(chunk_ids)
    required = list(must_cite)

    def check(self: RiskAssessmentDraft) -> RiskAssessmentDraft:
        problems: list[str] = []
        n = len(self.risks)
        if n < MIN_RISKS:
            problems.append(
                f"risks has {n} entries; return at least {MIN_RISKS} (six to twelve is the target)"
            )
        elif n > MAX_RISKS:
            problems.append(
                f"risks has {n} entries; return at most {MAX_RISKS}: merge risks with the "
                "same cause and drop the least important"
            )
        for i, k in enumerate(self.risks):
            unknown = validate_ids_exist(k.requirement_ids, allowed_reqs)
            if unknown:
                problems.append(
                    f"risks[{i}] ({k.title!r}).requirement_ids cites IDs that are not in "
                    f"the requirement list: {unknown}; copy IDs exactly from the list"
                )
            unknown = validate_ids_exist(k.chunk_ids, allowed_chunks)
            if unknown:
                problems.append(
                    f"risks[{i}] ({k.title!r}).chunk_ids cites chunk IDs that are not shown "
                    f"in the inputs: {unknown}; cite only the bracketed chunk IDs, never "
                    "requirement, ambiguity, gap or component IDs"
                )
        cited = {rid for k in self.risks for rid in k.requirement_ids}
        missing = [rid for rid in required if rid not in cited]
        if missing:
            problems.append(
                "these mandatory requirements are not addressed by the solution and no "
                f"risk cites them: {missing}; add a risk for each or add the ID to the "
                "requirement_ids of an existing risk"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return create_model(
        "RiskAssessmentDraft",
        __base__=RiskAssessmentDraft,
        __module__=__name__,
        __validators__={"check_risks": model_validator(mode="after")(check)},
    )


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------


def _kid(n: int) -> str:
    return f"K{n:02d}"


def _rank(level: Severity | Likelihood) -> int:
    return _LEVEL_RANK[level.value]


def to_assessment(draft: RiskAssessmentDraft) -> RiskAssessment:
    """Stable sort by severity then likelihood (both high to low), number ``K01…``, fold
    duplicate IDs within a risk."""
    ordered = sorted(draft.risks, key=lambda k: (-_rank(k.severity), -_rank(k.likelihood)))
    risks = [
        Risk(
            id=_kid(i),
            title=k.title.strip(),
            description=k.description.strip(),
            severity=k.severity,
            likelihood=k.likelihood,
            justification=k.justification.strip(),
            source=k.source,
            requirement_ids=list(dict.fromkeys(k.requirement_ids)),
            chunk_ids=list(dict.fromkeys(k.chunk_ids)),
            mitigation=k.mitigation.strip() if k.mitigation and k.mitigation.strip() else None,
        )
        for i, k in enumerate(ordered, start=1)
    ]
    return RiskAssessment(risks=risks)


def build_risks(
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    solution: Solution,
    *,
    title: str | None = None,
    referenced_documents: Iterable[ReferencedDocument] = (),
    flags: Iterable[PageFlag] = (),
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> RiskResult:
    """Assess the risks in one validated call.

    ``referenced_documents`` and ``flags`` come from the parsed document (after the S4
    quality pass when the caller ran it). Raises ``StructuredOutputError`` when no draft
    passes validation within the retry budget; nothing is dropped silently.
    """
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    if model is None:
        model = get_chat_model(settings=settings)
    title = title or "untitled RFP"

    findings = detect_findings(
        requirements, solution, referenced_documents=referenced_documents, flags=flags
    )
    known = set(requirements.requirement_ids())
    must_cite = [i for i in findings.uncovered_requirement_ids if i in known]
    if len(must_cite) != len(findings.uncovered_requirement_ids):
        logger.warning(
            "%s: uncovered IDs not in the requirement list are not enforced: %s",
            NODE,
            [i for i in findings.uncovered_requirement_ids if i not in known],
        )
    text = render_prompt(requirements, problem, solution, findings, title=title)
    schema = risk_schema(
        requirements.requirement_ids(),
        allowed_chunk_ids(requirements, problem, solution),
        must_cite,
    )
    result = structured_call(
        model,
        schema,
        [HumanMessage(text)],
        node=NODE,
        settings=settings,
        recorder=recorder,
        config=config,
    )
    # Hand back the plain contract class, not the per-call subclass.
    draft = RiskAssessmentDraft.model_validate(result.value.model_dump())
    return RiskResult(assessment=to_assessment(draft), findings=findings)
