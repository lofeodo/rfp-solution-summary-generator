# Eval results

One directory per results set (`<label>`), produced by the S12 harness
(`evals/harness/`). `baseline/` is the pipeline as merged after S10: three runs per
RFP, the committed sample (`runs/samples/<rfp>`) as run 1 and two fresh runs, all
scored by the judge (`anthropic:claude-sonnet-5-5`, effort `medium`).

| File | What it is |
|---|---|
| `summary.md` | The tables: one row per run, then consistency per RFP, then judge agreement. Start here. |
| `summary.json` | The same numbers as data (`evals.harness.report.LabelSummary`). |
| `scores/<rfp>-<k>.json` | Everything scored for one run (`evals.harness.schemas.RunScores`), including every per-item verdict with the item's text and the judge's reason, so it reads without the run directory. |
| `judge_logs/<rfp>-<k>.json` | The judge's own run log: one entry per judge call with tokens, cost, latency, retries and the prompt hashes. |
| `agreement_sample.json` | The hand-labelling sample as exported (judge answers not in the file). |
| `agreement_labels.json` | The same items with the `human` field filled in. |
| `pairwise_*.json` | Pairwise judge results (`compare`). |

The run directories themselves are under `runs/evals/<label>/` and are not committed
(about 650 KB each); `scores/*.json` record each run's path and run ID.

## Reproduce

```
python -m evals.harness run --label baseline --all --runs 2 --reuse-samples   # ~$0.60
python -m evals.harness score --label baseline                                # ~$5, judge
python -m evals.harness report --label baseline
python -m evals.harness sample --label baseline   # then fill `human` into agreement_labels.json
python -m evals.harness agree --label baseline
python -m evals.harness compare runs/samples/missouri runs/evals/pairwise/missouri_full_text_problem.json --what problem --rfp missouri
```

`score --no-judge` gives the code metrics only, for free. `score` skips runs that
already have a score file unless `--force`, so an interrupted scoring run resumes.

### Partial rescoring and label comparison (S13)

```
python -m evals.harness score --label baseline --only match          # one judge, ~$0.40
python -m evals.harness run --label ablation_full_text --all --runs 2 --full-text-problem
python -m evals.harness score --label ablation_full_text --only problem,grounding,cost
python -m evals.harness diff baseline ablation_full_text --what problem -o diff_problem.md
```

`--only` names the sections to (re)compute: `match` (gold matching, code tier then
judge tier), `precision` (the per-item judge), `problem`, `solution`, `risks`,
`grounding`, `cost`. The other sections are copied from the run's existing score file
(or computed code-only when there is none), and the run's judge log is merged: the
replaced judge's old calls are dropped and the new ones appended. The *judge $* column
therefore always means the cost of the calls behind the verdicts in the score file, not
the spend of the last invocation; *judge failures* is summed over passes. `--only`
with `--force` ignores the existing file instead (the other sections reset to
code-only). `diff` reads two labels' `summary.json` and prints per-RFP mean ± sd (sd
only when a label has several runs) with the delta, `b` minus `a`; `--what` picks a
column set (`problem`, `requirements`, `solution`) and `--columns` any `Row` field,
with `unsupported.problem` or `rubric.specificity` for the dict columns.

## How to read the tables

**Requirements.**

- *recall*: share of gold requirements matched by at least one extracted requirement.
  Matching is code first (quote containment either way after `normalise`, or the
  extracted statement containing the gold quote, or word overlap of the quotes of at
  least 0.5), then the judge for the gold items code could not pair, shown only
  extracted items cited on the gold item's page plus or minus one. *by judge* counts the
  judge-tier matches.
- *recall (code only)*: the code tier alone, a lower bound. The judge tier accepts some
  candidates that omit the gold item's key value (a date, a named standard; F14), so
  true recall lies between the two columns.
- *recall (reachable)*: the same over gold items whose quote is in the parsed text.
  Federal Way's eight page-5 items (an image-only table) are unreachable without a VLM
  (ST2); they stay in plain recall so the parsing gap shows.
- *precision*: share of extracted items the judge finds both supported by their cited
  chunk and a real requirement (an obligation, constraint, deadline, limit or
  deliverable). Every extracted quote is already verified against its chunk by code
  (S5), so precision sits near the ceiling by construction; it catches invented values
  and narrative mistaken for obligations.
- *in scope*: share the judge finds core per the gold scope rule (D23). Out-of-scope
  items are surplus, not errors (D31); this is the number S13 would move if it tightened
  extraction.
- *type acc*, *strictness acc*: gold label versus the best-matched extracted item.

**Problem statement and grounding.**

- *checklist*: gold facts the judge finds stated with their concrete detail, plus the
  ones stated without it (*partial*), out of 12. Federal Way's GC12 (page-5 systems) is
  unreachable for the same reason as above.
- *claims p/s/r*: grounded items in the problem statement, solution (component claims
  plus assumptions) and risks.
- *unsupported p/s/r*: items the grounding judge rates `partially` or `unsupported`
  against only the text they cite. Assumptions are judged on the facts they state about
  the RFP, not on the position they take. Risks are judged on the facts they rest on.
- *dangling IDs*: cited IDs that do not exist (code; always 0 because assembly is
  strict).
- *entity misses*: items with a number or capitalised name that does not occur in the
  cited text (code heuristic; it over-flags style capitals and a name cited to the
  wrong chunk is a real miss, so read it as a pointer, not a score).

**Solution and risks.**

- *cited cov*: in-scope mandatory requirements cited by some component (what S7's loop
  optimises). *judged cov*: the same, counting a citation only when the judge finds the
  component's description actually meets the requirement.
- *calendar*: components the judge finds exist only for proposal-process dates (S7's
  open issue).
- *spec/feas/cons*: rubric, 1 to 5: specificity, feasibility, consistency with the
  stated constraints.
- *sev agree*, *lik agree*: share of risks where the judge, rating from the description
  without seeing the pipeline's levels, lands on the same severity and likelihood.
- *findings code/judge*: of the findings code detected (conflict pairs, absent
  documents, flagged pages, uncovered requirements), how many a risk addresses: by code
  (cites both IDs, names the document, mentions the page) and by the judge.

**Consistency.** Mean ± sample sd (min–max) over each RFP's runs, plus the Jaccard
overlap of the matched gold requirements and of the covered checklist facts between
every pair of runs.

**Judge agreement.** The agent labelled a seeded sample of verdicts from run 1 of each
RFP, reading only the item and its evidence (the judge's answer is not in the sample
file). Up to half of each kind was drawn from the judge's negative verdicts, so the rate
is over a negative-enriched sample, not a uniform one.
