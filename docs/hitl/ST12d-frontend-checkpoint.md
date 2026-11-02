# ST12d. Frontend checkpoint

- **Status:** done
- **Summary:** The UI takes the checkpoint: a Checkpoint tab with per-row reject, strictness and type held as a browser-side draft, model instructions on the requirements or problem with each revision summarised, a pursuit brief with a live preview of its H1..Hn paragraphs, and confirm under a reviewer name, below a lifecycle banner that follows every run state live; live Missouri checkpoint through the UI with a restart cost $0.085.
- **Goal:** lifecycle banner and checkpoint page: requirement row actions, instruction
  box, brief form, confirm with reviewer name.
- **Detailed plan:** (2026-11-02, branch `st12d-frontend-checkpoint` off `hitl`)

  Author's answers at planning: the checkpoint is a **Checkpoint tab** (first, the
  default view while the run waits; read-only record afterwards) under a **lifecycle
  banner** (Read → Checkpoint → Draft → Refine → Sign-off); the brief is **one textarea**
  with an "insert template" button and a **live preview of its H1..Hn chunks** (a TS
  port of `parse_brief`, the server stays the authority); the **instruction box** targets
  requirements or problem (both allowed at the checkpoint) and shows a compact result
  (applied/failed, cost, added/removed/changed), the full diff view stays in ST12e;
  **one live Missouri checkpoint through the UI** at the end (~$0.10).

  1. *Types and client* (`api/types.ts`, `api/client.ts`): the eight run states and
     `RESTING`; stage status `waiting`; mirrors of `RequirementDecision`, `Brief`,
     `CheckpointRecord`, `VersionState`, `SignOff`, `Allowed`, `ReviewState`,
     `RevisionRecord`, `DiffSummary`, `JobAccepted`; `RunStatus.review`;
     `Requirement.origin`; artifacts `checkpoint`, `requirements_confirmed`;
     `api.checkpoint`, `api.revise`, `api.revisions`; upload option `unattended`.
  2. *Hooks*: `useRun` keeps the SSE stream open while the run is busy (queued,
     running, drafting, refining), refreshes on `state` events, and returns `refresh()`
     so a page re-polls after posting a job; `useArtifact` refetches when an artefact's
     version changes; `useRunData.requirements` prefers the confirmed list, plus
     `extracted` and `checkpoint`.
  3. *Pure logic with tests*: `lib/brief.ts` (`parseBrief`, template), `lib/checkpoint.ts`
     (row draft → decisions sent only for changed rows, prune after a revision, counts),
     `lib/lifecycle.ts` (state → phase and next action), localStorage helpers for the
     reviewer name and the per-run draft.
  4. *Checkpoint view* (`views/CheckpointView.tsx`, `views/CheckpointRows.tsx`): filtered
     requirement table with reject, strictness and type per row; instruction box;
     brief with preview; reviewer, note, summary of what will be sent, confirm; inline
     errors; read-only record once confirmed.
  5. *Lifecycle and run page*: `StateBadge` for every state, a `checkpoint` row in the
     stage timeline, `components/Lifecycle.tsx`, Checkpoint tab and default-tab logic in
     `RunPage.tsx` (minimal edits; shared with ST12e), `unattended` checkbox on the
     upload form.
  6. *Docs*: this file, the index, frontend README / USAGE / README as needed,
     DECISIONS, TIMELOG.

  Verification: typecheck, vitest, build, pytest once; live Missouri upload driven with
  Playwright through the checkpoint (reject, strictness change, one instruction, brief,
  confirm) to a drafted run, with a backend restart while waiting.
- **What was done:** (2026-11-02, branch `st12d-frontend-checkpoint` → `hitl`)
  - `api/types.ts`: `RunState` with the eight backend states, `RESTING`/`isResting`;
    `StageStatus` adds `waiting`; mirrors of `RequirementDecision`, `Brief`,
    `CheckpointRecord`, `ArtefactVersion`, `VersionState`, `SignOff`, `Allowed`,
    `ReviewState`, `FieldChange`, `DiffSummary`, `RevisionRecord`, `RevisionLog`,
    `JobAccepted`, request bodies `CheckpointBody`, `ReviseBody`; `RunStatus.review`;
    `Requirement.origin`; artifacts `checkpoint`, `requirements_confirmed`.
  - `api/client.ts`: `postJson`; `api.checkpoint`, `api.revise`, `api.revisions`;
    `RunOptions.unattended` (form field sent only when on).
  - `hooks/useRun.ts`: the SSE stream is open while the run is busy (keyed on
    `[id, live]`, so a POSTed job reopens it), `state` events refresh the status, stages
    are reset from the status when the run rests; returns `refresh()`. `useArtifact`
    takes a version key. `hooks/useRunData.ts`: refetches requirements (confirmed),
    problem, solution and risks when their `current.json` version moves;
    `requirements` is the confirmed list once it exists, plus `extracted` and
    `checkpoint`. **For ST12e:** these version keys already refetch revised artefacts.
  - `lib/brief.ts` (`parseBrief`, port of `parse_brief`; `BRIEF_SECTIONS`,
    `BRIEF_TEMPLATE`, `dropUnfilledTemplate`), `lib/checkpoint.ts` (`setRow`, `prune`,
    `decisions`, `effective`, `counts`), `lib/lifecycle.ts` (`PHASES`, `lifecycle`,
    `phaseIndex`), `lib/revisions.ts` (`compactDiff`: diff paths grouped by item),
    `lib/storage.ts` (guarded localStorage; reviewer name and per-run draft).
  - `views/CheckpointView.tsx`: the tab. While waiting (or refining before any draft):
    reviewer name, requirement rows, instruction box (requirements or problem from
    `review.allowed.revise`, revision log as compact lines), brief with template and H
    preview, confirm box (counts, brief size, reviewer, note; inline 400/409/503).
    After confirmation: the record (reviewer, time, wait, note, rejected, edited with
    before → after, brief as H1..Hn). Runs without a checkpoint say so.
    `views/CheckpointRows.tsx`: filters (type, strictness, changed, search), per-row
    type and strictness selects and reject toggle, edited/rejected marks, undo all.
  - `components/Lifecycle.tsx` (banner with the five phases and the next action, link to
    the checkpoint); `components/ui.tsx` `StateBadge` for all states (busy ones pulse);
    `lib/stages.ts` a human `checkpoint` row (`waiting`, or `skipped` on runs that never
    paused; `stagesDone` counts timeline stages only); `StageTimeline.tsx` markers for
    both; `UploadForm.tsx` "unattended" checkbox.
  - `views/RunPage.tsx` (**shared with ST12e**): `Checkpoint` tab first; with no tab in
    the URL the page opens on `checkpoint` while the run waits, `solution` otherwise;
    `live` = not resting; `Lifecycle` under the header (not on samples); passes
    `refresh` to the checkpoint view.
  - Tests: `lib/review.test.ts` (14: brief split mirrored from
    `tests/test_checkpoint.py`, template dropping, draft to decisions, reset, rejection
    without edits, pruning, counts, lifecycle, diff grouping) and 2 new stage tests in
    `lib/lib.test.ts`; 27 Vitest tests, typecheck and build clean; Python suite
    unchanged (see below).
  - Docs: D49, README checkpoint paragraph, USAGE UI section, TIMELOG, this file and
    the index.
  - Live (Missouri, run `20261102-200113-0557af`, copied to the main checkout's
    `runs/st12d/`, gitignored), driven with Playwright on the built UI: upload paused
    with 115 requirements ($0.054, about 60 s); the page opened on the Checkpoint tab
    with the banner and the waiting row; rejected R010, R008 mandatory → desired, R005
    → optional, then the instruction "merge R005 into R001" (V01, applied, $0.006,
    2 s): R005 left the table and its draft row was pruned. Backend restarted while
    paused: the run came back `awaiting_checkpoint` and a reload kept the reviewer,
    the rejection and the edit. Brief from the template with two of five sections
    filled: preview H1 (win theme) and H2 (constraints). Confirmed with a note: the
    page followed `drafting` → `finished` live without a reload; the Solution
    tab showed five H1/H2 citations, the Risks tab 12 risks; Requirements tab shows the
    confirmed 113; the Checkpoint tab shows the record (waited 2 m 09 s). Whole run
    $0.085, 145 calls. No console errors; no horizontal scroll at 390 px.
- **Deviations from plan:** `lib/revisions.ts` (`compactDiff`) was added after the live
  run showed nested diff paths (`requirements[R001].chunk_ids[S4.1]`) garbling the
  compact line. The template-heading cleanup only drops the template's own headings,
  not every empty heading (the reviewer's text is never altered). The plan's "bulk
  reset" is an "undo all N changes" link. H citations in the record are labels, not
  chips: the citation chips do not know brief IDs (see open issues).
- **Open issues:**
  - Brief citations (`H1`) in the Solution and Risks views render as plain text, not
    clickable chips with the brief paragraph; `lib/ids.ts` and the source panel do not
    know `H` IDs. Belongs with ST12e's view work.
  - After confirming, the page with no tab in the URL moves to the Solution tab (the
    default for a drafting run); a reviewer who opened `/checkpoint` explicitly stays
    there. Deliberate (the draft lands there), noted in case it reads as a jump.
  - Revisions made at the checkpoint are listed on the form but not in the read-only
    record; the review history across the run is ST12e's.
  - The checkpoint form was checked at desktop width with real data; at phone width
    only the record view was checked (no overflow).
  - `main` has ST2's VLM checkbox in `UploadForm.tsx`; the `hitl` → `main` merge will
    need both checkboxes kept.
- **Decisions:** D49
