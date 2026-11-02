# ST12c. Backend

- **Status:** done
- **Summary:** The backend drives the whole human loop over HTTP: uploads pause at the checkpoint, the checkpoint, revisions, regenerations and sign-off are endpoints queued on the one worker, the run's state and allowed actions are derived from its files so paused and signed-off runs survive a restart, and SSE reports every state change; live Missouri loop through the API with a restart cost $0.12.
- **Goal:** run states `awaiting_checkpoint`, `drafting`, `refining`, `signed_off`;
  restart recovery; endpoints for checkpoint, revise, regenerate, sign-off, revisions
  and versions; SSE events for state changes.
- **Detailed plan:** (2026-11-02, branch `st12c-backend` off `hitl`)

  Author's answers at planning: runs started from the UI **pause by default** (form flag
  `unattended` for the old one-shot behaviour); `finished` stays the resting state of a
  drafted run that is open to refinement; review data goes into a `review` block on
  `RunStatus` plus `GET /revisions` and `GET /versions/{artefact}/{n}`; one live
  Missouri loop through the API at the end (~$0.10).

  *Run states* (`models.py`):

  ```
  queued → running → awaiting_checkpoint → drafting → finished ⇄ refining → signed_off
                   └──────────── failed (a pipeline stage or a job crash) ───────────┘
  ```

  `RESTING = {awaiting_checkpoint, finished, signed_off, failed}`: no job in flight; the
  SSE stream closes with `done` when the run rests. A failed revise or regenerate is a
  failed *revision*, not a failed run: the run returns to the state it rested in, with
  `error` set. `ARTIFACTS` gains `requirements_confirmed`, `checkpoint`, `current`,
  `revisions`. Request models `CheckpointRequest`, `ReviseRequest`, `RegenerateRequest`,
  `SignOffRequest`; response `JobAccepted`; `RunStatus.review: ReviewState` (checkpoint
  record, version state, stale list, sign-off, revision count, and `allowed`: which
  actions the run takes now, computed by code).

  *Store* (`store.py`): `state_from_log(log, run_dir)` knows `awaiting_checkpoint`
  (`waiting_checkpoint`), `signed_off` (`current.json`), `finished` (an `assemble`
  record finished), and judges failure by the latest record per stage (a failed
  regeneration leaves an earlier failed record on a healthy run, ST12b open issue).
  `stages_from_log` keeps the latest record per stage, adds `checkpoint` and `revise`.
  `review_state`, `allowed_actions`, `RunStore.version_file`.

  *Registry* (`runs.py`): one worker for every LLM job; `RunEntry` events are stage
  events plus `StateChange`s; `begin` refuses a busy run; `adopt` registers a run found
  on disk after a restart. Jobs: upload (`pause_at_checkpoint = not unattended`),
  `checkpoint` (`resume_pipeline`), `revise` (`refine.revise`), `regenerate`
  (`refine.regenerate`); `sign_off` runs in the request (code only). The chat model is
  built in the request, so a missing key is 503 and a bad spec 400 before queueing.

  *Routes* (`app.py`): `POST /runs/{id}/checkpoint` (403 sample, 409 not waiting or
  busy, 400 bad decisions via `validate_checkpoint`, 202), `POST /revise` (202 with the
  revision ID), `POST /regenerate` (202), `POST /sign-off` (200 `RunStatus`, 409 when
  stale), `GET /revisions`, `GET /versions/{artefact}/{n}`. SSE adds `event: state`.

  *Tests* (stubbed, `tests/test_ui_backend.py`): default pause; checkpoint drafts the
  rest with the brief; checkpoint refusals; revise, versions, stale, regenerate,
  sign-off and the frozen run; failed revise and failed regenerate leave the run
  `finished`; restart recovery of a paused run.

  *Docs*: backend README contract, D47, USAGE, README, TIMELOG, this file and the index.
- **What was done:** (2026-11-02, branch `st12c-backend` → `hitl`)
  - `ui/backend/models.py`: `RunState` with eight values and `RESTING` (replaces
    `TERMINAL`); `ARTIFACTS` gains `checkpoint`, `requirements_confirmed`, `current`,
    `revisions`; `StateChange`, `JobAccepted`, `Allowed`, `ReviewState`,
    `RunStatus.review`; requests `CheckpointRequest`, `ReviseRequest`,
    `RegenerateRequest`, `SignOffRequest` (reviewer stripped, non-empty).
  - `ui/backend/store.py`: `DISPLAY_ORDER` (pipeline, `checkpoint`, `revise`),
    `latest_records`, `stages_from_log` (latest record per stage, totals of every
    call of the stage), `state_from_log(log, run_dir)` (waiting checkpoint →
    `awaiting_checkpoint`, sign-off in `current.json` → `signed_off`, an assemble ever
    finished → `finished`, else failed), `allowed_actions`, `review_state`, tolerant
    loaders `load_version_state`/`load_revisions`/`load_checkpoint`,
    `RunStore.version_file` (the `.vN` copy, or the live file for the current version;
    `requirements.json` for a never-confirmed list); `stages_done` counts pipeline
    stages only.
  - `ui/backend/runs.py`: `RunEntry` events are `StageEvent | StateChange`;
    `is_idle`, `begin` (raises `RunBusy`), `wait_idle`, `totals` (spent before the job
    plus the job's ended stages); `RunRegistry.adopt` (entry for a run found on disk),
    `_queue` (soft failures return the run to where it rested), jobs `submit(...,
    unattended)`, `checkpoint`, `revise`, `regenerate` (return the revision ID),
    `sign_off` (synchronous).
  - `ui/backend/app.py`: upload form field `unattended` (default false, stored in
    `upload.json`); `POST /runs/{id}/checkpoint` (validates decisions with
    `validate_checkpoint` against the confirmed or extracted list, brief with
    `parse_brief`), `/revise`, `/regenerate`, `/sign-off`; `GET /runs/{id}/revisions`,
    `/versions/{artefact}/{n}`; 403 samples, 409 with the reason from the run's state,
    503 missing key; SSE `event: state`; `RunStatus.review` everywhere.
  - `ui/backend/README.md`: states table and diagram, files per touchpoint, endpoints,
    `review`, `state` events, restarts. `docs/USAGE.md` API section with curl examples;
    README checkpoint paragraph.
  - Tests (`tests/test_ui_backend.py`, 34, 9 new): `upload` defaults to unattended for
    the S14 tests; new: default pause, checkpoint drafts the rest with the brief,
    checkpoint refusals (400/403/404/409/422, a second checkpoint while the first is
    queued behind another run), revise → versions → stale → sign-off refused →
    regenerate → sign-off → frozen, also read back by a fresh app; failed revise and
    failed regenerate leave the run `finished` (also from disk); a paused and revised
    run confirmed from a fresh app; a run without a log refuses changes. Full suite
    451 passed, 10 paid-API tests deselected; ruff clean.
  - Live loop (Missouri, run `20261102-193819-b76fa3`, copied to the main checkout's
    `runs/st12c/`, gitignored), all through the HTTP API with a backend restart after
    the pause: upload paused with 127 requirements (141 calls, $0.075, 110 s); after the
    restart the run read `awaiting_checkpoint` with the checkpoint allowed; checkpoint
    with a four-section brief, R152 rejected and R051 made mandatory: 12 components, 12
    risks, 17 brief citations (3 calls, $0.027, 59 s); revise solution added C13 and two
    assumptions, risks stale (V01, $0.012, 20 s); sign-off refused with "stale risks";
    regenerate risk (V02, $0.010, 20 s); sign-off in 0.1 s froze requirements v1,
    problem v1, solution v2, risks v2; revise afterwards refused as frozen. State events
    after the restart: `awaiting_checkpoint, drafting, finished, refining, finished,
    refining, finished, refining, signed_off`. Whole run $0.124, 146 calls.
- **Deviations from plan:** `sign_off` passes through `refining` for the length of its
  re-assembly (a few hundred milliseconds) so a concurrent request sees the run busy.
  The 202 body carries the revision ID for regenerations too, not only revisions. A
  refused sign-off restores the run's state without setting `error`.
- **Open issues:**
  - The S15 frontend does not know the new states or the checkpoint: an upload from the
    UI now stops at `awaiting_checkpoint` with nothing to click until ST12d (the stream
    ends cleanly with `done`; `state` events are ignored). ST12d must also send
    `unattended` if it keeps a one-shot option.
  - Live run: the solution revision appended its citation IDs to the end of 20 unchanged
    claim texts ("... nine months. [H1]"), so the diff lists 20 changes nobody asked
    for. A `revise_solution` prompt rule (or stripping trailing `[ID]` lists in code)
    belongs to a prompt step, not this one.
  - A drafting lost to a restart leaves `checkpoint.json` and
    `requirements_confirmed.json` written but the log still waiting; confirming again
    applies the decisions on top of the confirmed list, so a repeated rejection is
    refused as an unknown ID (400) and the reviewer resubmits without it.
  - While a job is in flight, `nodes` is empty and `totals` is the pre-job log total
    plus the job's ended stages; exact once the run rests.
  - One worker serves all runs, so a revision can wait behind another run's pipeline
    (shown as `refining` meanwhile).
- **Decisions:** D47
