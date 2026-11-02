"""Revision of an artefact by instruction (ST12b): the model applies what a reviewer
asked, code re-validates it with the producing stage's own checks.

Two contracts, chosen by the size of the artefact and by what code can check:

- **Requirements: a patch.** The confirmed list can hold well over a hundred
  requirements, too long to return whole within the output cap (F16), and a whole
  rewrite could drift silently. The model returns ``RequirementsPatch`` (edits by ID,
  additions, removals); the per-call validator refuses unknown or duplicate IDs, empty
  edits, a quote without its chunk (or the reverse) and any quote not found verbatim in
  the chunk it names (the extractor's rule), so ``structured_call`` feeds the exact
  problem back and retries. ``apply_patch`` assigns new IDs (never reused), marks every
  touched requirement ``origin = reviewed`` and strips removed IDs from conflicts and
  ambiguities.
- **Problem, solution, risks: the whole artefact.** They are small and their stages
  already have per-call validators (``problem_schema``, ``solution_schema``,
  ``risk_schema``), which a revision reuses unchanged. A component or risk carries its
  current ``id`` when it is kept, so IDs stay stable across versions; code refuses an ID
  the artefact does not have, and refuses a solution revision that uncovers a mandatory
  requirement covered today. Coverage and the risk findings are recomputed by code.

One structured call per revision, node ``revise_<artefact>``, prompt ``revise_<artefact>``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from pydantic import create_model, model_validator

from rfp_agent.agents.problem import (
    FULL_TEXT_EVIDENCE,
    HIERARCHICAL_EVIDENCE,
    ProblemResult,
    evidence_ids,
    format_evidence,
    format_full_text,
    problem_schema,
)
from rfp_agent.agents.requirements import format_for_dedupe
from rfp_agent.agents.risk import (
    SUBMISSION_HEADING,
    RiskResult,
    detect_findings,
    format_findings,
    format_solution,
    risk_schema,
)
from rfp_agent.agents.risk import allowed_chunk_ids as risk_chunk_ids
from rfp_agent.agents.solution import (
    NONE,
    SolutionResult,
    compute_coverage,
    format_ambiguities,
    format_gaps,
    format_problem,
    format_requirements,
    in_scope,
    solution_schema,
)
from rfp_agent.agents.solution import allowed_chunk_ids as solution_chunk_ids
from rfp_agent.brief import brief_chunk_ids, format_brief
from rfp_agent.checkpoint import strip_references
from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import get_chat_model, load_prompt, structured_call
from rfp_agent.observability import current_recorder
from rfp_agent.schemas import (
    Artefact,
    Brief,
    Chunk,
    PageFlag,
    ProblemStatement,
    ReferencedDocument,
    Requirement,
    RequirementOrigin,
    RequirementsOutput,
    RequirementsPatch,
    Risk,
    RiskAssessment,
    RiskAssessmentRevision,
    Solution,
    SolutionComponent,
    SolutionRevision,
    SplitDocument,
)
from rfp_agent.textmatch import find_quote

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

NODES: dict[Artefact, str] = {a: f"revise_{a.value}" for a in Artefact}
PROMPTS: dict[Artefact, str] = {
    Artefact.REQUIREMENTS: "revise_requirements",
    Artefact.PROBLEM: "revise_problem",
    Artefact.SOLUTION: "revise_solution",
    Artefact.RISKS: "revise_risk",
}

_LEVEL_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


def _next_id(prefix: str, ids: Iterable[str], width: int) -> Callable[[], str]:
    """A generator of fresh IDs after the highest number in ``ids``: removed IDs are
    never reused, so a diff across versions stays unambiguous."""
    numbers = [int(m.group(1)) for i in ids if (m := re.fullmatch(rf"{prefix}(\d+)", i))]
    counter = [max(numbers, default=0)]

    def next_id() -> str:
        counter[0] += 1
        return f"{prefix}{counter[0]:0{width}d}"

    return next_id


def _resolve(settings: Settings | None, recorder: RunRecorder | None, model):
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    if model is None:
        model = get_chat_model(settings=settings)
    return settings, recorder, model


# --------------------------------------------------------------------------------------
# Requirements: a patch
# --------------------------------------------------------------------------------------


def format_chunks(split: SplitDocument) -> str:
    """Every chunk's own text, labelled with its ID, section and pages (the problem
    statement's full-text evidence, which the extractor's quotes come from)."""
    text, _ = format_full_text(split)
    return text


def requirements_patch_schema(
    known_ids: Iterable[str], chunks: dict[str, Chunk]
) -> type[RequirementsPatch]:
    """A ``RequirementsPatch`` subclass for one call that refuses unknown or duplicate
    IDs, an edit that changes nothing, a quote without its chunk ID (or the reverse), an
    unknown chunk, and a quote not found verbatim in its chunk."""
    known = set(known_ids)

    def quote_problem(where: str, quote: str | None, chunk_id: str | None) -> str | None:
        if quote is None and chunk_id is None:
            return None
        if quote is None or not quote.strip():
            return f"{where}: chunk_id {chunk_id} is given without a quote; give both or neither"
        if chunk_id is None:
            return f"{where}: a quote is given without its chunk_id; name the chunk it is from"
        chunk = chunks.get(chunk_id)
        if chunk is None:
            return f"{where}: chunk ID {chunk_id} does not exist; use a chunk ID shown"
        if not find_quote(chunk.text, quote):
            return (
                f'{where}: the quote "{quote}" was not found verbatim in chunk {chunk_id}. '
                "Copy the exact span, character for character."
            )
        return None

    def check(self: RequirementsPatch) -> RequirementsPatch:
        problems: list[str] = []
        seen: set[str] = set()
        for i, e in enumerate(self.edits):
            where = f"edits[{i}] ({e.id})"
            if e.id not in known:
                problems.append(f"{where}: no such requirement; copy IDs from the list")
            if e.id in seen:
                problems.append(f"{where}: {e.id} appears in more than one operation")
            seen.add(e.id)
            if all(v is None for v in (e.text, e.type, e.strictness, e.quote, e.chunk_id)):
                problems.append(f"{where}: changes nothing; leave it out")
            if (p := quote_problem(where, e.quote, e.chunk_id)) is not None:
                problems.append(p)
        for i, a in enumerate(self.additions):
            where = f"additions[{i}]"
            if not a.text.strip():
                problems.append(f"{where}: text is empty")
            if (p := quote_problem(where, a.quote, a.chunk_id)) is not None:
                problems.append(p)
        for i, rid in enumerate(self.removals):
            where = f"removals[{i}] ({rid})"
            if rid not in known:
                problems.append(f"{where}: no such requirement; copy IDs from the list")
            if rid in seen:
                problems.append(f"{where}: {rid} appears in more than one operation")
            seen.add(rid)
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return create_model(
        "RequirementsPatch",
        __base__=RequirementsPatch,
        __module__=__name__,
        __validators__={"check_patch": model_validator(mode="after")(check)},
    )


def apply_patch(
    current: RequirementsOutput, patch: RequirementsPatch
) -> tuple[RequirementsOutput, list[str]]:
    """The patched list and the removed IDs. Edits keep the requirement's ID and place;
    additions are appended with fresh IDs; every changed or added requirement gets
    ``origin = reviewed``; removed IDs are stripped from conflicts and ambiguities. The
    patch is assumed valid (``requirements_patch_schema``)."""
    edits = {e.id: e for e in patch.edits}
    requirements: list[Requirement] = []
    for r in current.requirements:
        e = edits.get(r.id)
        if e is None:
            requirements.append(r)
            continue
        updates: dict[str, Any] = {}
        if e.text is not None and e.text.strip() != r.text:
            updates["text"] = e.text.strip()
        if e.type is not None and e.type is not r.type:
            updates["type"] = e.type
        if e.strictness is not None and e.strictness is not r.strictness:
            updates["strictness"] = e.strictness
        if (
            e.quote is not None
            and e.chunk_id is not None
            and (e.quote != r.quote or [e.chunk_id] != r.chunk_ids)
        ):
            updates.update(quote=e.quote, chunk_ids=[e.chunk_id], quote_verified=True)
        if updates:
            updates["origin"] = RequirementOrigin.REVIEWED
        requirements.append(r.model_copy(update=updates) if updates else r)
    next_rid = _next_id("R", current.requirement_ids(), 3)
    for a in patch.additions:
        requirements.append(
            Requirement(
                id=next_rid(),
                text=a.text.strip(),
                type=a.type,
                strictness=a.strictness,
                quote=a.quote,
                chunk_ids=[a.chunk_id],
                quote_verified=True,
                origin=RequirementOrigin.REVIEWED,
            )
        )
    removed = list(dict.fromkeys(patch.removals))
    patched = current.model_copy(update={"requirements": requirements})
    return strip_references(patched, set(removed)), removed


def revise_requirements(
    current: RequirementsOutput,
    split: SplitDocument,
    *,
    instruction: str,
    title: str,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> tuple[RequirementsOutput, list[str]]:
    """Apply ``instruction`` to the requirement list; return the new list and the IDs it
    removed. Raises ``StructuredOutputError`` when no valid patch arrives."""
    settings, recorder, model = _resolve(settings, recorder, model)
    text = load_prompt(PROMPTS[Artefact.REQUIREMENTS]).render(
        title=title,
        instruction=instruction.strip(),
        requirements=format_for_dedupe(current.requirements) or NONE,
        chunks=format_chunks(split),
    )
    schema = requirements_patch_schema(current.requirement_ids(), {c.id: c for c in split.chunks()})
    result = structured_call(
        model,
        schema,
        [HumanMessage(text)],
        node=NODES[Artefact.REQUIREMENTS],
        settings=settings,
        recorder=recorder,
        config=config,
    )
    patch = RequirementsPatch.model_validate(result.value.model_dump())
    return apply_patch(current, patch)


# --------------------------------------------------------------------------------------
# Problem statement: the whole statement through problem_schema
# --------------------------------------------------------------------------------------


def problem_evidence(current: ProblemResult, split: SplitDocument) -> tuple[str, list[str], str]:
    """``(evidence, citable IDs, evidence kind)`` as the statement was synthesised from:
    the chunk summaries in hierarchical mode, the full text otherwise."""
    if current.mode == "hierarchical" and current.chunk_summaries:
        summaries = current.chunk_summaries
        return format_evidence(summaries, split), evidence_ids(summaries), HIERARCHICAL_EVIDENCE
    text, ids = format_full_text(split)
    return text, ids, FULL_TEXT_EVIDENCE


def revise_problem(
    current: ProblemResult,
    split: SplitDocument,
    *,
    instruction: str,
    title: str,
    brief: Brief | None = None,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> ProblemResult:
    """Apply ``instruction`` to the problem statement; keeps the mode and the summaries."""
    settings, recorder, model = _resolve(settings, recorder, model)
    evidence, ids, kind = problem_evidence(current, split)
    text = load_prompt(PROMPTS[Artefact.PROBLEM]).render(
        title=title,
        instruction=instruction.strip(),
        problem=format_problem(current.statement),
        evidence_kind=kind,
        evidence=evidence,
        brief=format_brief(brief),
    )
    result = structured_call(
        model,
        problem_schema([*ids, *brief_chunk_ids(brief)]),
        [HumanMessage(text)],
        node=NODES[Artefact.PROBLEM],
        settings=settings,
        recorder=recorder,
        config=config,
    )
    statement = ProblemStatement.model_validate(result.value.model_dump())
    return current.model_copy(update={"statement": statement})


# --------------------------------------------------------------------------------------
# Solution: the whole solution, stable component IDs, no coverage regression
# --------------------------------------------------------------------------------------


def _id_problems(kind: str, given: Sequence[str | None], known: set[str]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for i, item_id in enumerate(given):
        if item_id is None:
            continue
        if item_id not in known:
            problems.append(
                f"{kind}[{i}].id {item_id!r} is not in the current {kind}; keep the IDs "
                "shown, or omit id for a new one"
            )
        if item_id in seen:
            problems.append(f"{kind}[{i}].id {item_id!r} is used twice; each ID once")
        seen.add(item_id)
    return problems


def solution_revision_checks(
    current: Solution, requirements: Sequence[Requirement]
) -> Callable[[Any], list[str]]:
    """Extra checks for a revised solution: component IDs must exist and be unique, and
    no mandatory requirement covered by the current solution may become uncovered."""
    known = {c.id for c in current.components}
    covered = {r.id for r in in_scope(requirements)} - set(
        compute_coverage(current.components, requirements).uncovered_requirement_ids
    )
    by_id = {r.id: r for r in requirements}

    def check(draft: Any) -> list[str]:
        problems = _id_problems("components", [c.id for c in draft.components], known)
        uncovered = compute_coverage(draft.components, requirements).uncovered_requirement_ids
        lost = [rid for rid in uncovered if rid in covered]
        if lost:
            lines = "; ".join(f"{rid}: {by_id[rid].text.strip()}" for rid in lost)
            problems.append(
                f"these mandatory requirements are covered by the current solution and by "
                f"no component of the revision: {lines}. Keep them in the requirement_ids "
                "of a component, and say in its description how each is met"
            )
        return problems

    return check


def rekey_components(draft: SolutionRevision, current: Solution) -> list[SolutionComponent]:
    """Components in reply order; kept ones keep their ID, new ones get the next free."""
    next_cid = _next_id("C", [c.id for c in current.components], 2)
    return [
        SolutionComponent(
            id=c.id or next_cid(),
            title=c.title.strip(),
            description=c.description.strip(),
            requirement_ids=list(dict.fromkeys(c.requirement_ids)),
            claims=c.claims,
        )
        for c in draft.components
    ]


def revise_solution(
    current: SolutionResult,
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    *,
    instruction: str,
    title: str,
    brief: Brief | None = None,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> SolutionResult:
    """Apply ``instruction`` to the solution; coverage is recomputed by code."""
    settings, recorder, model = _resolve(settings, recorder, model)
    solution = current.solution
    text = load_prompt(PROMPTS[Artefact.SOLUTION]).render(
        title=title,
        instruction=instruction.strip(),
        solution=format_solution(solution),
        problem=format_problem(problem),
        requirements=format_requirements(requirements.requirements),
        ambiguities=format_ambiguities(requirements.ambiguities),
        gaps=format_gaps(requirements.gaps),
        brief=format_brief(brief),
    )
    chunk_ids = list(
        dict.fromkeys(
            [
                *solution_chunk_ids(requirements, problem, brief),
                *(k for c in solution.components for cl in c.claims for k in cl.chunk_ids),
                *(k for a in solution.assumptions for k in a.chunk_ids),
            ]
        )
    )
    schema = solution_schema(
        requirements.requirement_ids(),
        chunk_ids,
        base=SolutionRevision,
        extra=solution_revision_checks(solution, requirements.requirements),
    )
    result = structured_call(
        model,
        schema,
        [HumanMessage(text)],
        node=NODES[Artefact.SOLUTION],
        settings=settings,
        recorder=recorder,
        config=config,
    )
    draft = SolutionRevision.model_validate(result.value.model_dump())
    components = rekey_components(draft, solution)
    revised = Solution(
        summary=draft.summary.strip(),
        components=components,
        assumptions=draft.assumptions,
        coverage=compute_coverage(components, requirements.requirements),
    )
    return current.model_copy(update={"solution": revised})


# --------------------------------------------------------------------------------------
# Risks: the whole assessment, stable risk IDs
# --------------------------------------------------------------------------------------


def format_risks(assessment: RiskAssessment) -> str:
    lines: list[str] = []
    for k in assessment.risks:
        refs = "; ".join(x for x in (", ".join(k.requirement_ids), ", ".join(k.chunk_ids)) if x)
        lines.append(
            f"{k.id} [{k.severity.value}/{k.likelihood.value}, {k.source.value}] "
            f"{k.title.strip()} ({refs or 'no citation'})"
        )
        lines.append(f"  description: {k.description.strip()}")
        lines.append(f"  justification: {k.justification.strip()}")
        lines.append(f"  mitigation: {(k.mitigation or '-').strip()}")
    return "\n".join(lines) or NONE


def risk_revision_checks(current: RiskAssessment) -> Callable[[Any], list[str]]:
    known = {k.id for k in current.risks}

    def check(draft: Any) -> list[str]:
        return _id_problems("risks", [k.id for k in draft.risks], known)

    return check


def rekey_risks(draft: RiskAssessmentRevision, current: RiskAssessment) -> RiskAssessment:
    """Kept risks keep their ID, new ones get the next free; stable sort by severity then
    likelihood (as ``to_assessment``) without renumbering."""
    next_kid = _next_id("K", [k.id for k in current.risks], 2)
    risks = [
        Risk(
            id=k.id or next_kid(),
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
        for k in draft.risks
    ]
    risks.sort(key=lambda k: (-_LEVEL_RANK[k.severity.value], -_LEVEL_RANK[k.likelihood.value]))
    return RiskAssessment(risks=risks)


def revise_risks(
    current: RiskResult,
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    solution: Solution,
    *,
    instruction: str,
    title: str,
    brief: Brief | None = None,
    referenced_documents: Iterable[ReferencedDocument] = (),
    flags: Iterable[PageFlag] = (),
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
) -> RiskResult:
    """Apply ``instruction`` to the risks; the findings are recomputed from the current
    solution, and every uncovered mandatory requirement must still be cited."""
    settings, recorder, model = _resolve(settings, recorder, model)
    findings = detect_findings(
        requirements, solution, referenced_documents=referenced_documents, flags=flags
    )
    known = set(requirements.requirement_ids())
    must_cite = [i for i in findings.uncovered_requirement_ids if i in known]
    text = load_prompt(PROMPTS[Artefact.RISKS]).render(
        title=title,
        instruction=instruction.strip(),
        risks=format_risks(current.assessment),
        findings=format_findings(findings, requirements.requirements),
        solution=format_solution(solution),
        problem=format_problem(problem),
        requirements=format_requirements(
            requirements.requirements, submission_heading=SUBMISSION_HEADING
        ),
        ambiguities=format_ambiguities(requirements.ambiguities),
        gaps=format_gaps(requirements.gaps),
        brief=format_brief(brief),
    )
    chunk_ids = list(
        dict.fromkeys(
            [
                *risk_chunk_ids(requirements, problem, solution, brief),
                *(c for k in current.assessment.risks for c in k.chunk_ids),
            ]
        )
    )
    schema = risk_schema(
        requirements.requirement_ids(),
        chunk_ids,
        must_cite,
        base=RiskAssessmentRevision,
        extra=risk_revision_checks(current.assessment),
    )
    result = structured_call(
        model,
        schema,
        [HumanMessage(text)],
        node=NODES[Artefact.RISKS],
        settings=settings,
        recorder=recorder,
        config=config,
    )
    draft = RiskAssessmentRevision.model_validate(result.value.model_dump())
    return RiskResult(assessment=rekey_risks(draft, current.assessment), findings=findings)


__all__ = [
    "NODES",
    "PROMPTS",
    "apply_patch",
    "format_chunks",
    "format_risks",
    "problem_evidence",
    "rekey_components",
    "rekey_risks",
    "requirements_patch_schema",
    "revise_problem",
    "revise_requirements",
    "revise_risks",
    "revise_solution",
    "risk_revision_checks",
    "solution_revision_checks",
]
