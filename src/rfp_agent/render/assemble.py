"""Assemble the final ``SolutionSummary`` from the pipeline's intermediate outputs.

No LLM. The assembler is the last line of defence for traceability: the agents (S5 to
S8) validate their own citations, and this module checks once more, across the whole
summary, that every cited chunk and requirement ID resolves.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rfp_agent.schemas import (
    ChunkRef,
    Claim,
    ParsedDocument,
    ProblemStatement,
    RequirementsOutput,
    RiskAssessment,
    Solution,
    SolutionSummary,
    SplitDocument,
    validate_ids_exist,
)

# (location, id) pairs, e.g. ("risks.K01.chunk_ids", "S9.9")
Dangling = list[tuple[str, str]]


class CitationError(ValueError):
    """Raised when the assembled summary cites IDs that do not exist."""

    def __init__(self, dangling: Dangling):
        self.dangling = dangling
        lines = "\n".join(f"  {where} -> {id_}" for where, id_ in dangling)
        super().__init__(f"{len(dangling)} dangling citation(s):\n{lines}")


def chunk_refs(split: SplitDocument) -> list[ChunkRef]:
    """One ``ChunkRef`` per chunk, document order, titled by the owning section."""
    return [
        ChunkRef(id=c.id, section_title=s.title, page_start=c.page_start, page_end=c.page_end)
        for s in split.sections
        for c in s.chunks
    ]


def assemble(
    *,
    run_id: str,
    model: str,
    parsed: ParsedDocument,
    split: SplitDocument,
    requirements: RequirementsOutput,
    problem_statement: ProblemStatement,
    solution: Solution,
    risks: RiskAssessment,
    generated_at: datetime | None = None,
    strict: bool = True,
) -> SolutionSummary:
    """Build the JSON source of truth. Raises ``CitationError`` on dangling IDs if strict."""
    summary = SolutionSummary(
        run_id=run_id,
        source_path=parsed.source_path,
        document_title=parsed.title,
        generated_at=generated_at or datetime.now(UTC),
        model=model,
        chunks=chunk_refs(split),
        requirements=requirements,
        problem_statement=problem_statement,
        solution=solution,
        risks=risks,
        referenced_documents=parsed.referenced_documents,
        flags=parsed.flags,
    )
    if strict and (dangling := dangling_citations(summary)):
        raise CitationError(dangling)
    return summary


def dangling_citations(summary: SolutionSummary) -> Dangling:
    """Every cited chunk or requirement ID that does not resolve, with where it was cited.

    ``Requirement.merged_from`` is deliberately not checked: it records pre-dedupe IDs
    that no longer exist after the merge.
    """
    chunk_ids = [c.id for c in summary.chunks]
    req_ids = summary.requirements.requirement_ids()
    out: Dangling = []

    def check(where: str, ids: list[str], known: list[str]) -> None:
        out.extend((where, i) for i in validate_ids_exist(ids, known))

    def check_claims(where: str, claims: list[Claim]) -> None:
        for n, claim in enumerate(claims):
            check(f"{where}[{n}]", claim.chunk_ids, chunk_ids)

    ps = summary.problem_statement
    for field in ("client_situation", "goal", "success_criteria", "constraints"):
        check_claims(f"problem_statement.{field}", getattr(ps, field))

    reqs = summary.requirements
    for r in reqs.requirements:
        check(f"requirements.{r.id}.chunk_ids", r.chunk_ids, chunk_ids)
        check(f"requirements.{r.id}.conflicts_with", r.conflicts_with, req_ids)
    for a in reqs.ambiguities:
        check(f"ambiguities.{a.id}.chunk_ids", a.chunk_ids, chunk_ids)
        check(f"ambiguities.{a.id}.requirement_ids", a.requirement_ids, req_ids)
    for g in reqs.gaps:
        check(f"gaps.{g.id}.chunk_ids", g.chunk_ids, chunk_ids)

    sol = summary.solution
    for comp in sol.components:
        check(f"solution.{comp.id}.requirement_ids", comp.requirement_ids, req_ids)
        check_claims(f"solution.{comp.id}.claims", comp.claims)
    check_claims("solution.assumptions", sol.assumptions)
    check(
        "solution.coverage.uncovered_requirement_ids",
        sol.coverage.uncovered_requirement_ids,
        req_ids,
    )

    for k in summary.risks.risks:
        check(f"risks.{k.id}.requirement_ids", k.requirement_ids, req_ids)
        check(f"risks.{k.id}.chunk_ids", k.chunk_ids, chunk_ids)

    return out
