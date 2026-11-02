# ST12d. Frontend checkpoint

- **Status:** in progress
- **Summary:** (draft) Checkpoint tab in the UI: requirement row actions, model instructions on requirements and problem, a pursuit brief with a live H1..Hn preview, confirm with a reviewer name; lifecycle banner and all eight run states.
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
- **What was done:**
- **Deviations from plan:**
- **Open issues:**
- **Decisions:**
