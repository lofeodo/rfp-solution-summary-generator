# USAGE.md — every way to run it

The README has the short path (open the UI). This file has the rest: local setup in
detail, the CLI and its flags, the UI in development mode, the backend API, Docker
details, the evaluation harness, and troubleshooting.

## Local setup

```bash
conda create -n rfp-solution-gen python=3.12 -y
conda activate rfp-solution-gen
pip install -r requirements.txt          # also installs the package in editable mode (-e .)
# copy .env.example to .env (`copy` on Windows cmd, `cp` elsewhere), then fill in
# DEEPSEEK_API_KEY (and ANTHROPIC_API_KEY for evals)
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

reads the RFP and stops at the checkpoint: parse, judge the flagged pages, split, then
requirements extraction and the problem statement in parallel. The CLI prints one line
per stage as it starts and finishes (wall time, LLM calls, cost), then a per-stage
table, a per-node table, the run totals, and the command that continues the run.
Review `requirements.json` (and `problem.json`) in the run directory, write the pursuit
brief, then

```bash
python -m rfp_agent checkpoint <run_id> --reviewer "Dana" --brief brief.md \
    --reject R017 --strictness R042=desired --type R058=technical
```

confirms the requirements and drafts the rest on the same run: the solution, the
risks and the assembled summary. `--reject` drops a requirement (and every reference
to it), `--strictness` and `--type` change one requirement each; all three repeat.
The brief is a text or markdown file; each paragraph becomes a chunk `H1`, `H2`...
that the solution and the risks cite like an RFP chunk, so the summary shows which
claims rest on the team's input. The reviewer's name, the decisions, the brief and the
time the run waited are recorded in `checkpoint.json` and rendered as "Review history"
in `summary.md`; the extractor's `requirements.json` is kept untouched next to
`requirements_confirmed.json`. See [DECISIONS.md](DECISIONS.md) D42 to D44 for why
the checkpoint sits where it does.

```bash
python -m rfp_agent run inputs/rfp_brief.pdf --unattended
```

does everything in one go with no checkpoint and no brief: the behaviour before ST12,
and what the eval harness and the committed samples use.

| Flag | Command | Effect |
|---|---|---|
| `--unattended` | run | no checkpoint: draft right after the read stages |
| `--full-text-problem` | run | ablation: problem statement from one full-text call (`RFP_FULL_TEXT_PROBLEM`) |
| `--single-call-extraction` | run | ablation: one extraction call over the whole document (`RFP_SINGLE_CALL_EXTRACTION`) |
| `--reviewer NAME` | checkpoint | who confirms (required, recorded) |
| `--brief FILE` | checkpoint | the pursuit brief, one citable chunk per paragraph |
| `--reject ID`, `--strictness ID=LEVEL`, `--type ID=TYPE`, `--note TEXT` | checkpoint | the decisions; repeatable |
| `--max-iterations N` | both | solution rounds for this run (`RFP_SOLUTION_MAX_ITERATIONS`) |
| `--model provider:id` | both | generator for this run (`RFP_MODEL`) |
| `--runs-dir DIR`, `--run-id ID` | both | where the run directory is (default `runs/<timestamp-hex>/`) |
| `-v` | both | log every failed structured-output attempt and its feedback |

Outputs go to `runs/<run_id>/`: `summary.json` (the source of truth), `summary.md`
(rendered from the JSON by code), `run_log.json` (per-call tokens, latency and cost,
per-stage wall time, including how long the run waited at the checkpoint) and every
intermediate (`parsed.json`, `quality.json`, `split.json`, `requirements.json` and its
report, `problem.json`, `checkpoint.json`, `requirements_confirmed.json`,
`solution.json`, `risks.json`), each written as its stage finishes so a failed or
paused run keeps what it had. Committed samples for the four RFPs live under
`runs/samples/<rfp>/`.

Exit codes: 0 on success or on a pause at the checkpoint, 1 when a stage fails (the
run log and the intermediates written so far are kept, and the failing stage is
named), 2 when the provider key is missing, the checkpoint arguments are malformed, a
decision names an unknown requirement, or the run is not waiting. The graph is
importable too: `rfp_agent.graph.run_pipeline(pdf, pause_at_checkpoint=True,
on_event=...)` and `resume_pipeline(run_dir, record, on_event=...)` call back with a
`StageEvent` (`started`, `finished`, `failed`, `waiting`, wall time, the stage's calls
and cost) from each node, which is what the UI backend streams. Per-agent debug
commands with JSON reuse of upstream outputs live in `python -m rfp_agent.agents`
(see `PIPELINE.md` for one per stage).

### Refine and sign off

Once a run is drafted, review it in prose:

```bash
python -m rfp_agent revise <run_id> solution --reviewer "Dana" \
    --instruction "Add a component for accessibility testing, citing the brief"
python -m rfp_agent history <run_id>
python -m rfp_agent regenerate <run_id> risk --reviewer "Dana"
python -m rfp_agent sign-off <run_id> --reviewer "Lee" --note "Red team done"
```

`revise` applies one instruction to one artefact (`requirements`, `problem`,
`solution` or `risks`). The model revises it under the producing stage's own checks:
every ID it cites must exist, a new requirement's quote must be verbatim in the chunk
it names, and a solution revision may not leave a mandatory requirement uncovered that
is covered now. The requirement list is revised as a patch (edit, add, remove by ID);
the other three are returned whole, with component and risk IDs kept stable. The CLI
prints the diff (`+` added, `-` removed, `~` changed), the version change, what went
stale and the cost. `requirements` and `problem` can also be revised while the run
waits at the checkpoint (merge, split or reword before confirming); the checkpoint's
decisions then apply on top of the revised list.

A change marks what depends on it stale: requirements or problem → solution and risks;
solution → risks. Nothing is regenerated automatically; `regenerate <run_id>
solution|risk` re-runs that one stage on the current inputs (it never cascades), or a
`revise` of the stale artefact clears it too. The summary is re-assembled after every
change, so `summary.md` always shows the current versions and a "Revisions" list.
`sign-off` is refused while anything is stale; afterwards the run is frozen and the
header names who signed off which versions.

Files added to the run directory: `<artefact>.vN.json` (a copy of every version, v1
taken before the first change), `current.json` (version and stale flag per artefact,
the sign-off) and `revisions.json` (append-only: reviewer, instruction, diff, versions,
calls, cost, status). A revision the model cannot make valid is recorded as `failed`
and changes nothing. Exit codes as above: 2 for a request the run cannot take (signed
off, still waiting, stale at sign-off, unknown artefact, missing key), 1 when the model
or a regenerated stage fails. See [DECISIONS.md](DECISIONS.md) D45 and D46.

| Flag | Command | Effect |
|---|---|---|
| `--reviewer NAME` | revise, regenerate, sign-off | who asks for it (required, recorded) |
| `--instruction TEXT`, `--instruction-file FILE` | revise | what to change, in plain words (exactly one) |
| `--note TEXT` | sign-off | recorded with the sign-off |
| `--max-iterations N` | regenerate | solution rounds for this regeneration |
| `--model provider:id` | revise, regenerate | generator for this call (`RFP_MODEL`) |
| `--runs-dir DIR` | all four | parent of the run directory (default `runs/`) |

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

The volume flag is the one shell-specific part: `$PWD` in bash, `${PWD}` in PowerShell,
`%cd%` in Windows cmd. The container runs as a non-root user and
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
