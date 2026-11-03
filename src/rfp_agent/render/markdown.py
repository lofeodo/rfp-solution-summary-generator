"""Render a ``SolutionSummary`` as markdown, in code, never by an LLM (D8).

Pure and deterministic: the same summary always renders to the same string, which is
what the golden-file test relies on. Citations render as
``(Section title, p. 4 [S3.2])``; chunk IDs that share a section title and page range
are grouped, and an ID with no ``ChunkRef`` renders as the bare ``[S9.9]`` so the
renderer never raises on a dangling citation (the assembler is where those fail).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePath

from rfp_agent.schemas import (
    CheckpointRecord,
    ChunkRef,
    Claim,
    ClaimKind,
    DecisionAction,
    DiffSummary,
    Likelihood,
    Requirement,
    RequirementType,
    RevisionRecord,
    RevisionStatus,
    RiskSource,
    Severity,
    SignOff,
    SolutionSummary,
    Strictness,
)

TYPE_LABELS: dict[RequirementType, str] = {
    RequirementType.FUNCTIONAL: "Functional",
    RequirementType.TECHNICAL: "Technical",
    RequirementType.SECURITY_COMPLIANCE: "Security and compliance",
    RequirementType.LEGAL_CONTRACTUAL: "Legal and contractual",
    RequirementType.TIMELINE: "Timeline",
    RequirementType.BUDGET_PRICING: "Budget and pricing",
    RequirementType.SUBMISSION: "Submission",
    RequirementType.OTHER: "Other",
}

SOURCE_LABELS: dict[RiskSource, str] = {RiskSource.RFP: "RFP", RiskSource.SOLUTION: "Solution"}

_LEVEL_RANK = {"low": 0, "medium": 1, "high": 2}

NONE = "None."


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------


def _inline(text: str) -> str:
    """Collapse all whitespace, so a value never breaks a list item or table row."""
    return " ".join(text.split())


def _cell(text: str) -> str:
    return _inline(text).replace("|", "\\|")


def _ids(ids: Iterable[str]) -> str:
    return ", ".join(ids)


def _pages(ref: ChunkRef) -> str:
    """``p. 4`` or ``pp. 4-6``; empty for a pursuit-brief chunk, which has no pages."""
    if ref.page_start is None or ref.page_end is None:
        return ""
    if ref.page_start == ref.page_end:
        return f"p. {ref.page_start}"
    return f"pp. {ref.page_start}-{ref.page_end}"


def _location(ref: ChunkRef) -> str:
    """``Title, p. 4`` for an RFP chunk; ``Pursuit brief`` for a brief chunk."""
    pages = _pages(ref)
    title = _inline(ref.section_title)
    return f"{title}, {pages}" if pages else title


def cite(chunk_ids: list[str], index: dict[str, ChunkRef]) -> str:
    """``(Title, p. 4 [S3.2]; Other, pp. 13-18 [S7.1, S7.3])``, or ``""`` if no IDs.

    IDs sharing a section title and page range are grouped in first-seen order; an ID
    missing from ``index`` renders as a bare ``[S9.9]``.
    """
    groups: dict[tuple[str, int | None, int | None] | None, list[str]] = {}
    for cid in chunk_ids:
        ref = index.get(cid)
        key = (ref.section_title, ref.page_start, ref.page_end) if ref else None
        ids = groups.setdefault(key, [])
        if cid not in ids:
            ids.append(cid)
    parts = []
    for key, ids in groups.items():
        bracket = f"[{_ids(ids)}]"
        if key is None:
            parts.append(bracket)
        else:
            parts.append(f"{_location(index[ids[0]])} {bracket}")
    return f"({'; '.join(parts)})" if parts else ""


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def _claims(claims: list[Claim], index: dict[str, ChunkRef]) -> str:
    if not claims:
        return NONE
    lines = []
    for c in claims:
        marker = "*(inference)*" if c.kind is ClaimKind.INFERENCE else ""
        lines.append("- " + _join(_inline(c.text), marker, cite(c.chunk_ids, index)))
    return "\n".join(lines)


def _rank(level: Severity | Likelihood) -> int:
    return _LEVEL_RANK[level.value]


# --------------------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------------------


def _header(s: SolutionSummary) -> list[str]:
    title = s.document_title or PurePath(s.source_path).name
    lines = [
        f"- **Source:** {s.source_path}",
        f"- **Run:** {s.run_id}",
        f"- **Generated:** {s.generated_at.isoformat()}",
        f"- **Model:** {s.model}",
    ]
    if s.review is not None and s.review.checkpoint is not None:
        cp = s.review.checkpoint
        when = cp.confirmed_at.isoformat()
        lines.append(f"- **Checkpoint:** confirmed by {_inline(cp.reviewer)} on {when}")
    if s.review is not None and s.review.sign_off is not None:
        lines.append(f"- **Signed off:** {_sign_off_text(s.review.sign_off)}")
    return [f"# Solution summary: {_inline(title)}", "\n".join(lines)]


def _sign_off_text(so: SignOff) -> str:
    """``by Dana on <time> (requirements v2, problem v1, solution v3, risks v2)``."""
    versions = ", ".join(f"{a.value} v{v}" for a, v in so.versions.items())
    text = f"by {_inline(so.reviewer)} on {so.signed_at.isoformat()}"
    return text + (f" ({versions})" if versions else "")


def _problem(s: SolutionSummary, index: dict[str, ChunkRef]) -> list[str]:
    ps = s.problem_statement
    out = ["## Problem statement"]
    for heading, claims in (
        ("Client situation", ps.client_situation),
        ("Goal", ps.goal),
        ("Success criteria", ps.success_criteria),
        ("Constraints", ps.constraints),
    ):
        out += [f"### {heading}", _claims(claims, index)]
    return out


def _requirement(r: Requirement, index: dict[str, ChunkRef]) -> str:
    notes = []
    if r.merged_from:
        notes.append(f"merged from {_ids(r.merged_from)}")
    if r.conflicts_with:
        notes.append(f"conflicts with {_ids(r.conflicts_with)}")
    note = f"_({'; '.join(notes)})_" if notes else ""
    head = "- " + _join(f"**{r.id}**", f"({r.strictness.value})", _inline(r.text), note)
    unverified = "" if r.quote_verified else "*(quote not verified)*"
    quote = "  > " + _join(f'"{_inline(r.quote)}"', cite(r.chunk_ids, index), unverified)
    return f"{head}\n{quote}"


def _id_list(items: list[str]) -> str:
    return "\n".join(items) if items else NONE


def _requirements(s: SolutionSummary, index: dict[str, ChunkRef]) -> list[str]:
    reqs = s.requirements
    counts = {k: sum(r.strictness is k for r in reqs.requirements) for k in Strictness}
    out = [
        "## Requirements",
        f"{len(reqs.requirements)} requirements: "
        + ", ".join(f"{counts[k]} {k.value}" for k in Strictness)
        + ".",
    ]
    for rtype in RequirementType:
        group = [r for r in reqs.requirements if r.type is rtype]
        if group:
            out += [
                f"### {TYPE_LABELS[rtype]} ({len(group)})",
                "\n".join(_requirement(r, index) for r in group),
            ]

    ambiguities = []
    for a in reqs.ambiguities:
        affects = f"_(affects {_ids(a.requirement_ids)})_" if a.requirement_ids else ""
        ambiguities.append(
            "- " + _join(f"**{a.id}**", _inline(a.description), affects, cite(a.chunk_ids, index))
        )

    gaps = []
    for g in reqs.gaps:
        doc = (
            f"_(referenced document: {_inline(g.referenced_document)})_"
            if g.referenced_document
            else ""
        )
        gaps.append(
            "- " + _join(f"**{g.id}**", _inline(g.description), doc, cite(g.chunk_ids, index))
        )

    return out + ["### Ambiguities", _id_list(ambiguities), "### Gaps", _id_list(gaps)]


def _solution(s: SolutionSummary, index: dict[str, ChunkRef]) -> list[str]:
    sol = s.solution
    cov = sol.coverage
    if cov.mandatory_total == 0:
        coverage = "No mandatory requirements to cover."
    else:
        coverage = (
            f"Covers {cov.mandatory_covered} of {cov.mandatory_total} mandatory requirements."
        )
    if cov.uncovered_requirement_ids:
        coverage += f" Uncovered: {_ids(cov.uncovered_requirement_ids)}."
    out = ["## Proposed solution", sol.summary.strip() or NONE, "### Coverage", coverage]

    out.append("### Components")
    if not sol.components:
        out.append(NONE)
    for comp in sol.components:
        out += [f"#### {comp.id}. {_inline(comp.title)}", comp.description.strip()]
        if comp.requirement_ids:
            out.append(f"Addresses: {_ids(comp.requirement_ids)}.")
        if comp.claims:
            out.append(_claims(comp.claims, index))

    return out + ["### Assumptions", _claims(sol.assumptions, index)]


def sorted_risks(s: SolutionSummary):
    """Severity high to low, then likelihood high to low, then ID."""
    return sorted(s.risks.risks, key=lambda k: (-_rank(k.severity), -_rank(k.likelihood), k.id))


def _risks(s: SolutionSummary, index: dict[str, ChunkRef]) -> list[str]:
    out = ["## Risks"]
    risks = sorted_risks(s)
    if not risks:
        return out + [NONE]
    rows = ["| ID | Risk | Severity | Likelihood | Source |", "|---|---|---|---|---|"]
    rows += [
        f"| {k.id} | {_cell(k.title)} | {k.severity.value} | {k.likelihood.value} "
        f"| {SOURCE_LABELS[k.source]} |"
        for k in risks
    ]
    out.append("\n".join(rows))
    for k in risks:
        out += [
            f"### {k.id}. {_inline(k.title)}",
            k.description.strip(),
            _join(f"**Why:** {_inline(k.justification)}", cite(k.chunk_ids, index)),
        ]
        if k.mitigation:
            out.append(f"**Mitigation:** {_inline(k.mitigation)}")
        if k.requirement_ids:
            out.append(f"**Related requirements:** {_ids(k.requirement_ids)}.")
    return out


def _referenced(s: SolutionSummary) -> list[str]:
    out = ["## Referenced documents"]
    if not s.referenced_documents:
        return out + [NONE]
    rows = ["| Name | Kind | Page | Section | In PDF | URL |", "|---|---|---|---|---|---|"]
    rows += [
        f"| {_cell(d.name)} | {d.kind.value} | {d.page} | {_cell(d.section or '')} "
        f"| {'yes' if d.present else 'no'} | {_cell(d.url or '')} |"
        for d in s.referenced_documents
    ]
    return out + ["\n".join(rows)]


def _flags(s: SolutionSummary) -> list[str]:
    lines = []
    for f in s.flags:
        detail = f" ({_inline(f.detail)})" if f.detail else ""
        lines.append(f"- Page {f.page}: {f.reason.value.replace('_', ' ')}{detail}")
    return ["## Parse flags", _id_list(lines)]


def _checkpoint_lines(cp: CheckpointRecord) -> list[str]:
    lines = [
        "- **Checkpoint:** confirmed by "
        + _join(
            _inline(cp.reviewer),
            f"on {cp.confirmed_at.isoformat()}",
            f"after {cp.waited_s:.0f} s" if cp.waited_s else "",
        )
    ]
    if cp.note:
        lines.append(f"- **Note:** {_inline(cp.note)}")
    rejected = cp.rejected_ids()
    lines.append(f"- **Rejected requirements:** {_ids(rejected) if rejected else NONE}")
    edits = []
    for d in cp.decisions:
        if d.action is DecisionAction.REJECT:
            continue
        changes = []
        if d.strictness is not None:
            changes.append(f"strictness set to {d.strictness.value}")
        if d.type is not None:
            changes.append(f"type set to {d.type.value}")
        if not changes:
            continue
        note = f" ({_inline(d.note)})" if d.note else ""
        edits.append(f"  - **{d.requirement_id}:** {'; '.join(changes)}{note}")
    lines.append("- **Edited requirements:**" + ("\n" + "\n".join(edits) if edits else f" {NONE}"))
    return lines


def _diff_counts(diff: DiffSummary | None) -> str:
    if diff is None:
        return ""
    if diff.empty:
        return "no change"
    parts = [
        f"{len(diff.added)} added" if diff.added else "",
        f"{len(diff.removed)} removed" if diff.removed else "",
        f"{len(diff.changed)} changed" if diff.changed else "",
    ]
    return ", ".join(p for p in parts if p)


def _revision_line(r: RevisionRecord) -> str:
    what = r.kind.value.replace("_", " ") + (f" {r.artefact.value}" if r.artefact else "")
    head = f"- **{r.id}** {what} by {_inline(r.reviewer)} on {r.created_at.isoformat()}"
    if r.status is RevisionStatus.FAILED:
        return f"{head}: failed ({_inline(r.error or 'no error text')})"
    details = []
    if r.instruction:
        details.append(f'"{_inline(r.instruction)}"')
    if r.from_version is not None and r.to_version is not None:
        details.append(f"v{r.from_version} to v{r.to_version}")
    if counts := _diff_counts(r.diff):
        details.append(counts)
    if r.made_stale:
        details.append("made stale: " + ", ".join(a.value for a in r.made_stale))
    if r.calls:
        details.append(f"{r.calls} call{'s' if r.calls != 1 else ''}, ${r.cost_usd:.4f}")
    if r.note:
        details.append(_inline(r.note))
    return head + (": " + "; ".join(details) if details else "")


def _review(s: SolutionSummary) -> list[str]:
    """The human touchpoints of the run (ST12): who confirmed the checkpoint, when, what
    they changed, the pursuit brief the draft was built on, every revision since, and the
    sign-off. Omitted for an unattended run."""
    review = s.review
    if review is None or (
        review.checkpoint is None and not review.revisions and review.sign_off is None
    ):
        return []
    cp = review.checkpoint
    blocks = ["## Review history"]
    if cp is not None:
        blocks.append("\n".join(_checkpoint_lines(cp)))
        if cp.brief is not None:
            brief_lines = [f"- **{c.id}** {_inline(c.text)}" for c in cp.brief.chunks]
            blocks += ["### Pursuit brief", "\n".join(brief_lines)]
    if review.revisions:
        blocks += ["### Revisions", "\n".join(_revision_line(r) for r in review.revisions)]
    if review.sign_off is not None:
        so = review.sign_off
        line = f"Signed off {_sign_off_text(so)}."
        if so.note:
            line += f" {_inline(so.note)}"
        blocks += ["### Sign-off", line]
    return blocks


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def render_markdown(summary: SolutionSummary) -> str:
    """Render the whole summary. Blocks are separated by one blank line."""
    index = {c.id: c for c in summary.chunks}
    blocks = [
        *_header(summary),
        *_problem(summary, index),
        *_requirements(summary, index),
        *_solution(summary, index),
        *_risks(summary, index),
        *_referenced(summary),
        *_flags(summary),
        *_review(summary),
    ]
    return "\n\n".join(b for b in blocks if b) + "\n"
