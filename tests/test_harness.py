"""Eval harness (S12) with a scripted judge over the committed sample runs. No network.

The fake judge reads the IDs out of each judge prompt and answers with fixed rules, so
the tests check the plumbing (batching, ID validation, verdict mapping, arithmetic), not
judgment.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import BaseMessage
from typer.testing import CliRunner

from evals.gold.label import final_path, load_gold
from evals.gold.schema import GoldRequirement
from evals.harness import __main__ as cli
from evals.harness import agreement
from evals.harness.consistency import consistency, jaccard_mean, stats
from evals.harness.grounding import entities, missing_entities
from evals.harness.judge import Judge, exact_ids, judge_cost_from_log, merge_judge_logs
from evals.harness.load import EvalRun, rfp_name
from evals.harness.match import ItemVerdicts, code_score, score_requirements
from evals.harness.pairwise import compare, load_output
from evals.harness.report import cell, diff, render_diff, render_markdown, summarise
from evals.harness.score import load_scores, parse_sections, score_run
from evals.harness.sections import score_problem
from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.config import Settings
from rfp_agent.schemas import Requirement, RequirementType, RunLog, Strictness

SAMPLES = Path(__file__).resolve().parents[1] / "runs" / "samples"
SAMPLE_NAMES = ["missouri", "nyesd", "colfax", "federal_way"]
SETTINGS = Settings(_env_file=None, max_structured_retries=1, llm_concurrency=4)


# --------------------------------------------------------------------------------------
# Scripted judge
# --------------------------------------------------------------------------------------


def block(text: str, tag: str) -> str:
    start = text.rfind(f"<{tag}>")
    end = text.rfind(f"</{tag}>")
    return text[start + len(tag) + 2 : end]


def ids(pattern: str, text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(pattern, text, flags=re.M)))


def judge_reply(messages: list[BaseMessage]):
    """Fixed answers per judge prompt, recognised by its opening sentence."""
    p = str(messages[0].content)
    if "against a gold standard" in p:
        gold = ids(r"^(GR\d+) \[", block(p, "gold"))
        cands = ids(r"^(R\d{3,}) \[", block(p, "candidates"))
        matches = [
            {"gold_id": g, "requirement_ids": ([cands[0], "R999"] if n == 0 else []), "reason": "x"}
            for n, g in enumerate(gold)
        ]
        return tool_call_msg("MatchVerdicts", {"matches": matches})
    if "grading the output of an automated requirements extractor" in p:
        rids = ids(r"^(R\d{3,}) \[", block(p, "requirements"))
        verdicts = [
            {
                "id": r,
                "supported": True,
                "is_requirement": r != "R001",
                "in_scope": int(r[1:]) % 2 == 0,
                "reason": "x",
            }
            for r in rids
        ]
        return tool_call_msg("ItemVerdicts", {"verdicts": verdicts})
    if "check whether statements" in p:
        iids = ids(r"^(I\d{3}) \(", block(p, "items"))
        verdicts = [
            {
                "id": i,
                "verdict": "unsupported" if i == "I000" else "supported",
                "reasonable_inference": True,
                "reason": "x",
            }
            for i in iids
        ]
        return tool_call_msg("ClaimVerdicts", {"verdicts": verdicts})
    if "checklist of facts" in p:
        labels = ids(r"^(\w+\[\d+\]) ", block(p, "statement"))
        facts = ids(r"^(GC\d+) ", block(p, "checklist"))
        out = [
            {
                "gold_id": f,
                "status": "covered" if n else "missing",
                "claim": labels[0] if n else None,
                "reason": "x",
            }
            for n, f in enumerate(facts)
        ]
        return tool_call_msg("ChecklistVerdicts", {"facts": out})
    if "review a proposed solution approach" in p:
        comps, cites, current = [], {}, None
        for line in block(p, "components").splitlines():
            if m := re.match(r"^(C\d{2}) ", line):
                current = m.group(1)
                comps.append(current)
                cites[current] = []
            elif m := re.match(r"^\s+(R\d{3,}) \[", line):
                cites[current].append(m.group(1))
        rubric = {"score": 4, "reason": "x"}
        return tool_call_msg(
            "SolutionVerdict",
            {
                "specificity": rubric,
                "feasibility": rubric,
                "consistency": rubric,
                "components": [
                    {"id": c, "not_addressed": cites[c][:1] if n == 0 else [], "calendar": n == 1,
                     "reason": "x"}
                    for n, c in enumerate(comps)
                ],
            },
        )  # fmt: skip
    if "review the risk register" in p:
        risks = ids(r"^(K\d{2}) ", block(p, "risks"))
        assert "severity" not in block(p, "risks")  # levels hidden from the judge
        findings = ids(r"^(F\d+) \(", block(p, "findings"))
        return tool_call_msg(
            "RiskVerdicts",
            {
                "risks": [
                    {"id": k, "severity": "high", "likelihood": "medium", "reason": "x"}
                    for k in risks
                ],
                "findings": [{"id": f, "covered_by": [risks[0]]} for f in findings],
            },
        )
    raise AssertionError(f"unexpected prompt: {p[:80]}")


def make_judge(responder=judge_reply) -> tuple[Judge, ScriptedChatModel]:
    model = ScriptedChatModel(responder=responder)
    return Judge(model, settings=SETTINGS), model


@pytest.fixture(scope="module")
def fw_run() -> EvalRun:
    return EvalRun.load(SAMPLES / "federal_way")


@pytest.fixture(scope="module")
def fw_judged(fw_run):
    judge, model = make_judge()
    return score_run(fw_run, judge, key="1"), judge, model


# --------------------------------------------------------------------------------------
# Loading and code metrics
# --------------------------------------------------------------------------------------


def test_rfp_name_matches_gold_case_insensitively():
    assert rfp_name("data/rfps/NYESD.pdf") == "NYESD"
    assert rfp_name("data\\rfps\\federal_way.pdf") == "federal_way"
    run = EvalRun.load(SAMPLES / "nyesd")
    assert run.rfp == "NYESD"
    assert run.gold().rfp == "NYESD"


def test_source_blocks_carry_the_heading_and_skip_unknown_ids(fw_run):
    cid = next(iter(fw_run.chunks))
    rid = next(iter(fw_run.requirements))
    blocks = dict(fw_run.source_blocks([cid, rid, "S999.9", cid]))
    assert list(blocks) == [cid, rid]
    assert blocks[cid].startswith("[") and "page" in blocks[cid].splitlines()[0]
    assert "Quote:" in blocks[rid]


def _req(quote: str, text: str = "Something unrelated.") -> Requirement:
    return Requirement(
        id="R001",
        text=text,
        type=RequirementType.TECHNICAL,
        strictness=Strictness.MANDATORY,
        quote=quote,
        chunk_ids=["S1.1"],
    )


def _gold(quote: str) -> GoldRequirement:
    return GoldRequirement(
        id="GR001",
        text="x",
        type=RequirementType.TECHNICAL,
        strictness=Strictness.MANDATORY,
        quote=quote,
    )


def test_code_score_tiers():
    g = _gold("The system must comply with WCAG 2.1 AA standards")
    assert code_score(g, _req("**The system must comply** with WCAG 2.1 AA standards.")) == 1.0
    assert code_score(g, _req("must comply with WCAG 2.1 AA")) == 1.0  # contained, 6 words
    assert code_score(g, _req("WCAG")) is None  # too short to count as containment
    assert (
        code_score(g, _req("x", text="The system must comply with WCAG 2.1 AA standards.")) == 1.0
    )
    partial = code_score(g, _req("The system shall comply with WCAG 2.1 AA guidelines"))
    assert partial is not None and 0.5 <= partial < 1.0
    assert code_score(g, _req("Proposals are due on Friday at noon")) is None


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_code_only_scores_on_every_sample(name):
    s = score_run(EvalRun.load(SAMPLES / name), None, key="1")
    r = s.requirements
    assert not s.judged and s.judge is None
    assert r.extracted > 0 and 0 < r.recall <= 1
    assert r.matched_by_judge == 0 and r.precision is None
    assert r.matched_gold == sum(m.tier == "code" for m in r.matches)
    assert s.solution.stored_coverage_agrees
    assert s.solution.judged_coverage is None
    assert all(t.dangling_ids == 0 for t in s.grounding.by_output.values())
    assert s.risks.risks == len(s.risks.risk_verdicts) >= 3
    assert s.cost.cost_usd > 0 and s.cost.calls > 0 and s.cost.stages
    assert s.problem.checklist_total == 12 and s.problem.checklist_coverage is None


def test_federal_way_reachable_recall_excludes_the_image_table():
    s = score_run(EvalRun.load(SAMPLES / "federal_way"), None)
    r = s.requirements
    assert r.gold - r.gold_reachable == 8  # page 5 ERP table, quote_verifiable=false
    assert r.recall_reachable > r.recall


def test_retries_are_listed_with_their_node():
    s = score_run(EvalRun.load(SAMPLES / "missouri"), None)
    assert [x.node for x in s.cost.retried] == ["problem_synthesis"]
    # The S16 samples postdate the F7 fix, so the cause is recorded.
    assert s.cost.retried[0].last_error.startswith("1 validation error for ProblemStatement")


# --------------------------------------------------------------------------------------
# Entity check
# --------------------------------------------------------------------------------------


def test_entities_numbers_and_names():
    text = (
        "The budget is $175,000 and proposals are due August 21, 2024 under EPG Section "
        "236.4.6.2; MoDOT's Right of Way staff review the MoDOT-approved drafts."
    )
    assert entities(text) == ["175000", "21", "2024", "236.4.6.2", "EPG", "MoDOT", "Right", "Way"]


def test_missing_entities_respects_number_boundaries_and_formats():
    claim = "The cap is $175,000, due 21 August 2024, per MoDOT."
    assert missing_entities(claim, "not to exceed $175,000.00 by 8/21/2024 (MoDOT)") == []
    assert missing_entities(claim, "not to exceed $1,750,000 by 8/21/2024 (MoDOT)") == ["175000"]
    assert missing_entities(claim, "not to exceed $175,000 by 8/21/2024 (MHTC)") == ["MoDOT"]


# --------------------------------------------------------------------------------------
# Judged scoring with the scripted judge
# --------------------------------------------------------------------------------------


def test_judge_tier_matches_and_drops_unknown_ids(fw_judged):
    s, _, _ = fw_judged
    r = s.requirements
    judged = [m for m in r.matches if m.tier == "judge"]
    assert r.matched_by_judge == len(judged) >= 1
    assert all("R999" not in m.matched_ids for m in judged)
    assert r.matched_gold == r.matched_by_code + r.matched_by_judge
    assert all(m.best_type for m in r.matches if m.tier != "none")


def test_precision_counts_every_item(fw_judged):
    s, _, _ = fw_judged
    r = s.requirements
    assert r.judged == r.extracted
    assert r.precision == pytest.approx((r.extracted - 1) / r.extracted)  # R001 not a requirement
    even = sum(int(v.id[1:]) % 2 == 0 for v in r.verdicts)
    assert r.in_scope_share == pytest.approx(even / r.extracted)


def test_grounding_verdicts_fill_every_cited_item(fw_judged):
    s, _, _ = fw_judged
    tallies = s.grounding.by_output
    cited = [i for i in s.grounding.items if i.cited]
    assert sum(t.judged for t in tallies.values()) == len(cited)
    assert sum(t.unsupported for t in tallies.values()) == 1  # only I000
    assert tallies["problem"].unsupported_claims == 1
    assert all(i.reasonable_inference is None for i in cited if i.kind in ("fact", "risk"))
    assumptions = [i for i in cited if i.where.startswith("solution.assumptions")]
    assert assumptions and all(i.kind == "assumption" for i in assumptions)
    assert all(i.reasonable_inference is True for i in assumptions)


def test_checklist_solution_and_risk_judges(fw_judged):
    s, _, _ = fw_judged
    p = s.problem
    assert (p.checklist_covered, p.checklist_partial) == (11, 0)
    assert p.checklist[0].status == "missing" and p.checklist[0].claim is None
    sol = s.solution
    assert set(sol.rubric) == {"specificity", "feasibility", "consistency"}
    assert sol.calendar_components == ["C02"]
    assert sum(not p.addressed for p in sol.pairs) == 1
    assert sol.judged_coverage <= sol.cited_coverage
    risks = s.risks
    expected = sum(v.severity == "high" for v in risks.risk_verdicts) / risks.risks
    assert risks.severity_agreement == pytest.approx(expected)
    assert risks.findings_judge_covered == risks.findings


def test_judge_cost_is_logged(fw_judged):
    s, judge, model = fw_judged
    assert s.judge.calls == len(model.calls) and s.judge.failures == 0
    assert {"judge_requirements", "judge_grounding", "judge_checklist"} <= set(s.judge.per_node)
    assert "judge_grounding" in judge.recorder.log.prompt_hashes


def test_score_file_round_trip(fw_judged, tmp_path):
    s, _, _ = fw_judged
    path = tmp_path / "s.json"
    path.write_text(s.model_dump_json(), encoding="utf-8")
    assert load_scores(path) == s


def test_exact_ids_rejects_missing_and_invented_ids_and_retries(fw_run):
    answers = [
        tool_call_msg("ItemVerdicts", {"verdicts": [
            {"id": "R001", "supported": True, "is_requirement": True, "in_scope": True,
             "reason": "x"},
            {"id": "R777", "supported": True, "is_requirement": True, "in_scope": True,
             "reason": "x"},
        ]}),
        tool_call_msg("ItemVerdicts", {"verdicts": [
            {"id": i, "supported": True, "is_requirement": True, "in_scope": True,
             "reason": "x"} for i in ("R001", "R002")
        ]}),
    ]  # fmt: skip
    model = ScriptedChatModel(responses=answers)
    judge = Judge(model, settings=SETTINGS)
    schema = exact_ids(ItemVerdicts, "verdicts", "id", ["R001", "R002"])
    out = judge.call(schema, "judge_requirements", "t", sources="s", requirements="r")
    assert [v.id for v in out.verdicts] == ["R001", "R002"]
    feedback = str(model.calls[1][-1].content)
    assert "missing entries for ['R002']" in feedback and "R777" in feedback


def test_failed_judge_call_leaves_fields_empty_and_is_counted(fw_run):
    judge, _ = make_judge(lambda _: tool_call_msg("ChecklistVerdicts", {"facts": []}))
    p = score_problem(fw_run, fw_run.gold(), judge)
    assert p.checklist_coverage is None and judge.failures == 1


# --------------------------------------------------------------------------------------
# Partial rescoring (score --only)
# --------------------------------------------------------------------------------------


def _prompts(model: ScriptedChatModel) -> list[str]:
    return [str(c[0].content) for c in model.calls]


def test_requirement_halves_rescore_independently(fw_run, fw_judged):
    s, _, _ = fw_judged
    gold = fw_run.gold()
    judge, model = make_judge()
    r = score_requirements(fw_run, gold, judge, match=False, previous=s.requirements)
    assert not any("against a gold standard" in p for p in _prompts(model))
    assert r.matches == s.requirements.matches and r.recall == s.requirements.recall
    assert r.verdicts == s.requirements.verdicts and r.precision == s.requirements.precision
    judge, model = make_judge()
    r = score_requirements(fw_run, gold, judge, precision=False, previous=s.requirements)
    assert not any("grading the output" in p for p in _prompts(model))
    assert r.matches == s.requirements.matches and r.verdicts == s.requirements.verdicts
    code_only = score_requirements(fw_run, gold, make_judge()[0], match=False, precision=False)
    assert code_only.matched_by_judge == 0 and code_only.precision is None


def test_score_run_only_keeps_the_other_sections(fw_run, fw_judged):
    s, _, _ = fw_judged
    judge, _ = make_judge()
    t = score_run(fw_run, judge, key="1", only={"problem"}, previous=s)
    assert set(judge.cost().per_node) == {"judge_checklist"}
    assert t.judged and t.judge == judge.cost()
    assert (t.requirements, t.solution, t.risks, t.grounding) == (
        s.requirements, s.solution, s.risks, s.grounding)  # fmt: skip
    assert t.problem.checklist_coverage is not None
    judge, model = make_judge()
    c = score_run(fw_run, judge, key="1", only={"cost"})
    assert not model.calls and not c.judged and c.judge is None
    assert c.requirements.precision is None and c.problem.checklist_coverage is None
    with pytest.raises(ValueError, match="previous scores are for run"):
        score_run(fw_run, None, only={"cost"}, previous=s.model_copy(update={"run_id": "x"}))


def test_merge_judge_logs(fw_run, fw_judged):
    _, judge, _ = fw_judged
    old = judge.recorder.log
    fresh, _ = make_judge()
    score_problem(fw_run, fw_run.gold(), fresh)
    new = fresh.recorder.log
    merged = merge_judge_logs(old, new, {"judge_checklist"})
    nodes = [n.node for n in merged.nodes]
    kept = [n.node for n in old.nodes if n.node != "judge_checklist"]
    assert nodes == kept + [n.node for n in new.nodes]
    assert nodes.count("judge_checklist") == len(new.nodes) >= 1
    assert merged.prompt_hashes["judge_checklist"] == new.prompt_hashes["judge_checklist"]
    cost = judge_cost_from_log(judge.spec, merged, failures=0)
    assert cost.calls == len(nodes) and set(cost.per_node) == set(nodes)


def test_parse_sections():
    assert parse_sections(["match,precision", "cost"]) == {"match", "precision", "cost"}
    assert parse_sections(None) is None and parse_sections([""]) is None
    with pytest.raises(ValueError, match="unknown section 'bogus'"):
        parse_sections(["bogus"])


# --------------------------------------------------------------------------------------
# Consistency, pairwise, agreement, report
# --------------------------------------------------------------------------------------


def test_stats_and_jaccard():
    s = stats([1, 2, None, 3])
    assert (s.n, s.mean, s.sd, s.min, s.max) == (3, 2.0, 1.0, 1.0, 3.0)
    assert stats([None]) is None
    assert jaccard_mean([{"a", "b"}, {"a"}, {"a", "b"}]) == pytest.approx((0.5 + 1 + 0.5) / 3)
    assert jaccard_mean([{"a"}]) is None


def test_consistency_over_runs(fw_judged):
    s, _, _ = fw_judged
    other = s.model_copy(update={"run": "2"}, deep=True)
    other.requirements.recall = 0.0
    c = consistency("federal_way", [s, other])
    assert c.metrics["recall"].n == 2 and c.metrics["recall"].min == 0.0
    assert c.matched_gold_jaccard == 1.0 and c.checklist_jaccard == 1.0


def _pref(choice: str):
    return tool_call_msg("Preference", {"preferred": choice, "reason": "x"})


@pytest.mark.parametrize(
    ("answers", "winner", "bias"),
    [(("A", "B"), "a", False), (("B", "A"), "b", False), (("A", "A"), "tie", True),
     (("tie", "A"), "tie", False)],
)  # fmt: skip
def test_pairwise_order_swap(answers, winner, bias):
    model = ScriptedChatModel(responses=[_pref(a) for a in answers])
    judge = Judge(model, settings=SETTINGS)
    a = load_output(SAMPLES / "federal_way", "problem")
    b = load_output(SAMPLES / "federal_way" / "summary.json", "problem")
    result = compare(a, b, what="problem", gold=load_gold(final_path("federal_way")), judge=judge)
    assert (result.winner, result.order_bias) == (winner, bias)
    first, second = (str(c[0].content) for c in model.calls)
    assert first.index("<a>") < first.index("<b>")
    assert "Version A" in second and "reference" in first.lower()


def test_agreement_sample_hides_the_judge_and_agree_scores_it(fw_judged):
    s, _, _ = fw_judged
    counts = {"precision": 4, "grounding": 4, "checklist": 2, "coverage": 2}
    items = agreement.sample([s], counts)
    assert items == agreement.sample([s], counts)  # seeded
    assert len(items) == 12 and len({i.id for i in items}) == 12
    assert all(i.human is None and i.evidence for i in items)
    assert "verdict" not in json.dumps([i.model_dump() for i in items])
    for i in items:  # label exactly as the judge did, then flip one
        key, kind, ref = i.id.split("|", 2)
        i.human = agreement._judge_value(s, kind, ref)
    items[0].human = not items[0].human if isinstance(items[0].human, bool) else "missing"
    result = agreement.agree(items, [s])
    assert result["items"] == 12 and result["agree"] == 11
    assert result["disagreements"][0]["id"] == items[0].id


def test_report_mixes_judged_and_code_only_rows(fw_run, fw_judged):
    s, _, _ = fw_judged
    summary = summarise("t", [s, score_run(fw_run, None, key="2")])
    assert "federal_way-2" in render_markdown(summary)
    assert summary.consistency[0].metrics["precision"].n == 1


def test_diff_cells_and_table(fw_judged):
    s, _, _ = fw_judged
    a = summarise("a", [s])
    other = s.model_copy(update={"run": "2"}, deep=True)
    other.requirements.recall = 0.5
    b = summarise("b", [s, other])
    r = a.rows[0]
    assert cell(r, "unsupported.problem") == 1.0 and cell(r, "rubric.specificity") == 4.0
    assert cell(r, "rubric.missing") is None and cell(r, "recall") == s.requirements.recall
    for bad in ("nope", "rubric", "recall.x"):
        with pytest.raises(KeyError):
            cell(r, bad)
    rows = diff(a, b, ["recall", "unsupported.problem"])
    rec = rows[0]
    assert (rec.rfp, rec.column, rec.a.n, rec.b.n) == ("federal_way", "recall", 1, 2)
    assert rec.delta == pytest.approx((s.requirements.recall + 0.5) / 2 - s.requirements.recall)
    md = render_diff(a, b, rows)
    assert "| federal_way | recall |" in md and "(n=1)" in md and "± " in md and " pp |" in md
    assert "| unsupported, problem |" in md


def test_report_renders_every_section(fw_judged):
    s, _, _ = fw_judged
    summary = summarise("t", [s], {"items": 1, "agree": 1, "rate": 1.0, "by_kind": {
        "precision": {"items": 1, "agree": 1, "rate": 1.0}}})  # fmt: skip
    md = render_markdown(summary)
    for heading in ("## Requirements", "## Problem statement and grounding",
                    "## Solution and risks", "## Cost", "## Consistency across runs",
                    "## Judge agreement"):  # fmt: skip
        assert heading in md
    assert "federal_way-1" in md


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


@pytest.fixture
def cli_dirs(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    results = tmp_path / "results"
    samples = tmp_path / "samples"
    shutil.copytree(SAMPLES / "federal_way", samples / "federal_way")
    monkeypatch.setattr(cli, "EVAL_RUNS", runs)
    monkeypatch.setattr(cli, "RESULTS", results)
    monkeypatch.setattr(cli, "SAMPLES", samples)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    return runs, results


def _stub_pipeline(monkeypatch) -> list[tuple[str, str, dict]]:
    """Replace ``run_pipeline`` with a stub that writes the Federal Way sample summary
    and records ``(pdf, run_id, extra kwargs)``."""
    import rfp_agent.graph as graph

    summary = EvalRun.load(SAMPLES / "federal_way").summary
    calls: list[tuple[str, str, dict]] = []

    def fake_run_pipeline(pdf, *, runs_dir, run_id, **kw):
        calls.append((Path(pdf).as_posix(), run_id, kw))
        out = runs_dir / run_id
        out.mkdir(parents=True)
        (out / "summary.json").write_text(summary.model_dump_json(), encoding="utf-8")

        class Log:
            def totals(self):
                from rfp_agent.schemas import RunTotals

                return RunTotals(cost_usd=0.05)

        class Result:
            run_log = Log()

        Result.summary = summary
        return Result()

    monkeypatch.setattr(graph, "run_pipeline", fake_run_pipeline)
    return calls


def test_cli_run_reuses_the_sample_and_adds_fresh_runs(cli_dirs, monkeypatch):
    runs, _ = cli_dirs
    calls = _stub_pipeline(monkeypatch)
    result = CliRunner().invoke(
        cli.app, ["run", "--label", "t", "--rfp", "federal_way", "--runs", "2", "--reuse-samples"]
    )
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (runs / "t" / "federal_way").iterdir()) == ["1", "2", "3"]
    assert [c[1] for c in calls] == ["2", "3"]
    assert calls[0][0].endswith("data/rfps/federal_way.pdf")
    assert calls[0][2] == {"full_text_problem": None, "single_call_extraction": None}


def test_cli_run_forwards_the_ablation_flags(cli_dirs, monkeypatch):
    calls = _stub_pipeline(monkeypatch)
    result = CliRunner().invoke(
        cli.app,
        ["run", "--label", "t", "--rfp", "Federal_Way", "--runs", "1", "--full-text-problem",
         "--no-single-call-extraction"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert [c[2] for c in calls] == [{"full_text_problem": True, "single_call_extraction": False}]


def test_gold_name_is_case_insensitive():
    import typer

    assert cli._gold_name("nyesd") == "NYESD" and cli._rfps("federal_way", False) == ["federal_way"]
    with pytest.raises(typer.BadParameter):
        cli._gold_name("x")


def test_cli_score_only_merges_the_scores_and_the_judge_log(cli_dirs, monkeypatch):
    runs, results = cli_dirs
    shutil.copytree(SAMPLES / "federal_way", runs / "t" / "federal_way" / "1")
    monkeypatch.setattr(cli, "_judge", lambda: make_judge()[0])
    runner = CliRunner()
    r = runner.invoke(cli.app, ["score", "--label", "t"])
    assert r.exit_code == 0, r.output
    path = results / "t" / "scores" / "federal_way-1.json"
    log_path = results / "t" / "judge_logs" / "federal_way-1.json"
    before = load_scores(path)
    before_nodes = [n.node for n in RunLog.model_validate_json(log_path.read_text("utf-8")).nodes]

    r = runner.invoke(cli.app, ["score", "--label", "t", "--only", "problem,cost"])
    assert r.exit_code == 0 and "only=cost,problem" in r.output, r.output
    after = load_scores(path)
    assert after.requirements == before.requirements and after.judged
    assert after.judge.per_node.keys() == before.judge.per_node.keys()
    assert after.judge.calls == before.judge.calls
    after_nodes = [n.node for n in RunLog.model_validate_json(log_path.read_text("utf-8")).nodes]
    assert sorted(after_nodes) == sorted(before_nodes)
    assert after_nodes[-1] == "judge_checklist" and after_nodes[0] != "judge_checklist"

    r = runner.invoke(cli.app, ["score", "--label", "t", "--only", "bogus"])
    assert r.exit_code == 2


def test_cli_diff(cli_dirs, fw_judged):
    _, results = cli_dirs
    s, _, _ = fw_judged
    for label in ("a", "b"):
        (results / label).mkdir(parents=True)
        (results / label / "summary.json").write_text(
            summarise(label, [s]).model_dump_json(), encoding="utf-8"
        )
    runner = CliRunner()
    r = runner.invoke(cli.app, ["diff", "a", "b", "--what", "requirements"])
    assert r.exit_code == 0, r.output
    assert "| federal_way | recall (code only) |" in r.output and "+0 pp" in r.output
    r = runner.invoke(cli.app, ["diff", "a", "b", "-c", "recall,rubric.specificity"])
    assert r.exit_code == 0 and "| rubric: specificity |" in r.output
    assert runner.invoke(cli.app, ["diff", "a", "nope"]).exit_code == 1
    assert runner.invoke(cli.app, ["diff", "a", "b", "-c", "nope"]).exit_code == 2


def test_cli_score_no_judge_then_report(cli_dirs):
    runs, results = cli_dirs
    shutil.copytree(SAMPLES / "federal_way", runs / "t" / "federal_way" / "1")
    runner = CliRunner()
    r = runner.invoke(cli.app, ["score", "--label", "t", "--no-judge"])
    assert r.exit_code == 0, r.output
    assert (results / "t" / "scores" / "federal_way-1.json").exists()
    r = runner.invoke(cli.app, ["score", "--label", "t", "--no-judge"])
    assert "skipping" in r.output
    r = runner.invoke(cli.app, ["report", "--label", "t"])
    assert r.exit_code == 0, r.output
    summary = json.loads((results / "t" / "summary.json").read_text(encoding="utf-8"))
    assert summary["rows"][0]["key"] == "federal_way-1"
    assert (results / "t" / "summary.md").exists()


def test_cli_missing_judge_key_exits_2(cli_dirs, monkeypatch):
    runs, _ = cli_dirs
    shutil.copytree(SAMPLES / "federal_way", runs / "t" / "federal_way" / "1")
    from evals.harness import judge as judge_mod
    from rfp_agent.llm import MissingApiKeyError

    def no_key(*a, **k):
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set")

    monkeypatch.setattr(judge_mod, "build_judge_model", no_key)
    r = CliRunner().invoke(cli.app, ["score", "--label", "t"])
    assert r.exit_code == 2
