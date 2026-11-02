# USAGE.md — every way to run it

The README has the short path (open the UI). This file has the rest: local setup in
detail, the CLI and its flags, the UI in development mode, the backend API, Docker
details, the evaluation harness, and troubleshooting.

## Local setup

```bash
conda create -n rfp-solution-gen python=3.12 -y
conda activate rfp-solution-gen
pip install -r requirements.txt          # also installs the package in editable mode (-e .)
cp .env.example .env                     # then fill in DEEPSEEK_API_KEY (and ANTHROPIC_API_KEY for evals)
pytest                                   # unit tests; nothing here calls a paid API
pytest --update-golden                   # rewrite golden files after an intended render change
pytest -m llm                            # live smoke tests against the real APIs (paid)
```

**Where the key goes:** `.env` at the repository root, which is gitignored. Everything
(CLI, UI, evals, Docker via `--env-file .env`) reads it from there; `.env.example`
lists every variable. The pipeline needs `DEEPSEEK_API_KEY` (or the key of whichever
provider `RFP_MODEL` names); the eval judge and the gold-label scripts need
`ANTHROPIC_API_KEY`. Without any key the unit tests, the committed samples and the UI's
sample browsing still work.

## CLI

```bash
python -m rfp_agent run inputs/rfp_brief.pdf
```

runs the graph: parse, judge the flagged pages, split, then requirements extraction and
the problem statement in parallel, then the solution, the risks, and the assembled
summary. The CLI prints one line per stage as it starts and finishes (wall time, LLM
calls, cost), then a per-stage table, a per-node table and the run totals.

| Flag | Effect |
|---|---|
| `--full-text-problem` | ablation: problem statement from one full-text call (`RFP_FULL_TEXT_PROBLEM`) |
| `--single-call-extraction` | ablation: one extraction call over the whole document (`RFP_SINGLE_CALL_EXTRACTION`) |
| `--max-iterations N` | solution rounds for this run (`RFP_SOLUTION_MAX_ITERATIONS`) |
| `--model provider:id` | generator for this run (`RFP_MODEL`) |
| `--runs-dir DIR`, `--run-id ID` | where the run directory goes (default `runs/<timestamp-hex>/`) |
| `-v` | log every failed structured-output attempt and its feedback |

Outputs go to `runs/<run_id>/`: `summary.json` (the source of truth), `summary.md`
(rendered from the JSON by code), `run_log.json` (per-call tokens, latency and cost,
per-stage wall time) and every intermediate (`parsed.json`, `quality.json`,
`split.json`, `requirements.json` and its report, `problem.json`, `solution.json`,
`risks.json`), each written as its stage finishes so a failed run keeps what it had.
Committed samples for the four RFPs live under `runs/samples/<rfp>/`.

Exit codes: 0 on success, 1 when a stage fails (the run log and the intermediates
written so far are kept, and the failing stage is named), 2 when the provider key is
missing. The graph is importable too: `rfp_agent.graph.run_pipeline(pdf, on_event=...)`
calls back with a `StageEvent` (`started`, `finished`, `failed`, wall time, the stage's
calls and cost) from each node, which is what the UI backend streams. Per-agent debug
commands with JSON reuse of upstream outputs live in `python -m rfp_agent.agents`
(see `PIPELINE.md` for one per stage).

## UI

Upload an RFP and watch each stage run live, with per-stage time, calls, tokens and
cost. Then read the proposed solution, the requirements (filterable by type and
strictness), the risks (sorted by severity), the problem statement, the parse and chunk
views, and a metrics dashboard. Click any chunk, requirement, component or risk ID to
open its source: the cited chunk with the verbatim quote highlighted, and the PDF at
that page. The four samples need no API key.

```bash
# once: build the frontend (Node 20+)
cd ui/frontend && npm ci && npm run build && cd ../..
python -m ui.backend --port 8000          # UI and API on http://127.0.0.1:8000

# or, while editing the frontend: two terminals
python -m ui.backend --port 8000
cd ui/frontend && npm run dev             # http://localhost:5173, proxies /api
```

Frontend checks: `npm run typecheck`, `npm test` (Vitest) and `npm run build` in
`ui/frontend`, also run in CI.

### Backend API

`python -m ui.backend --port 8000` serves a FastAPI app over the same pipeline. It
uploads a PDF, runs it on one worker thread (later uploads wait as `queued`), and
streams every stage event over SSE. It also serves each intermediate output, the
rendered markdown, downloads, the source PDF and a chunk lookup for source reveal. The
four committed samples are listed as runs (`missouri`, `nyesd`, `colfax`,
`federal_way`), so the UI works without an API key. The full API contract is in
`ui/backend/README.md`, and OpenAPI docs are at `/docs`.

```bash
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

Gold labels:

```bash
python -m evals.gold.label check --all   # every gold quote is in the parsed text
python -m evals.gold.label diff --all    # draft vs final correction table
```

## Troubleshooting

- **`No module named rfp_agent`.** The package is installed in editable mode and points
  at wherever `pip install -r requirements.txt` was last run. Run `pip install -e .`
  from the repository root in the `rfp-solution-gen` env.
- **The UI opens but shows no frontend (only `/docs`).** `ui/frontend/dist` is missing:
  run `cd ui/frontend && npm ci && npm run build`, then restart the backend.
- **503 on upload.** No provider key in `.env` (or the key of the provider `RFP_MODEL`
  names). The four samples still browse without one.
- **Docker on Windows.** Start Docker Desktop first; in PowerShell use `${PWD}` in the
  volume flag.
