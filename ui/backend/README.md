# UI backend (S14, ST12c): API contract

FastAPI app over `rfp_agent.graph` and `rfp_agent.refine`. It uploads a PDF, runs the
pipeline to the checkpoint on one worker thread, takes the reviewer's checkpoint,
revisions, regenerations and sign-off, streams stage and state events over SSE, and
serves everything the run writes into `runs/<run_id>/`. `rfp_agent` itself has no web
dependencies.

```
python -m ui.backend [--host 127.0.0.1] [--port 8000] [--reload]
```

Interactive docs at `http://127.0.0.1:8000/docs` (OpenAPI). When `ui/frontend/dist`
exists, the same process serves the built frontend at `/`. Unknown non-API paths get
`index.html` so client-side routes work. CORS allows the Vite dev server at
`http://localhost:5173`.

## Runs

A run ID is either generated (`YYYYMMDD-HHMMSS-<6 hex>`, UTC) or the name of a sample
directory. An ID resolves to `runs/<id>` first, then `runs/samples/<id>`, so the four
committed samples are served as `missouri`, `nyesd`, `colfax` and `federal_way`. They
need no API key.

```
queued ──► running ──► awaiting_checkpoint ──► drafting ──► finished ◄──► refining
              │         (POST checkpoint)                     │   (revise, regenerate)
              │                                               └──► signed_off (POST sign-off)
              └──► finished            (unattended upload)
   failed: a pipeline stage failed (reading or drafting)
```

| State | Meaning | Rests? |
|---|---|---|
| `queued` | the upload waits for the worker | no |
| `running` | parse to requirements and problem | no |
| `awaiting_checkpoint` | paused for the reviewer (ST12a); `requirements` and `problem` can be revised | yes |
| `drafting` | solution, risks, assembly after a confirmed checkpoint | no |
| `finished` | drafted; open to revision, regeneration and sign-off | yes |
| `refining` | a revision or regeneration is queued or running | no |
| `signed_off` | frozen at its current versions | yes |
| `failed` | a stage failed before the first assembly | yes |

- **Uploads pause at the checkpoint** unless the form says `unattended=true`, which
  runs to the end as before ST12 (the samples and the eval harness are unattended).
- **One job at a time, across runs.** A new run, a drafting, a revision and a
  regeneration all go through one worker. A job's state is set when it is queued, so
  the run reads busy at once and refuses a second job (409) until it rests.
- **A failed revision or regeneration is not a failed run.** The artefact is unchanged,
  the failure is recorded in `revisions.json`, and the run goes back to the state it
  rested in with `error` set; the next job clears it. On disk, a run that has assembled
  once reads `finished` whatever failed after.
- **Outputs appear as stages finish.** A stage's files are on disk before its
  `finished` event is sent, so fetch an artifact after its event, not before.
- **A failed run keeps everything written before the failure,** plus `run_log.json`.
- **Restarts.** A run's state is read from its files, so a run paused at the
  checkpoint, refined or signed off reads the same after a restart and takes the same
  requests (the backend adopts it on the first one). A job in flight during a restart
  is lost: a run lost before its log exists is not listed and reads `failed` with an
  "interrupted" error; a lost drafting or revision leaves the files of the last state
  it reached. No cancel or delete.
- **Samples are read-only** (403 on every request that changes a run).

| Stage | Files written when it finishes | Artifact names |
|---|---|---|
| `parse` | `parsed.json` | `parsed` |
| `parse_quality` | `parsed.json` (judged flags), `quality.json` | `parsed`, `quality` |
| `split` | `split.json` | `split` |
| `requirements` ‖ `problem` | `requirements.json`, `requirements_report.json` ‖ `problem.json` | `requirements`, `requirements_report` ‖ `problem` |
| `solution` | `solution.json` | `solution` |
| `risk` | `risks.json` | `risks` |
| `checkpoint` (confirmed) | `checkpoint.json` (reviewer, decisions, brief, note), `requirements_confirmed.json` | `checkpoint`, `requirements_confirmed` |
| `assemble` | `summary.json`, `summary.md` | `summary` |
| a revision, regeneration or sign-off | the artefact's live file, `<stem>.vN.json` copies, `current.json` (versions, stale flags, sign-off), `revisions.json` (append-only), then `summary.json` and `summary.md` re-assembled | `current`, `revisions` |
| end of run, pause, every job | `run_log.json` | `run_log` |

The upload itself is kept as `source.pdf` beside `upload.json`, which holds the
original file name and the options.

## Endpoints (prefix `/api`)

| Method and path | Request | Response | Errors |
|---|---|---|---|
| `GET /health` | | `{status, model, runs_dir}` | |
| `POST /runs` | multipart: `file` (PDF, required); optional `model` (`provider:model`), `full_text_problem`, `single_call_extraction` (`true`/`false`), `max_iterations` (1 to 10) | 202 `{run_id, status}` | 400 not a PDF, empty, or unknown model; 413 over 50 MB; 422 bad field; 503 provider key missing (the message names the variable) |
| `GET /runs` | | `RunListItem[]`: own runs newest first, then samples by name | |
| `GET /runs/{id}` | | `RunStatus` | 404 |
| `GET /runs/{id}/events` | | SSE stream, see below | 404 |
| `GET /runs/{id}/artifacts/{name}` | `name` from the table above | the JSON file | 404 unknown name or not written yet |
| `GET /runs/{id}/summary.md` | | `text/markdown` | 404 before `assemble` |
| `GET /runs/{id}/download/{file}` | `summary.json` or `summary.md` | attachment `<id>-<file>` | 404 |
| `GET /runs/{id}/source.pdf` | | `application/pdf` (samples: the PDF in `data/rfps/` named by the run log) | 404 |
| `GET /runs/{id}/chunks` | | `Chunk[]` (`id, section_id, section_path, page_start, page_end, text`) | 404 before `split` |
| `GET /runs/{id}/chunks/{chunk_id}` | `chunk_id` like `S3.2` | `Chunk` | 404 |
| `POST /runs/{id}/checkpoint` | JSON `{reviewer, decisions?: RequirementDecision[], brief?, note?, model?, max_iterations?}` | 202 `{run_id, status: "drafting", revision_id: null}` | 400 a decision names an unknown or repeated ID, or rejects and edits one; 403 sample; 404; 409 not `awaiting_checkpoint` or busy; 422 bad body; 503 key missing |
| `POST /runs/{id}/revise` | JSON `{reviewer, artefact: requirements\|problem\|solution\|risks, instruction, model?}` | 202 `{run_id, status: "refining", revision_id: "V03"}` | 403; 404; 409 the run does not take it now (see `review.allowed`); 422; 503 |
| `POST /runs/{id}/regenerate` | JSON `{reviewer, stage: solution\|risk, model?, max_iterations?}` | 202 as above | 403; 404; 409; 422; 503 |
| `POST /runs/{id}/sign-off` | JSON `{reviewer, note?}` | 200 `RunStatus` (`signed_off`) | 403; 404; 409 not `finished`, busy, or stale artefacts (named) |
| `GET /runs/{id}/revisions` | | `RevisionLog` `{revisions: RevisionRecord[]}` (empty when none) | 404 |
| `GET /runs/{id}/versions/{artefact}/{n}` | `artefact` as above, `n` from 1 | the version's JSON (the live file for the current version of an unrevised artefact) | 404 |

`RequirementDecision`: `{requirement_id, action: accept|reject, strictness?, type?,
note?}`. The brief is free text; each paragraph becomes a citable chunk `H1, H2...`
(headings attach to the paragraph after them). A revision's ID is the one it will have
in `revisions.json`; follow the job on the SSE stream, then read `GET /revisions`.

`RunListItem`: `run_id, status, sample, source_name, started_at, finished_at, cost_usd,
latency_s` (whole-run wall time, once ended), `stages_done`.

`RunStatus`: `run_id, status, sample, source_name, model, started_at, finished_at,
error, stages` (latest `StageEvent` per stage in pipeline order), `totals`
(`RunTotals`), `nodes` (every LLM call's `NodeMetrics`, empty until the run log
exists), `langfuse_trace_url` (null without Langfuse keys), `artifacts` (names on disk),
`review`.

`review` (`ReviewState`): `checkpoint` (the `CheckpointRecord`, or null), `versions`
(`current.json`: per artefact `{version, stale, stale_because, updated_at}`, and
`signed_off`), `stale` (artefact names), `sign_off`, `revisions` (record count), and
`allowed` `{checkpoint, revise: [artefact], regenerate: [stage], sign_off}`: what the run
takes now, computed by the backend; a frontend shows exactly these actions. While a job
is in flight `allowed` is empty, `nodes` is empty and `totals` adds the job's finished
stages to what the run had spent before it.

**Source reveal.** Requirements, claims and risks carry `chunk_ids`, and requirements
also carry a verbatim `quote`. To show a source, fetch `chunks/{chunk_id}` and
highlight the quote in its text. `summary.json` also holds `chunks` (ID, section
title, pages) for citation labels without the text.

## SSE stream

`GET /runs/{id}/events` sends every event from the start of the run, then live ones,
then `done` once the run rests (`awaiting_checkpoint`, `finished`, `signed_off` or
`failed`), and closes. After a checkpoint, revision or regeneration, subscribe again:
the new stream replays the earlier events and follows the new job. A client that connects mid-run misses nothing and gets
nothing twice. A comment line `: keepalive` comes every 15 s while no event arrives.
For a run that ended before this process started, the stream replays the stage records
from `run_log.json`: one `finished` or `failed` event per stage, no `started` events.

```
event: stage
data: {"stage":"requirements","status":"finished","started_at":"2026-10-30T20:29:39.171086Z","latency_s":23.254791000013938,"calls":23,"totals":{"input_tokens":70138,"output_tokens":12700,"cached_input_tokens":58493,"cost_usd":0.019084458,"latency_s":67.52535169996554,"retries":2},"error":null}

event: state
data: {"status":"drafting","error":null,"at":"2026-11-02T21:04:11.120Z"}

event: done
data: {"status":"finished","error":null}
```

`state` events mark every change of the run's state, in order with the stage events.
A run adopted after a restart starts its stream with the replayed stage records and one
`state` event for where it rested.

A stage event's `status` is `started`, `finished`, `failed`, or `waiting` (the
`checkpoint` stage of a paused run). Besides the pipeline stages, `checkpoint` (finished
when confirmed, `latency_s` is the time it waited) and `revise` appear. On `finished`, `calls` and `totals`
cover the stage's LLM calls. `totals.latency_s` sums the call latencies, which exceeds
the stage's wall time `latency_s` when calls run concurrently. `requirements` and
`problem` run in parallel, so their events interleave; key the display by `stage`.

## Tests

`tests/test_ui_backend.py` covers the API with the five LLM stages stubbed and the
revise agents on a scripted model. It holds a run at a gate to test queueing, a live
subscription and a job refused while another waits its turn, and builds a second app on
the same directories to test restarts.
