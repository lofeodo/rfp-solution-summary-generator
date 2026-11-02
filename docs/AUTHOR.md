# AUTHOR.md — notes for the author only

Not part of the public README: the demo script for the recording, the rehearsed live
changes for the follow-up interview, and the status of the submission. Everything here
assumes the repo checked out, the UI running (`python -m ui.backend` with a built
frontend, or the Docker image) and a key in `.env`.

## Status

Core is complete (S0 to S16, see `ROADMAP.md`). Deliverables: pipeline and CLI, browser
UI with live stage progress and source reveal, evaluation harness with committed results
(baseline, two ablations, one prompt fix), per-run observability, Docker image, the
living docs under `docs/`. Stretch goals (VLM transcription of image pages, fetching
referenced documents, a critic agent, a model-family benchmark, cloud deployment) are
listed at the end of `ROADMAP.md` and not started.

## Demo script (3 to 5 minutes)

Before recording: the UI up, `DEEPSEEK_API_KEY` in `.env`, and
`evals/results/baseline/summary.md` open in an editor. Times are cumulative.

1. **0:00 The problem and the shape of the answer.** Show the README's pipeline
   diagram. One sentence on the traceability rule: every factual claim cites a chunk
   ID, code checks the IDs, so "unsupported claim" is a number the evals count.
2. **0:30 Start a live run.** In the UI, upload `data/rfps/colfax.pdf` with the
   defaults and submit. The timeline shows the stages: parse, parse quality, split,
   then requirements and the problem statement side by side, then solution, risks,
   assemble. Point at the per-stage wall time, calls and cost as each finishes. The
   run takes 80 to 110 seconds; do not wait for it.
3. **1:00 Read a finished output.** Open the `missouri` sample from the runs list.
   Solution tab: the summary, the components, each with the requirement IDs it
   satisfies, and the coverage figure. Click one requirement chip: the slide-over shows
   the cited chunk with the verbatim quote highlighted and the PDF open at that page.
   That is the traceability rule made visible.
4. **1:45 Requirements and risks.** Requirements tab: filter to `mandatory`, then to
   type `technical`; show the strictness and the `R`-IDs. Risks tab: K01 is the top
   risk because code sorts by severity then likelihood; the findings block (uncovered
   mandatory requirements, absent referenced documents, unreadable pages) is computed
   by code and the model must address every item. Missouri's list leads with the IS
   approval gate on the named program and the EPG rules the RFP points at but does
   not contain.
5. **2:30 Observability.** Metrics tab of the same run: cost, input, cached and output
   tokens and retries for the run, wall time and cost per stage, and a per-node table
   sorted by cost. Then `runs/samples/missouri/run_log.json` in the editor for what the
   tab does not show: the prompt hashes, each retry's cause, the parse-quality
   escalations. The same trace goes to Langfuse when keys are set.
6. **3:15 Evaluation.** Switch to `evals/results/baseline/summary.md`: recall against
   hand-corrected gold with the code-matched share, judged precision, checklist
   coverage, grounding, judged coverage of mandatory requirements, consistency across
   three runs. Then one ablation diff
   (`evals/results/ablation_single_call/diff_requirements.md`): the single call is
   cheaper and matches recall, but truncates on the largest RFP and drops whole
   obligations, which is why per-chunk extraction stays the default (D39).
7. **4:00 Back to the live run.** The Colfax run has finished: show its risk list,
   which on every run so far leads with the absent Attachments F and G (a gap the
   parser recorded and the extractor reported), and its cost on the timeline. Close on
   `DECISIONS.md`: D40 explains what the evals did not justify building (a critic
   loop), which is the decision to defend first.

## Live-change rehearsal

The follow-up asks for a small change made live. Three rehearsed ones, each with the
exact edit points and the command that proves it worked.

**1. Swap the generator model.** No edit: `--model` or `RFP_MODEL`.

```bash
python -m rfp_agent run data/rfps/colfax.pdf --model anthropic:claude-haiku-5-5
```

What to point at: the run log records `model`; cost comes from the pricing table
`PRICING` in `src/rfp_agent/config.py`, so a model with no row there is recorded at
cost 0 with one warning in the log, and the fix is one dictionary entry. Anthropic
models are not sent a temperature (they reject non-default sampling), which
`src/rfp_agent/llm.py` handles per provider. Provider packages are the pinned
`langchain-deepseek` and `langchain-anthropic`; another provider needs its LangChain
package added to `requirements.txt`. Rehearsed once on Federal Way: 49 calls, $0.047,
0 retries, 147 s, every stage finished.

**2. Edit a prompt and rerun only its stage.** Edit a rule in `prompts/risk.md` (for
example, cap the list at eight risks), then rerun the risk stage on a sample's
upstream outputs instead of the whole pipeline:

```bash
python -m rfp_agent.agents -v risk data/rfps/colfax.pdf \
    --requirements runs/samples/colfax/requirements.json \
    --problem runs/samples/colfax/problem.json \
    --solution runs/samples/colfax/solution.json --out /tmp/colfax_risks.json
```

What to point at: the debug command prints the stage's calls, tokens, cost and
retries and writes only the JSON (one pipeline run later carries the new prompt hash
in its `run_log.json`); the validator in `src/rfp_agent/agents/risk.py` still rejects
fewer than three or more than fifteen risks inside the retry, so a prompt asking for
two would show a validation retry under `-v`; and the change needs a changelog line in
`PROMPTS.md`. Rehearsed once: "at most eight" returned ten risks for about a cent,
which is the point to make about prompt rules versus code checks (F12 in
`DECISIONS.md`): the count rule in the prompt is advice the model overshoots, the band
in the validator is the guarantee. For a judge prompt the equivalent is
`python -m evals.harness score --label baseline --only risks`.

**3. Add a requirement type.** Say `accessibility` as its own type instead of folding
it into `technical`. Edit points, in order:

- `src/rfp_agent/schemas.py`: add the member to `RequirementType` (the contract; the
  extractor's structured output and the assembler validate against it).
- `prompts/requirements_extract.md`: add it to the list of kinds and to the `type`
  enum line, with one sentence on when it applies.
- `src/rfp_agent/render/markdown.py`: add its heading to `TYPE_LABELS` (the
  requirements section is grouped by type in enum order).
- `ui/frontend/src/api/types.ts`: add it to the `type` union;
  `ui/frontend/src/lib/requirements.ts`: add its label so the filter and the source
  panel show it (`npm run typecheck` fails until both are done).
- Optional for the evals: `prompts/gold_requirements.md` and
  `prompts/judge_requirements.md` list the types too; leaving them alone only means
  the type-accuracy column counts the new type as a mismatch against gold.

The solution generator, the risk assessor and the UI backend need no change; they
carry the type through. Prove it with `pytest` (the schema tests and the fake-model
extractor tests) and `cd ui/frontend && npm run typecheck && npm test`; then one paid
run on a PDF with such a clause shows the new type in the Requirements filter.
