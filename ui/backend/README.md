# UI backend (S14): API contract

FastAPI app over `rfp_agent.graph.run_pipeline`. It uploads a PDF, runs the pipeline on
one worker thread, streams stage events over SSE, and serves everything the run writes
into `runs/<run_id>/`. `rfp_agent` itself has no web dependencies.

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
queued ──► running ──► finished
                  └──► failed
```

- **One run at a time.** Uploads made while a run is in flight wait as `queued`.
- **Outputs appear as stages finish.** A stage's files are on disk before its
  `finished` event is sent, so fetch an artifact after its event, not before.
- **A failed run keeps everything written before the failure,** plus `run_log.json`.
- **No cancel or delete.** A reload or restart during a run loses that run. Its
  directory has no `run_log.json`, so it is not listed, and its status reads `failed`
  with an "interrupted" error.

| Stage | Files written when it finishes | Artifact names |
|---|---|---|
| `parse` | `parsed.json` | `parsed` |
| `parse_quality` | `parsed.json` (judged flags), `quality.json` | `parsed`, `quality` |
| `split` | `split.json` | `split` |
| `requirements` ‖ `problem` | `requirements.json`, `requirements_report.json` ‖ `problem.json` | `requirements`, `requirements_report` ‖ `problem` |
| `solution` | `solution.json` | `solution` |
| `risk` | `risks.json` | `risks` |
| `assemble` | `summary.json`, `summary.md` | `summary` |
| end of run | `run_log.json` | `run_log` |

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

`RunListItem`: `run_id, status, sample, source_name, started_at, finished_at, cost_usd,
latency_s` (whole-run wall time, once ended), `stages_done`.

`RunStatus`: `run_id, status, sample, source_name, model, started_at, finished_at,
error, stages` (latest `StageEvent` per stage in pipeline order), `totals`
(`RunTotals`), `nodes` (every LLM call's `NodeMetrics`, empty until the run log
exists), `langfuse_trace_url` (null without Langfuse keys), `artifacts` (names on disk).

**Source reveal.** Requirements, claims and risks carry `chunk_ids`, and requirements
also carry a verbatim `quote`. To show a source, fetch `chunks/{chunk_id}` and
highlight the quote in its text. `summary.json` also holds `chunks` (ID, section
title, pages) for citation labels without the text.

## SSE stream

`GET /runs/{id}/events` sends every event from the start of the run, then live ones,
then `done`, and closes. A client that connects mid-run misses nothing and gets
nothing twice. A comment line `: keepalive` comes every 15 s while no event arrives.
For a run that ended before this process started, the stream replays the stage records
from `run_log.json`: one `finished` or `failed` event per stage, no `started` events.

```
event: stage
data: {"stage":"requirements","status":"finished","started_at":"2026-10-30T20:29:39.171086Z","latency_s":23.254791000013938,"calls":23,"totals":{"input_tokens":70138,"output_tokens":12700,"cached_input_tokens":58493,"cost_usd":0.019084458,"latency_s":67.52535169996554,"retries":2},"error":null}

event: done
data: {"status":"finished","error":null}
```

`status` is `started`, `finished` or `failed`. On `finished`, `calls` and `totals`
cover the stage's LLM calls. `totals.latency_s` sums the call latencies, which exceeds
the stage's wall time `latency_s` when calls run concurrently. `requirements` and
`problem` run in parallel, so their events interleave; key the display by `stage`.

## Tests

`tests/test_ui_backend.py` covers the API with the five LLM stages stubbed. It holds a
run at a gate to test queueing and a live subscription.
