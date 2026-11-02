# ST12c. Backend

- **Status:** in progress
- **Summary:** (draft) Backend run states, restart recovery, endpoints and events for the checkpoint, revisions and sign-off.
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
- **What was done:**
- **Deviations from plan:**
- **Open issues:**
- **Decisions:**
