"""Per-output scores: problem statement, solution, risks, cost.

Each judge here is one call per run. Code-side counts are always computed; the judge
fields stay ``None`` when no judge is given or its call fails.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field, create_model, model_validator

from evals.gold.schema import GoldSet
from evals.harness.judge import Judge
from evals.harness.load import EvalRun
from evals.harness.schemas import (
    ChecklistVerdict,
    ComponentRecord,
    CostScores,
    FindingVerdict,
    PairVerdict,
    ProblemScores,
    RetryRecord,
    RiskScores,
    RiskVerdict,
    RubricScore,
    SolutionScores,
    StageCost,
)
from rfp_agent.agents.problem import CLAIM_LISTS
from rfp_agent.agents.solution import compute_coverage, in_scope
from rfp_agent.llm import StructuredOutputError
from rfp_agent.schemas import Requirement
from rfp_agent.textmatch import normalise

LEVELS = ("low", "medium", "high")
RUBRIC = ("specificity", "feasibility", "consistency")


def _checked[T: BaseModel](base: type[T], check) -> type[T]:
    return create_model(
        base.__name__,
        __base__=base,
        __module__=base.__module__,
        __validators__={"check": model_validator(mode="after")(check)},
    )


def _once[T](judge: Judge, fn) -> T | None:
    try:
        return fn()
    except StructuredOutputError:
        judge.failures += 1
        return None


def _req_line(r: Requirement) -> str:
    return f"{r.id} [{r.strictness.value}, {r.type.value}] {r.text}"


# --------------------------------------------------------------------------------------
# Problem statement: checklist coverage
# --------------------------------------------------------------------------------------


class FactVerdict(BaseModel):
    gold_id: str
    status: Literal["covered", "partial", "missing"]
    claim: str | None = Field(
        default=None, description="Label of the claim that covers it, e.g. goal[2]"
    )
    reason: str = Field(description="At most 15 words")


class ChecklistVerdicts(BaseModel):
    facts: list[FactVerdict]


def _checklist_schema(gold_ids: list[str], labels: list[str]) -> type[ChecklistVerdicts]:
    def check(self: ChecklistVerdicts) -> ChecklistVerdicts:
        got = [f.gold_id for f in self.facts]
        problems = []
        if sorted(got) != sorted(gold_ids):
            problems.append(f"return exactly one entry per fact ID {gold_ids}; got {got}")
        for f in self.facts:
            if f.status != "missing" and f.claim not in labels:
                problems.append(
                    f"{f.gold_id}: claim must be one of the labels shown, got {f.claim!r}"
                )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return _checked(ChecklistVerdicts, check)


def score_problem(run: EvalRun, gold: GoldSet, judge: Judge | None) -> ProblemScores:
    ps = run.summary.problem_statement
    labelled = [
        (f"{name}[{n}]", c) for name in CLAIM_LISTS for n, c in enumerate(getattr(ps, name))
    ]
    checklist = [
        ChecklistVerdict(gold_id=g.id, fact=g.fact, quote_verifiable=g.quote_verifiable)
        for g in gold.checklist
    ]
    scores = ProblemScores(
        mode=run.problem.mode if run.problem else "unknown",
        claims={name: len(getattr(ps, name)) for name in CLAIM_LISTS},
        facts=sum(c.kind.value == "fact" for _, c in labelled),
        inferences=sum(c.kind.value == "inference" for _, c in labelled),
        checklist_total=len(gold.checklist),
        checklist=checklist,
    )
    if judge is None or not gold.checklist:
        return scores

    labels = [lab for lab, _ in labelled]
    statement = "\n".join(
        f"{lab} {c.text}{' (inference)' if c.kind.value == 'inference' else ''}"
        for lab, c in labelled
    )
    facts = "\n".join(f"{g.id} {g.fact}" for g in gold.checklist)
    schema = _checklist_schema([g.id for g in gold.checklist], labels)
    out = _once(
        judge,
        lambda: judge.call(
            schema, "judge_checklist", "judge_checklist", statement=statement, facts=facts
        ),
    )
    if out is None:
        return scores
    by_id = {f.gold_id: f for f in out.facts}
    for item in checklist:
        f = by_id[item.gold_id]
        item.status, item.claim, item.reason = f.status, f.claim, f.reason
    scores.checklist_covered = sum(i.status == "covered" for i in checklist)
    scores.checklist_partial = sum(i.status == "partial" for i in checklist)
    scores.checklist_coverage = scores.checklist_covered / len(checklist)
    return scores


# --------------------------------------------------------------------------------------
# Solution: cited coverage, judged coverage, rubric
# --------------------------------------------------------------------------------------


class ComponentVerdict(BaseModel):
    id: str
    not_addressed: list[str] = Field(
        default_factory=list,
        description="Cited requirement IDs the description does not actually meet",
    )
    calendar: bool = Field(
        description="True when the component exists only to meet proposal-process dates"
    )
    reason: str = Field(description="At most 25 words")


class SolutionVerdict(BaseModel):
    specificity: RubricScore
    feasibility: RubricScore
    consistency: RubricScore
    components: list[ComponentVerdict]


def _solution_schema(cited: dict[str, list[str]]) -> type[SolutionVerdict]:
    def check(self: SolutionVerdict) -> SolutionVerdict:
        got = [c.id for c in self.components]
        problems = []
        if sorted(got) != sorted(cited):
            problems.append(f"return exactly one entry per component {sorted(cited)}; got {got}")
        for c in self.components:
            extra = [i for i in c.not_addressed if i not in cited.get(c.id, [])]
            if extra:
                problems.append(
                    f"{c.id}: not_addressed may only list IDs it cites; {extra} are not"
                )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return _checked(SolutionVerdict, check)


def score_solution(run: EvalRun, judge: Judge | None) -> SolutionScores:
    sol = run.summary.solution
    reqs = run.summary.requirements.requirements
    by_id = {r.id: r for r in reqs}
    scope_ids = {r.id for r in in_scope(reqs)}
    cov = compute_coverage(sol.components, reqs)
    pairs = [
        PairVerdict(
            component_id=c.id,
            requirement_id=rid,
            requirement_text=by_id[rid].text if rid in by_id else "",
            in_scope=rid in scope_ids,
        )
        for c in sol.components
        for rid in c.requirement_ids
    ]
    scores = SolutionScores(
        components=len(sol.components),
        assumptions=len(sol.assumptions),
        rounds=run.solution.iterations if run.solution else 0,
        cited_total=cov.mandatory_total,
        cited_covered=cov.mandatory_covered,
        cited_coverage=cov.mandatory_covered / cov.mandatory_total if cov.mandatory_total else 1.0,
        stored_coverage_agrees=cov == sol.coverage,
        component_records=[
            ComponentRecord(
                id=c.id, title=c.title, description=c.description, requirement_ids=c.requirement_ids
            )
            for c in sol.components
        ],
        pairs=pairs,
    )
    if judge is None or not sol.components:
        return scores

    ps = run.summary.problem_statement
    constraints = "\n".join(f"- {c.text}" for c in ps.constraints) or "(none)"
    goal = "\n".join(f"- {c.text}" for c in ps.goal) or "(none)"
    blocks = []
    for c in sol.components:
        cited_lines = "\n".join(
            f"    {_req_line(by_id[r])}" for r in c.requirement_ids if r in by_id
        )
        blocks.append(f"{c.id} {c.title}\n  {c.description}\n  Cites:\n{cited_lines}")
    assumptions = "\n".join(f"- {a.text}" for a in sol.assumptions) or "(none)"
    cited = {c.id: list(c.requirement_ids) for c in sol.components}
    out = _once(
        judge,
        lambda: judge.call(
            _solution_schema(cited),
            "judge_solution",
            "judge_solution",
            goal=goal,
            constraints=constraints,
            summary=sol.summary,
            components="\n\n".join(blocks),
            assumptions=assumptions,
        ),
    )
    if out is None:
        return scores
    verdicts = {c.id: c for c in out.components}
    for p in pairs:
        v = verdicts[p.component_id]
        p.addressed = p.requirement_id not in v.not_addressed
        if not p.addressed:
            p.reason = v.reason
    covered = {p.requirement_id for p in pairs if p.addressed and p.in_scope}
    scores.judged_covered = len(covered)
    scores.judged_coverage = len(covered) / cov.mandatory_total if cov.mandatory_total else 1.0
    scores.rubric = {name: getattr(out, name) for name in RUBRIC}
    scores.calendar_components = [c.id for c in out.components if c.calendar]
    return scores


# --------------------------------------------------------------------------------------
# Risks: levels against the definitions, findings coverage
# --------------------------------------------------------------------------------------


class RiskLevelVerdict(BaseModel):
    id: str
    severity: Literal["low", "medium", "high"]
    likelihood: Literal["low", "medium", "high"]
    reason: str = Field(description="At most 20 words; say why when you disagree")


class FindingCoverage(BaseModel):
    id: str
    covered_by: list[str] = Field(
        default_factory=list, description="Risk IDs that address this finding; empty if none"
    )


class RiskVerdicts(BaseModel):
    risks: list[RiskLevelVerdict]
    findings: list[FindingCoverage]


def _risk_schema(risk_ids: list[str], finding_ids: list[str]) -> type[RiskVerdicts]:
    def check(self: RiskVerdicts) -> RiskVerdicts:
        problems = []
        got = [r.id for r in self.risks]
        if sorted(got) != sorted(risk_ids):
            problems.append(f"return exactly one `risks` entry per risk {risk_ids}; got {got}")
        got_f = [f.id for f in self.findings]
        if sorted(got_f) != sorted(finding_ids):
            problems.append(
                f"return exactly one `findings` entry per finding {finding_ids}; got {got_f}"
            )
        bad = sorted({i for f in self.findings for i in f.covered_by if i not in risk_ids})
        if bad:
            problems.append(f"covered_by may only list risk IDs shown; {bad} are not")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return _checked(RiskVerdicts, check)


def _mentions_page(text: str, page: int) -> bool:
    return (
        re.search(rf"\b(?:pages?|p\.)\s*(?:\d+\s*(?:,|and|to|-|–)\s*)*{page}\b", text, re.I)
        is not None
    )


def _findings(run: EvalRun) -> list[FindingVerdict]:
    f = run.findings()
    risks = run.summary.risks.risks
    texts = {
        k.id: f"{k.title} {k.description} {k.justification} {k.mitigation or ''}" for k in risks
    }
    out: list[FindingVerdict] = []

    def add(kind: str, label: str, risk_ids: list[str]) -> None:
        out.append(
            FindingVerdict(
                id=f"F{len(out) + 1}",
                kind=kind,  # type: ignore[arg-type]
                label=label,
                code_covered=bool(risk_ids),
                code_risk_ids=risk_ids,
            )
        )

    by_id = run.requirements
    for a, b in f.conflicts:
        ids = [k.id for k in risks if a in k.requirement_ids and b in k.requirement_ids]
        ta = by_id[a].text if a in by_id else ""
        tb = by_id[b].text if b in by_id else ""
        add("conflict", f"{a} <-> {b}: {ta} / {tb}", ids)
    for d in f.absent_documents:
        name = normalise(d.name)
        ids = [kid for kid, t in texts.items() if name and name in normalise(t)]
        add("absent_document", f"{d.name} (referenced on page {d.page}, not in the PDF)", ids)
    for flag in f.flags:
        ids = [kid for kid, t in texts.items() if _mentions_page(t, flag.page)]
        add("flagged_page", f"page {flag.page} unreadable or incomplete ({flag.reason.value})", ids)
    for rid in f.uncovered_requirement_ids:
        ids = [k.id for k in risks if rid in k.requirement_ids]
        text = by_id[rid].text if rid in by_id else ""
        add("uncovered_requirement", f"{rid} not addressed by the solution: {text}", ids)
    return out


def score_risks(run: EvalRun, judge: Judge | None) -> RiskScores:
    risks = run.summary.risks.risks
    findings = _findings(run)
    verdicts = [
        RiskVerdict(
            id=k.id,
            title=k.title,
            severity=k.severity.value,
            likelihood=k.likelihood.value,
            source=k.source.value,
        )
        for k in risks
    ]
    scores = RiskScores(
        risks=len(risks),
        severity=dict(Counter(k.severity.value for k in risks)),
        likelihood=dict(Counter(k.likelihood.value for k in risks)),
        source=dict(Counter(k.source.value for k in risks)),
        findings=len(findings),
        findings_code_covered=sum(f.code_covered for f in findings),
        risk_verdicts=verdicts,
        finding_verdicts=findings,
    )
    if judge is None or not risks:
        return scores

    by_id = run.requirements
    blocks = []
    for k in risks:
        cites = "".join(f"\n    {_req_line(by_id[r])}" for r in k.requirement_ids if r in by_id)
        # The pipeline's levels and its justification (which argues for them) are not
        # shown, so the judge rates from the description instead of anchoring (S12 tune).
        blocks.append(
            f"{k.id} {k.title}\n  {k.description}"
            + (f"\n  Mitigation: {k.mitigation}" if k.mitigation else "")
            + (f"\n  Cites:{cites}" if cites else "")
        )
    finding_lines = "\n".join(f"{f.id} ({f.kind}) {f.label}" for f in findings) or "(none)"
    out = _once(
        judge,
        lambda: judge.call(
            _risk_schema([k.id for k in risks], [f.id for f in findings]),
            "judge_risks",
            "judge_risks",
            risks="\n\n".join(blocks),
            findings=finding_lines,
        ),
    )
    if out is None:
        return scores
    levels = {r.id: r for r in out.risks}
    for v in verdicts:
        lv = levels[v.id]
        v.judge_severity, v.judge_likelihood, v.reason = lv.severity, lv.likelihood, lv.reason
    scores.severity_agreement = sum(v.severity == v.judge_severity for v in verdicts) / len(
        verdicts
    )
    scores.likelihood_agreement = sum(v.likelihood == v.judge_likelihood for v in verdicts) / len(
        verdicts
    )
    covered = {f.id: f.covered_by for f in out.findings}
    for f in findings:
        f.judge_risk_ids = list(dict.fromkeys(covered.get(f.id, [])))
        f.judge_covered = bool(f.judge_risk_ids)
    scores.findings_judge_covered = sum(bool(f.judge_covered) for f in findings)
    return scores


# --------------------------------------------------------------------------------------
# Cost, latency, retries
# --------------------------------------------------------------------------------------


def score_cost(run: EvalRun) -> CostScores:
    from rfp_agent.graph import stage_totals

    log = run.log
    t = log.totals()
    stages = []
    for s in log.stages:
        calls, st = stage_totals(log, s.stage)
        stages.append(
            StageCost(
                stage=s.stage,
                status=s.status.value,
                wall_s=s.latency_s,
                calls=calls,
                input_tokens=st.input_tokens,
                output_tokens=st.output_tokens,
                cached_input_tokens=st.cached_input_tokens,
                cost_usd=st.cost_usd,
                retries=st.retries,
            )
        )
    retried = [
        RetryRecord(node=n.node, retries=n.retries, last_error=n.last_error)
        for n in log.nodes
        if n.retries
    ]
    return CostScores(
        calls=len(log.nodes),
        input_tokens=t.input_tokens,
        output_tokens=t.output_tokens,
        cached_input_tokens=t.cached_input_tokens,
        cached_share=t.cached_input_tokens / t.input_tokens if t.input_tokens else 0.0,
        cost_usd=t.cost_usd,
        wall_s=run.wall_s,
        retries=t.retries,
        stages=stages,
        retried=retried,
    )
