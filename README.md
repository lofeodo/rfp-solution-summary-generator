# RFP solution-summary generator

An agentic LangGraph pipeline that reads an RFP (request for proposal) PDF and produces a
structured solution summary: the requirements it imposes, the problem it is really
asking to solve, a proposed approach, and the risks. Every factual claim in the output
cites the chunk of the RFP it came from, so the summary can be checked against the
source. The repo includes an evaluation harness and per-run observability (tokens,
latency, cost).

**Status:** core complete. The pipeline and its CLI, a browser UI with live stage
progress and source reveal, an evaluation harness with committed results (a baseline,
two ablations and one prompt fix), per-run observability, a Docker image and the
living docs under `docs/` are all in. Sample outputs for the four public RFPs are
under `runs/samples/` and need no API key to browse. Stretch goals (VLM transcription
of image pages, fetching referenced documents, a critic agent, a model-family
benchmark, cloud deployment) are listed at the end of `docs/ROADMAP.md` and are not
started.

**Contents:** [Pipeline](#pipeline) · [Quickstart](#quickstart) ·
[Running the pipeline](#running-the-pipeline) · [UI](#ui) · [Docker](#docker) ·
[Parsing](#parsing) · [Splitting](#splitting) ·
[Requirements extraction](#requirements-extraction) ·
[Problem statement](#problem-statement) · [Solution generator](#solution-generator) ·
[Risk assessor](#risk-assessor) · [Configuration](#configuration) ·
[Observability](#observability) · [Inputs](#inputs) · [Evaluation](#evaluation) ·
[Demo script](#demo-script-3-to-5-minutes) ·
[Live-change rehearsal](#live-change-rehearsal) ·
[Repository layout](#repository-layout) · [Documentation](#documentation)

## Pipeline

```mermaid
flowchart LR
    PDF[RFP PDF] --> P0[0. Parse PDF to markdown<br/>+ flag pages, links, images, referenced docs]
    P0 --> P1[1. Split: sections and citable chunks<br/>stable IDs S3.2]
    P1 --> P2[2. Requirements extractor<br/>per chunk, validated, deduped]
    P1 --> P3[3. Problem statement<br/>hierarchical summaries]
    P2 --> P4[4. Solution generator]
    P3 --> P4
    P4 --> P5[5. Risk assessor]
    P2 --> P5
    P3 --> P5
    P5 --> P6[6. Assemble JSON, render markdown]
```

Generator: DeepSeek by default. Eval judge: Claude. Provider and model are one setting
(`RFP_MODEL=<provider>:<model_id>`), so any LangChain-supported model can be swapped in.
JSON is the source of truth; markdown is rendered from it by code, never by an LLM.

## Quickstart

```bash
conda create -n rfp-solution-gen python=3.12 -y
conda activate rfp-solution-gen
pip install -r requirements.txt          # also installs the package in editable mode
cp .env.example .env                     # then fill in DEEPSEEK_API_KEY (and ANTHROPIC_API_KEY for evals)
pytest                                   # unit tests; nothing here calls a paid API
pytest --update-golden                   # rewrite golden files after an intended render change
```

**Where the key goes:** `.env` at the repository root, which is gitignored. Everything
(CLI, UI, evals, Docker via `--env-file .env`) reads it from there; `.env.example`
lists every variable. The pipeline needs `DEEPSEEK_API_KEY` (or the key of whichever
provider `RFP_MODEL` names); the eval judge and the gold-label scripts need
`ANTHROPIC_API_KEY`. Without any key the unit tests, the committed samples and the UI's
sample browsing still work. No Docker is needed for a local run; see
[Docker](#docker) for the containerised one.

Run the pipeline on the default brief:

```bash
python -m rfp_agent run inputs/rfp_brief.pdf
```

Outputs go to `runs/<run_id>/`: `summary.json` (the source of truth), `summary.md`
(rendered from the JSON by code), `run_log.json` (per-call tokens, latency and cost,
per-stage wall time) and every intermediate (`parsed.json`, `quality.json`,
`split.json`, `requirements.json` and its report, `problem.json`, `solution.json`,
`risks.json`), each written as its stage finishes so a failed run keeps what it had.
Citations in the markdown read `(Section title, p. 4 [S3.2])`; the bracketed chunk ID
is the key into the JSON. Committed samples for the four RFPs live under
`runs/samples/<rfp>/`. Langfuse tracing turns on automatically when `LANGFUSE_*` keys
are set and is a no-op otherwise.

## Running the pipeline

`python -m rfp_agent run <pdf>` runs the graph below: parse, judge the flagged pages,
split, then requirements extraction and the problem statement in parallel, then the
solution, the risks, and the assembled summary. The CLI prints one line per stage as it
starts and finishes (wall time, LLM calls, cost), then a per-stage table, a per-node
table and the run totals.

| Flag | Effect |
|---|---|
| `--full-text-problem` | ablation: problem statement from one full-text call (`RFP_FULL_TEXT_PROBLEM`) |
| `--single-call-extraction` | ablation: one extraction call over the whole document (`RFP_SINGLE_CALL_EXTRACTION`) |
| `--max-iterations N` | solution rounds for this run (`RFP_SOLUTION_MAX_ITERATIONS`) |
| `--model provider:id` | generator for this run (`RFP_MODEL`) |
| `--runs-dir DIR`, `--run-id ID` | where the run directory goes (default `runs/<timestamp-hex>/`) |
| `-v` | log every failed structured-output attempt and its feedback |

Exit codes: 0 on success, 1 when a stage fails (the run log and the intermediates
written so far are kept, and the failing stage is named), 2 when the provider key is
missing. The graph is importable too: `rfp_agent.graph.run_pipeline(pdf, on_event=...)`
calls back with a `StageEvent` (`started`, `finished`, `failed`, wall time, the stage's
calls and cost) from each node, which is what the UI backend streams. Per-agent debug
commands with JSON reuse of upstream outputs live in `python -m rfp_agent.agents`.

## UI

A browser UI over the pipeline. Upload an RFP and watch each stage run live, with
per-stage time, calls, tokens and cost. Then read the proposed solution, the
requirements (filterable by type and strictness), the risks (sorted by severity),
the problem statement, the parse and chunk views, and a metrics dashboard. Click
any chunk, requirement, component or risk ID to open its source: the cited chunk
with the verbatim quote highlighted, and the PDF at that page. The four samples
need no API key.

```
# once: build the frontend (Node 20+)
cd ui/frontend && npm ci && npm run build && cd ../..
python -m ui.backend --port 8000          # UI and API on http://127.0.0.1:8000

# or, while editing the frontend: two terminals
python -m ui.backend --port 8000
cd ui/frontend && npm run dev             # http://localhost:5173, proxies /api
```

Frontend checks: `npm run typecheck`, `npm test` (Vitest) and `npm run build` in
`ui/frontend`, also run in CI.

### UI backend

`python -m ui.backend --port 8000` serves a FastAPI app over the same pipeline. It
uploads a PDF, runs it on one worker thread (later uploads wait as `queued`), and
streams every stage event over SSE. It also serves each intermediate output, the
rendered markdown, downloads, the source PDF and a chunk lookup for source reveal. The
four committed samples are listed as runs (`missouri`, `nyesd`, `colfax`,
`federal_way`), so the UI works without an API key. The full API contract is in
`ui/backend/README.md`, and OpenAPI docs are at `/docs`.

```
python -m ui.backend --port 8000
curl -F file=@data/rfps/federal_way.pdf http://127.0.0.1:8000/api/runs   # -> {"run_id": ...}
curl -N http://127.0.0.1:8000/api/runs/<run_id>/events                    # live stage events
curl http://127.0.0.1:8000/api/runs/missouri/chunks/S1.1                  # a cited chunk
```

The upload form takes the CLI's options as fields: `model`, `full_text_problem`,
`single_call_extraction` and `max_iterations`. A missing provider key returns 503
before anything is written. When `ui/frontend/dist` exists, the same process serves the
built frontend. `--reload` is for development only, because a reload loses a run that
is in flight.

## Docker

One image serves the UI and runs the CLI; nothing but Docker is needed on the host.
The build has two stages: Node 22 builds the frontend, then `python:3.12-slim`
installs the pinned requirements and copies the prompts, the public RFPs, the committed
samples, the evals and the tests. The image never contains a key: `.env` is in
`.dockerignore`, and the keys are passed at run time with `--env-file`.

```bash
docker build -t rfp-agent .

# UI and API on http://127.0.0.1:8000 (the four samples work with no key at all)
docker run --rm -p 8000:8000 --env-file .env -v "$PWD/runs:/app/runs" rfp-agent

# CLI: the run directory lands in ./runs on the host through the mounted volume
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" rfp-agent \
    python -m rfp_agent run inputs/rfp_brief.pdf

# any other command works the same way
docker run --rm rfp-agent pytest -q
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" rfp-agent \
    python -m rfp_agent run data/rfps/colfax.pdf --single-call-extraction
```

On PowerShell replace `$PWD` with `${PWD}`. The container runs as a non-root user and
writes only under `/app/runs`; mount an empty or existing `runs/` directory there.
Settings are read from the environment, so any `RFP_*` variable in `.env` (or passed
with `-e`) applies inside the container exactly as it does locally.

## Parsing

`rfp_agent.parsing.parse_pdf(path)` turns a PDF into a `ParsedDocument`: markdown per
page (tables kept as markdown tables, running headers and footers removed, quotes and
spaces normalised), the PDF outline, tables, images with captions, every http(s) link and
every Attachment/Appendix/Exhibit/Schedule/Addendum reference with its section and
whether its content is in the PDF, and page flags (low word count, large image, broken
table, fragmented lines) for the parse-quality pass. No LLM is involved. To inspect it:

```bash
python -m rfp_agent.parsing data/rfps/colfax.pdf --out colfax.json
```

### Parse-quality pass

The flags are suspicions. `rfp_agent.parsing.quality.run_quality_pass(parsed)` sends each
flagged page to the generator model once (prompt `prompts/parse_quality.md`), which says
whether the text is usable and whether content is missing (for example a table that is
only an image). Code then clears false alarms, keeps confirmed flags, and records an
escalation per page in the run log, noting whether a heuristic (`code`) or the judge
(`model`) found the problem. Confirmed-bad pages go to a VLM hook that, in core, only
records "would escalate to VLM". A judge failure keeps the page's flags. On the four RFPs
it clears 9 of 12 flagged pages and escalates Missouri p19 and p20 and Federal Way p5,
for about half a cent in total. To see the verdicts (paid, needs `DEEPSEEK_API_KEY`):

```bash
python -m rfp_agent.parsing data/rfps/federal_way.pdf --judge --out federal_way.json
```

## Splitting

`rfp_agent.splitting.split_document(parsed)` turns a `ParsedDocument` into a
`SplitDocument`: one section per heading of the RFP, each cut into citable chunks.
Headings come from the PDF outline when there is one (located in the page text, including
bold labels that open a paragraph such as `**(A) Services:** ...`), from markdown
headings otherwise, plus bold lines numbered like an existing heading ("SECTION 4" after
"SECTION 3"). Chunks hold at most 300 words, cut at paragraphs (sentences only inside an
over-long paragraph), never inside a table, and each chunk repeats the last sentence of
the previous one. IDs are stable: `S7` is the seventh section in document order and
`S7.2` its second chunk, so the same PDF always gives the same citations. Each section is
tagged `requirement_bearing` or `narrative` by obligation cues ("shall", "must",
"Describe ..."). No LLM is involved. To inspect it:

```bash
python -m rfp_agent.splitting data/rfps/federal_way.pdf --out federal_way_split.json
```

## Requirements extraction

`rfp_agent.agents.requirements.extract_requirements(split, title=...)` turns a
`SplitDocument` into a `RequirementsOutput` (requirements, ambiguities, gaps) plus a
`RequirementsReport`. One structured LLM call per chunk (`RFP_LLM_CONCURRENCY` in
parallel, default 4) returns core requirements with type, strictness and a verbatim
quote; code looks every quote up in the chunk, gives the model one turn to fix the ones
it cannot find, and keeps the rest flagged `quote_verified=false`. Code assigns the
`R001` IDs, cites the chunk, folds exact duplicates (the one-sentence chunk overlap
produces them), then one grouping call names near-duplicates and contradictions; code
checks the answer (every ID exists, none in two groups), feeds violations back once,
sanitises what remains and merges: the representative keeps its text and quote, chunk
IDs are unioned, the stricter strictness wins, absorbed IDs sit in `merged_from`.
Contradictions are flagged on both items (`conflicts_with`) and listed as ambiguities,
never merged. Gaps are documents the RFP points at but does not contain (Colfax
Attachments F and G). The scope is the gold scope: core requirements, no generic
contract boilerplate. `RFP_SINGLE_CALL_EXTRACTION=true` (or `--single-call`) runs one
call over the whole document instead, the eval baseline. To inspect it (paid, a few
cents per RFP):

```bash
python -m rfp_agent.agents requirements data/rfps/colfax.pdf --out colfax_requirements.json
## Problem statement

`rfp_agent.agents.problem.build_problem_statement(split, title=...)` writes the part of
the summary that says what the client is asking for and why: four lists of one-sentence
claims (client situation, goal, success criteria, constraints), each citing the chunk IDs
that support it and labelled `fact` or `inference`. Two paths:

- **Hierarchical** (default): one call per chunk (prompt `prompts/problem_chunk.md`,
  `RFP_LLM_CONCURRENCY` calls at a time) returns whether the chunk is relevant and a
  compact factual summary; code attaches the chunk ID. One synthesis call
  (`prompts/problem_synthesis.md`) then sees only the relevant summaries, labelled with
  their IDs. The synthesis output schema rejects an empty list or a citation that was not
  in the evidence, so the validation error goes back to the model and the call is
  retried; after the retry budget the node fails rather than keep an unverifiable claim.
- **Full text** (`RFP_FULL_TEXT_PROBLEM=true`, the S13 ablation): the same synthesis
  prompt over the full text of every chunk with the same labels.

On the four RFPs the hierarchical path costs $0.01 to $0.04 and 30 to 60 s on DeepSeek
Flash, the full-text call $0.004 to $0.008 and about 10 s; both mention every fact of the
gold checklists that the parsed text contains. To run one agent on its own (paid):

```bash
python -m rfp_agent.agents problem data/rfps/colfax.pdf --out colfax_problem.json
python -m rfp_agent.agents -v problem data/rfps/colfax.pdf --full-text   # -v logs retries
```

## Solution generator

`rfp_agent.agents.solution.build_solution(requirements, problem_statement, title=...)`
writes the proposed approach: a short summary, four to ten components that each cite
the requirement IDs they satisfy, and the assumptions the design takes where the RFP is
ambiguous or incomplete. The model sees the problem statement, the requirements (one
line each), the ambiguities and the gaps, never the RFP text (prompt
`prompts/solution.md`), so it can only cite requirement IDs from the list and chunk IDs
labelled in those inputs; the output schema rejects anything else inside the retry.

Coverage is computed by code, not reported by the model: the share of mandatory
requirements (type `submission` excluded) cited by at least one component. A small
LangGraph loop generates, checks coverage, and when mandatory requirements are left
uncovered feeds their IDs and text back for a revision in the same conversation, up to
`RFP_SOLUTION_MAX_ITERATIONS` rounds (default 3). The draft with the fewest uncovered
requirements is kept and the rest are listed in `coverage.uncovered_requirement_ids`
for the risk assessor. Component IDs `C01…` are assigned by code.

On the four RFPs: 9 to 10 components, full mandatory coverage after one or two rounds,
$0.007 to $0.013 and 20 to 35 s per RFP on DeepSeek Flash. To run it on its own
(paid; without the JSON options it runs the extractor and the problem statement first):

```bash
python -m rfp_agent.agents solution data/rfps/colfax.pdf \
    --requirements colfax_requirements.json --problem colfax_problem.json --out colfax_solution.json
python -m rfp_agent.agents -v solution data/rfps/colfax.pdf --max-iterations 1   # no revision round
```

## Risk assessor

`rfp_agent.agents.risk.build_risks(requirements, problem_statement, solution,
title=..., referenced_documents=parsed.referenced_documents, flags=parsed.flags)`
writes the risks: six to twelve entries, each with a severity and a likelihood (`low`,
`medium`, `high`), a justification, the requirement and chunk IDs it relates to, a
`source` (`rfp` for what the RFP itself carries, `solution` for what the proposed
approach creates) and a mitigation. The model sees the solution, the problem statement,
the requirements, the ambiguities and the gaps, never the RFP text (prompt
`prompts/risk.md`).

Before the call, code computes a findings block the model must work from: the mandatory
requirements the solution left uncovered, the requirement conflicts S5 flagged, the
referenced documents the parser marked absent, the parse flags that survived the
quality pass, and how many budget requirements exist. The output schema rejects, inside
the retry, fewer than 3 or more than 15 risks, any unknown ID, and a draft in which an
uncovered mandatory requirement is cited by no risk. Code then sorts by severity and
likelihood and numbers the risks `K01…`, so K01 is the top risk in both the JSON and the
rendered table.

Scales: severity is the impact if the risk happens (`high`: the project fails, misses a
contractual date or overruns budget by more than a quarter; `medium`: rework or cost
that contingency absorbs; `low`: normal delivery); likelihood is the chance given the
RFP and the solution as written (`high`: expected unless someone acts; `medium`: turns
on facts the RFP does not settle; `low`: an unusual event).

On the four RFPs: 12 to 13 risks, one call, no validator retry, $0.007 to $0.011 and
about 20 s per RFP on DeepSeek Flash. To run it on its own (paid; it runs the
parse-quality pass first and, without the JSON options, S5, S6 and S7 too):

```bash
python -m rfp_agent.agents risk data/rfps/colfax.pdf --requirements colfax_requirements.json \
    --problem colfax_problem.json --solution colfax_solution.json --out colfax_risks.json
```

## Configuration

All settings live in `.env` (see `.env.example`); `RFP_*` variables override defaults.

| Variable | Default | Meaning |
|---|---|---|
| `RFP_MODEL` | `deepseek:deepseek-flash` | generator, `<provider>:<model_id>` |
| `RFP_JUDGE_MODEL` | `anthropic:claude-sonnet-5-5` | eval judge |
| `RFP_TEMPERATURE` | `0` | sent to every provider except Anthropic |
| `RFP_MAX_STRUCTURED_RETRIES` | `2` | retries after a schema validation failure |
| `RFP_MAX_OUTPUT_TOKENS` | provider default | output cap per call |
| `RFP_REQUEST_TIMEOUT_S` | `120` | per-request timeout |
| `RFP_LLM_TRANSPORT_RETRIES` | `2` | SDK retries on 429, 5xx and connection errors |
| `RFP_DEEPSEEK_THINKING` | `false` | DeepSeek thinking mode (structured output switches to JSON mode when on) |
| `RFP_LLM_CONCURRENCY` | `4` | parallel calls in per-chunk stages (requirement extraction, problem-statement summaries) |
| `RFP_FULL_TEXT_PROBLEM` | `false` | problem statement from one full-text call instead of per-chunk summaries (ablation) |
| `RFP_SINGLE_CALL_EXTRACTION` | `false` | requirements from one call over the whole document instead of per chunk plus dedupe (ablation) |
| `RFP_SOLUTION_MAX_ITERATIONS` | `3` | solution rounds: one generation plus revisions while mandatory requirements are uncovered; `1` disables revision |

## Observability

Every LLM call goes through `structured_call` in `src/rfp_agent/llm.py`, which records
one entry per call (node, model, input, output and cached tokens, cost from the pricing
table in `config.py`, latency, retries) into the run's log. The log also holds the model,
temperature and the SHA-256 of every prompt file used, plus one `stages` entry per
graph node (status, wall time, error text on failure), and is written to
`runs/<run_id>/run_log.json` even when a run fails. A stage's LLM calls are the nodes
whose name starts with the stage's prefix (`requirements_`, `problem_`, `solution_`,
`risk_`, `parse_quality`). Langfuse tracing is added as a
LangChain callback when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, and is
off otherwise.

Live smoke tests against the real APIs are skipped by default:

```bash
pytest -m llm      # needs DEEPSEEK_API_KEY and/or ANTHROPIC_API_KEY in .env
```

## Inputs

No RFP brief was provided with the assignment, so public US government RFPs stand in
(`data/rfps/`). The default input `inputs/rfp_brief.pdf` is Missouri DOT TR202504
("Using AI/ML to Write Legal Land Descriptions"). Three more RFPs form the eval set.
See `docs/ASSUMPTIONS.md`.

### Gold labels

`evals/gold/` holds reference labels for the four RFPs: core requirements and a
12-fact problem-statement checklist per RFP, drafted by Claude and corrected by hand
(19 to 26% of drafted requirements corrected). Format, workflow and the correction table
are in `evals/gold/README.md`.

```bash
python -m evals.gold.label check --all   # every gold quote is in the parsed text
python -m evals.gold.label diff --all    # draft vs final correction table
```

## Evaluation

`evals/harness/` scores pipeline runs against the gold labels with code checks first and
a Claude judge second (`RFP_JUDGE_MODEL`, needs `ANTHROPIC_API_KEY`). Per run it
measures:

- **Requirements:** recall against gold (code match, then the judge for the rest),
  precision and scope of every extracted item by the judge, and type and strictness
  accuracy.
- **Grounding:** every cited claim, assumption and risk is checked against only the text
  it cites. Code checks IDs, numbers and names; the judge rates each item supported,
  partially or unsupported.
- **Problem statement:** checklist coverage of the 12 gold facts.
- **Solution:** cited and judged coverage of mandatory requirements, plus a rubric for
  specificity, feasibility and consistency.
- **Risks:** severity and likelihood re-rated blind, and coverage of the code findings.
- **Cost and latency:** per stage from the run log, with each retry's cause.

Across runs it reports consistency, a pairwise A/B judge for ablations, and judge
agreement with a hand-labelled sample.

```bash
python -m evals.harness run --label baseline --all --runs 2 --reuse-samples  # paid, ~$0.60
python -m evals.harness score --label baseline            # judge, ~$5 for 12 runs
python -m evals.harness score --label baseline --no-judge # code metrics only, free
python -m evals.harness report --label baseline           # summary.md and summary.json
python -m evals.harness compare RUN_A RUN_B --what problem --rfp missouri   # pairwise
python -m evals.harness score --label baseline --only match   # re-run one judge, merged
python -m evals.harness run --label ablation_full_text --all --full-text-problem   # ablation
python -m evals.harness diff baseline ablation_full_text --what problem     # before/after
```

`--only` takes `match`, `precision`, `problem`, `solution`, `risks`, `grounding` and
`cost`; the other sections are kept from the existing score file, so a prompt change to
one judge costs one judge. `diff` prints per-RFP mean ± sd of two labels with the delta
(free); `run` takes the same `--full-text-problem` and `--single-call-extraction` flags
as the pipeline CLI.

Baseline (`evals/results/baseline/summary.md`): three runs per RFP, recall 80 to 100%,
with 61 to 94% matched by code alone. Federal Way's lower figure is its image-only page 5;
reachable recall is 93 to 96%. Precision is 95 to 99%, checklist coverage 67 to 92%,
and judged coverage of mandatory requirements 70 to 100% against 100% cited. The judge
agrees with 34 of 40 hand labels. How to read every column is in
`evals/results/README.md`.

## Demo script (3 to 5 minutes)

Before recording: `python -m ui.backend --port 8000` with a built frontend (or the
Docker image), `DEEPSEEK_API_KEY` in `.env`, and `evals/results/baseline/summary.md`
open in an editor. Times are cumulative.

1. **0:00 The problem and the shape of the answer.** Show this README's pipeline
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
   sorted by cost. Then `runs/samples/missouri/run_log.json` in the editor for what the tab
   does not show: the prompt hashes, each retry's cause, the parse-quality
   escalations. The same trace goes to Langfuse when keys are set.
6. **3:15 Evaluation.** Switch to `evals/results/baseline/summary.md`: recall against
   hand-corrected gold with the code-matched share, judged precision, checklist
   coverage, grounding, judged coverage of mandatory requirements, consistency across
   three runs. Then one ablation diff (`evals/results/ablation_single_call/diff_requirements.md`):
   the single call is cheaper and matches recall, but truncates on the largest RFP and
   drops whole obligations, which is why per-chunk extraction stays the default (D39).
7. **4:00 Back to the live run.** The Colfax run has finished: show its risk list,
   which on every run so far leads with the absent Attachments F and G (a gap the
   parser recorded and the extractor reported), and its cost on the timeline. Close on `docs/DECISIONS.md`: D40
   explains what the evals did not justify building (a critic loop), which is the
   decision to defend first.

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
package added to `requirements.txt`.

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
`docs/PROMPTS.md`. For a judge prompt the equivalent is
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

## Repository layout

```
src/rfp_agent/
  config.py        provider/model setting, paths, pricing table
  schemas.py       Pydantic v2 contract between every pipeline stage
  graph.py         the LangGraph pipeline: stage wrappers, events, run_pipeline (S10)
  cli.py           `python -m rfp_agent run <pdf>` (S10)
  parsing/         PDF to markdown, page flags, referenced documents (S2), quality pass (S4)
  splitting/       sections and citable chunks with stable IDs (S3)
  agents/          requirements extractor with dedupe (S5), problem (S6), solution
                   with its coverage loop (S7), risk assessor (S8); `python -m rfp_agent.agents` debug CLI
  textmatch.py     quote matching tolerant of markdown and typography (S5, gold labels)
  render/          JSON assembly and markdown rendering (S9)
prompts/           one markdown prompt per agent
tests/             pytest; `@pytest.mark.llm` tests are skipped by default
evals/gold/        gold labels and the labelling script (S11)
evals/harness/     eval harness: `python -m evals.harness` (S12)
evals/results/     committed eval results, one directory per label (S12, S13)
runs/samples/      committed end-to-end outputs for the four RFPs (S10)
ui/backend/        FastAPI app: uploads, run queue, SSE events, run outputs (S14)
ui/frontend/       Vite + React + TypeScript + Tailwind UI (S15)
docs/              ROADMAP, DECISIONS, ASSUMPTIONS, TIMELOG, PROMPTS
```

## Documentation

- `docs/ROADMAP.md`: the plan, step by step, with what was done in each.
- `docs/DECISIONS.md`: trade-offs and failure modes, with evidence.
- `docs/ASSUMPTIONS.md`: everything the assignment did not state.
- `docs/PROMPTS.md`: prompt design notes and changelog.
- `docs/TIMELOG.md`: hours per deliverable.
