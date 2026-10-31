"""``summary.json`` and ``summary.md`` for one label: a row per run, a consistency block
per RFP, the cost table and, when present, judge agreement."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from pydantic import BaseModel, Field

from evals.harness.consistency import Consistency, Stats, consistency, stats
from evals.harness.schemas import RunScores
from rfp_agent.schemas import RunTotals


class Row(BaseModel):
    """Headline numbers of one scored run."""

    key: str
    rfp: str
    run: str
    judged: bool
    requirements: int
    gold: int
    recall: float
    recall_code: float = Field(description="Code-tier matches only: the lower bound")
    recall_reachable: float
    matched_by_judge: int
    precision: float | None
    in_scope_share: float | None
    type_accuracy: float | None
    strictness_accuracy: float | None
    checklist_covered: int | None
    checklist_partial: int | None
    checklist_total: int
    claims: dict[str, int] = Field(description="Grounded items per output")
    unsupported: dict[str, int | None] = Field(description="partially + unsupported, per output")
    dangling_ids: int
    entity_misses: int
    components: int
    cited_coverage: float
    judged_coverage: float | None
    calendar_components: int
    rubric: dict[str, int]
    risks: int
    severity: dict[str, int]
    severity_agreement: float | None
    likelihood_agreement: float | None
    findings: int
    findings_code_covered: int
    findings_judge_covered: int | None
    cost_usd: float
    wall_s: float
    retries: int
    judge_cost_usd: float | None
    judge_failures: int | None


def row(s: RunScores) -> Row:
    g = s.grounding.by_output
    return Row(
        key=s.key,
        rfp=s.rfp,
        run=s.run,
        judged=s.judged,
        requirements=s.requirements.extracted,
        gold=s.requirements.gold,
        recall=s.requirements.recall,
        recall_code=s.requirements.matched_by_code / s.requirements.gold
        if s.requirements.gold
        else 0.0,
        recall_reachable=s.requirements.recall_reachable,
        matched_by_judge=s.requirements.matched_by_judge,
        precision=s.requirements.precision,
        in_scope_share=s.requirements.in_scope_share,
        type_accuracy=s.requirements.type_accuracy,
        strictness_accuracy=s.requirements.strictness_accuracy,
        checklist_covered=s.problem.checklist_covered,
        checklist_partial=s.problem.checklist_partial,
        checklist_total=s.problem.checklist_total,
        claims={k: t.items for k, t in g.items()},
        unsupported={k: (t.unsupported_claims if t.judged else None) for k, t in g.items()},
        dangling_ids=sum(t.dangling_ids for t in g.values()),
        entity_misses=sum(t.entity_misses for t in g.values()),
        components=s.solution.components,
        cited_coverage=s.solution.cited_coverage,
        judged_coverage=s.solution.judged_coverage,
        calendar_components=len(s.solution.calendar_components),
        rubric={k: v.score for k, v in s.solution.rubric.items()},
        risks=s.risks.risks,
        severity=s.risks.severity,
        severity_agreement=s.risks.severity_agreement,
        likelihood_agreement=s.risks.likelihood_agreement,
        findings=s.risks.findings,
        findings_code_covered=s.risks.findings_code_covered,
        findings_judge_covered=s.risks.findings_judge_covered,
        cost_usd=s.cost.cost_usd,
        wall_s=s.cost.wall_s,
        retries=s.cost.retries,
        judge_cost_usd=s.judge.totals.cost_usd if s.judge else None,
        judge_failures=s.judge.failures if s.judge else None,
    )


class LabelSummary(BaseModel):
    label: str
    rows: list[Row]
    consistency: list[Consistency]
    judge_cost_usd: float
    pipeline_cost_usd: float
    agreement: dict | None = None


def summarise(
    label: str, scores: Sequence[RunScores], agreement: dict | None = None
) -> LabelSummary:
    by_rfp: dict[str, list[RunScores]] = defaultdict(list)
    for s in sorted(scores, key=lambda x: (x.rfp.lower(), x.run)):
        by_rfp[s.rfp].append(s)
    judge = RunTotals()
    for s in scores:
        if s.judge:
            judge.cost_usd += s.judge.totals.cost_usd
    return LabelSummary(
        label=label,
        rows=[row(s) for group in by_rfp.values() for s in group],
        consistency=[consistency(rfp, group) for rfp, group in by_rfp.items()],
        judge_cost_usd=judge.cost_usd,
        pipeline_cost_usd=sum(s.cost.cost_usd for s in scores),
        agreement=agreement,
    )


# --------------------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------------------


def pct(v: float | None) -> str:
    return "–" if v is None else f"{100 * v:.0f}%"


def num(v: float | int | None, digits: int = 0) -> str:
    if v is None:
        return "–"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


METRIC_LABELS = {
    "requirements": ("requirements", 0, False),
    "recall": ("recall", 0, True),
    "recall_code": ("recall (code only)", 0, True),
    "recall_reachable": ("recall (reachable)", 0, True),
    "precision": ("precision", 0, True),
    "in_scope_share": ("in-scope share", 0, True),
    "type_accuracy": ("type accuracy", 0, True),
    "strictness_accuracy": ("strictness accuracy", 0, True),
    "checklist_coverage": ("checklist coverage", 0, True),
    "unsupported_problem": ("unsupported, problem", 1, False),
    "unsupported_solution": ("unsupported, solution", 1, False),
    "unsupported_risks": ("unsupported, risks", 1, False),
    "entity_misses": ("entity misses", 1, False),
    "components": ("components", 1, False),
    "judged_coverage": ("judged coverage", 0, True),
    "specificity": ("rubric: specificity", 1, False),
    "feasibility": ("rubric: feasibility", 1, False),
    "consistency": ("rubric: consistency", 1, False),
    "risks": ("risks", 1, False),
    "severity_agreement": ("severity agreement", 0, True),
    "cost_usd": ("pipeline cost $", 3, False),
    "wall_s": ("wall s", 0, False),
}


def _stat(s, digits: int, is_pct: bool) -> str:
    if is_pct:
        return f"{100 * s.mean:.0f}% ± {100 * s.sd:.0f} ({100 * s.min:.0f}–{100 * s.max:.0f})"
    return f"{s.mean:.{digits}f} ± {s.sd:.{digits}f} ({s.min:.{digits}f}–{s.max:.{digits}f})"


def render_markdown(summary: LabelSummary) -> str:
    rows = summary.rows
    out = [f"# Eval results: `{summary.label}`", ""]
    out.append(
        f"{len(rows)} runs. Pipeline cost ${summary.pipeline_cost_usd:.2f}, judge cost "
        f"${summary.judge_cost_usd:.2f}. Generated by `python -m evals.harness report "
        f"--label {summary.label}`; how to read each column is in `evals/results/README.md`."
    )
    out += ["", "## Requirements", ""]
    out.append(
        table(
            ["run", "extracted", "gold", "recall", "recall (code only)", "recall (reachable)",
             "by judge", "precision", "in scope", "type acc", "strictness acc"],
            [
                [r.key, str(r.requirements), str(r.gold), pct(r.recall), pct(r.recall_code),
                 pct(r.recall_reachable), str(r.matched_by_judge), pct(r.precision),
                 pct(r.in_scope_share),
                 pct(r.type_accuracy), pct(r.strictness_accuracy)]
                for r in rows
            ],
        )
    )  # fmt: skip
    out += ["", "## Problem statement and grounding", ""]
    out.append(
        table(
            ["run", "checklist", "claims p/s/r", "unsupported p/s/r", "dangling IDs",
             "entity misses"],
            [
                [r.key,
                 f"{num(r.checklist_covered)} (+{num(r.checklist_partial)} partial) / "
                 f"{r.checklist_total}",
                 "/".join(str(r.claims.get(k, 0)) for k in ("problem", "solution", "risks")),
                 "/".join(num(r.unsupported.get(k)) for k in ("problem", "solution", "risks")),
                 str(r.dangling_ids), str(r.entity_misses)]
                for r in rows
            ],
        )
    )  # fmt: skip
    out += ["", "## Solution and risks", ""]
    out.append(
        table(
            ["run", "components", "cited cov", "judged cov", "calendar", "spec/feas/cons",
             "risks", "severity h/m/l", "sev agree", "lik agree", "findings code/judge"],
            [
                [r.key, str(r.components), pct(r.cited_coverage), pct(r.judged_coverage),
                 str(r.calendar_components),
                 "/".join(str(r.rubric.get(k, "–")) for k in
                          ("specificity", "feasibility", "consistency")),
                 str(r.risks),
                 "/".join(str(r.severity.get(k, 0)) for k in ("high", "medium", "low")),
                 pct(r.severity_agreement), pct(r.likelihood_agreement),
                 f"{r.findings_code_covered}/{num(r.findings_judge_covered)} of {r.findings}"]
                for r in rows
            ],
        )
    )  # fmt: skip
    out += ["", "## Cost", ""]
    out.append(
        table(
            ["run", "pipeline $", "wall s", "retries", "judge $", "judge failures"],
            [
                [r.key, f"{r.cost_usd:.3f}", f"{r.wall_s:.0f}", str(r.retries),
                 num(r.judge_cost_usd, 3), num(r.judge_failures)]
                for r in rows
            ],
        )
    )  # fmt: skip
    out += ["", "## Consistency across runs", ""]
    out.append("Mean ± sample sd (min–max) over each RFP's runs.")
    rfps = [c.rfp for c in summary.consistency]
    body = []
    for name, (label, digits, is_pct) in METRIC_LABELS.items():
        cells = []
        for c in summary.consistency:
            s = c.metrics.get(name)
            cells.append("–" if s is None else _stat(s, digits, is_pct))
        body.append([label, *cells])
    body.append(
        ["matched-gold Jaccard", *[num(c.matched_gold_jaccard, 2) for c in summary.consistency]]
    )
    body.append(["checklist Jaccard", *[num(c.checklist_jaccard, 2) for c in summary.consistency]])
    body.append(["runs", *[str(len(c.runs)) for c in summary.consistency]])
    out += ["", table(["metric", *rfps], body)]
    if summary.agreement:
        out += ["", "## Judge agreement with hand labels", ""]
        a = summary.agreement
        out.append(
            table(
                ["verdict", "items", "agree", "rate"],
                [
                    [k, str(v["items"]), str(v["agree"]), pct(v["rate"])]
                    for k, v in a["by_kind"].items()
                ]
                + [["all", str(a["items"]), str(a["agree"]), pct(a["rate"])]],
            )
        )
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------------------
# Two labels side by side (ablations and before/after tables, S13)
# --------------------------------------------------------------------------------------

DIFF_COLUMNS: dict[str, list[str]] = {
    "problem": ["checklist_covered", "checklist_partial", "unsupported.problem", "cost_usd"],
    "requirements": ["requirements", "recall", "recall_code", "precision", "in_scope_share"],
    "solution": [
        "judged_coverage",
        "cited_coverage",
        "calendar_components",
        "rubric.specificity",
        "rubric.feasibility",
        "rubric.consistency",
    ],
}
PCT_COLUMNS = {
    "recall", "recall_code", "recall_reachable", "precision", "in_scope_share",
    "type_accuracy", "strictness_accuracy", "cited_coverage", "judged_coverage",
    "severity_agreement", "likelihood_agreement",
}  # fmt: skip
COLUMN_DIGITS = {"cost_usd": 3, "wall_s": 0, "judge_cost_usd": 3}


def cell(row: Row, column: str) -> float | None:
    """A ``Row`` value as a float; ``unsupported.problem`` and ``rubric.specificity``
    reach into the dicts. A missing sub-key or an unjudged value is ``None``; an unknown
    column raises ``KeyError``."""
    head, _, sub = column.partition(".")
    if head not in Row.model_fields:
        raise KeyError(column)
    value = getattr(row, head)
    if isinstance(value, dict):
        if not sub:
            raise KeyError(column)
        value = value.get(sub)
    elif sub:
        raise KeyError(column)
    return None if value is None else float(value)


class DiffRow(BaseModel):
    rfp: str
    column: str
    a: Stats | None
    b: Stats | None
    delta: float | None = Field(None, description="b mean minus a mean")


def diff(a: LabelSummary, b: LabelSummary, columns: Sequence[str]) -> list[DiffRow]:
    """Per-RFP stats of each column in both labels, RFPs in order of appearance."""
    rfps = list(dict.fromkeys([r.rfp for r in a.rows] + [r.rfp for r in b.rows]))
    out = []
    for rfp in rfps:
        for column in columns:
            sa = stats([cell(r, column) for r in a.rows if r.rfp == rfp])
            sb = stats([cell(r, column) for r in b.rows if r.rfp == rfp])
            delta = sb.mean - sa.mean if sa is not None and sb is not None else None
            out.append(DiffRow(rfp=rfp, column=column, a=sa, b=sb, delta=delta))
    return out


def _column_label(column: str) -> str:
    """The consistency table's label where one exists (``unsupported.problem`` ->
    "unsupported, problem", ``rubric.specificity`` -> "rubric: specificity")."""
    head, _, sub = column.partition(".")
    for key in (f"{head}_{sub}", sub, head):
        if key and key in METRIC_LABELS:
            return METRIC_LABELS[key][0]
    return column.replace(".", " ")


def _mean_sd(s: Stats | None, column: str) -> str:
    if s is None:
        return "–"
    is_pct = column in PCT_COLUMNS
    digits = COLUMN_DIGITS.get(column, 1)
    mean = f"{100 * s.mean:.0f}%" if is_pct else f"{s.mean:.{digits}f}"
    if s.n < 2:
        return f"{mean} (n=1)"
    sd = f"{100 * s.sd:.0f}" if is_pct else f"{s.sd:.{digits}f}"
    return f"{mean} ± {sd} (n={s.n})"


def _delta(d: float | None, column: str) -> str:
    if d is None:
        return "–"
    if column in PCT_COLUMNS:
        return f"{100 * d:+.0f} pp"
    return f"{d:+.{COLUMN_DIGITS.get(column, 1)}f}"


def render_diff(a: LabelSummary, b: LabelSummary, rows: Sequence[DiffRow]) -> str:
    out = [
        f"# `{a.label}` vs `{b.label}`",
        "",
        f"Per-RFP mean ± sample sd over each label's runs; delta is `{b.label}` minus "
        f"`{a.label}`. Generated by `python -m evals.harness diff {a.label} {b.label}`.",
        "",
        table(
            ["rfp", "metric", a.label, b.label, "delta"],
            [
                [
                    r.rfp,
                    _column_label(r.column),
                    _mean_sd(r.a, r.column),
                    _mean_sd(r.b, r.column),
                    _delta(r.delta, r.column),
                ]
                for r in rows
            ],
        ),  # fmt: skip
    ]
    return "\n".join(out) + "\n"
