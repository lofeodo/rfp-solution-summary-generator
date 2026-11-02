# ST12e. Frontend refine and sign-off

- **Status:** done
- **Summary:** The UI closes the loop after the draft: each artefact tab has a "Suggest edits" panel, a version bar with read-only older versions and a stale banner with Regenerate, a Review tab signs off and shows the whole history with every stored diff, and brief citations open the reviewer's paragraph; live Missouri revise, regenerate and sign-off through the UI cost $0.020.
- **Goal:** Suggest-edits panel on every artefact tab, diff view, version selector,
  stale banners with regenerate, sign-off, review history.
- **Detailed plan:** (2026-11-02, branch `st12e-frontend-refine` off `hitl`)

  Author's answers at planning: refine controls **on each artefact tab** (Solution,
  Requirements, Risks, Problem: a "Suggest edits" panel, a version selector, a stale
  banner with Regenerate) plus a new **Review tab** (sign-off form or record, stale
  summary, the whole history with diffs, cost); the diff view renders each revision's
  **stored** `DiffSummary` (before → after per field; no client-side diffing), and old
  versions are **browsable read-only** through the existing
  `GET /runs/{id}/versions/{artefact}/{n}`; brief citations `H1..Hn` become **clickable
  chips** that open the brief paragraph in the source panel (ST12d open issue); the live
  check **reuses ST12d's drafted Missouri run** (~$0.03–0.05). Frontend only: the
  backend contract from ST12c is complete.

  1. *Client* (`api/types.ts`, `api/client.ts`): `RegenerateBody`, `SignOffBody`;
     `api.regenerate`, `api.signOff`, `api.version(id, artefact, n)`.
  2. *Pure logic with tests* (`lib/revisions.ts`): `diffRows` (changes grouped by item,
     values shown as short text), `stageOf` (`risks` → `risk`), per-artefact history,
     sign-off blockers, `versionBody` (the reviewer-visible part of a version file, the
     same sub-object the stored diff compares).
  3. *Brief chips*: `lib/ids.ts` kind `brief` and `RunIndex.brief` from the checkpoint;
     `components/source.tsx` style and title; `SourcePanel` case.
  4. *Components*: `ReviseBox` (instruction for one artefact, its revision lines, uses
     `review.allowed.revise`), `RevisionLine` moved out of `CheckpointView`, `DiffView`,
     `ArtefactBar` (version selector, stale banner with Regenerate, frozen note),
     `SignOffForm`; a `ReviewContext` in `RunPage.tsx` so views do not thread props.
  5. *Views*: the four artefact views render the bar above and the panel below, and a
     selected old version in place of the current data; `views/ReviewView.tsx`.
  6. *Run page and banner* (minimal shared edits): Review tab; `Lifecycle` shows stale
     artefacts or "ready to sign off" with a link to the Review tab.
  7. *Docs*: this file, the index, DECISIONS, TIMELOG, README / USAGE / frontend README.

  Verification: typecheck, Vitest, build, pytest once; live on the copied ST12d run with
  Playwright: H chip opens the brief, revise the solution → diff, risks stale and
  sign-off blocked, regenerate risks → clear, view solution v1 and back, Review tab
  history, sign off → frozen; 390 px, no console errors.
- **What was done:** (2026-11-02, branch `st12e-frontend-refine` → `hitl`)
  - `api/types.ts`: `RegenerateStage`, `RegenerateBody`, `SignOffBody`.
    `api/client.ts`: `api.regenerate`, `api.signOff` (returns `RunStatus`),
    `api.version(id, artefact, n)` over `GET /runs/{id}/versions/{artefact}/{n}`, and
    `VERSION_FILE` (artefact → the live artifact whose shape a version file has).
  - `lib/revisions.ts`: `diffRows` (a stored `DiffSummary` grouped by item: whole items
    added or removed, fields changed with before/after text; claims keyed by text,
    positional items by index), `showValue`, `ARTEFACT_LABEL`, `stageOf` (`risks` →
    `risk`), `canRegenerate`, `signOffBlockers` (mirrors the server's refusals),
    `historyOf`, `totalCost`. `lib/lifecycle.ts`: `refineNote` ("Stale: …" or "Ready to
    sign off.").
  - Brief chips: `lib/ids.ts` kind `brief` (`H\d+`), `RunIndex.brief` and `briefBy` from
    the checkpoint record (`useRunData` passes it); `components/source.tsx` accent-soft
    chip with the paragraph as title; `SourcePanel` case: the paragraph, who wrote it,
    "human input, not the RFP".
  - `hooks/useReview.ts`: `ReviewContext` (`runId`, `status`, `refresh`, `log`,
    `reviewer`, `setReviewer`; null on samples), `useReviewer` (the `rfp.reviewer`
    key), `useRevisionLog` (reread when the record count moves and the run rests),
    `useVersion` (fetch one stored version while picked).
  - Components: `DiffView.tsx` (`DiffView`; `RevisionLine` moved here from
    `CheckpointView`, now with kind, time, "made stale" and a show/hide diff toggle),
    `ReviewControls.tsx` (`INPUT`, `AREA`, `Alert`, `ReviewerField`,
    `RegenerateButton`), `ArtefactBar.tsx` (version radio group, read-only strip with
    "back to the current version", stale banner with reason and Regenerate, signed-off
    note), `ReviseBox.tsx` ("Suggest edits": per-artefact hint and downstream effect,
    instruction, the artefact's revisions with diffs), `SignOffForm.tsx` (reviewer,
    note, blockers, sign off; the signed-off record), `Refinable.tsx` (wraps a view once
    the run has a draft: bar above, panel below, an old version swapped into `RunData`;
    the views are unchanged).
  - `views/ReviewView.tsx`: Review tab (00 Sign-off, 01 Versions with regenerate,
    02 History newest first with diffs open when ≤ 8 records, the checkpoint last).
  - Shared edits: `RunPage.tsx` (Review tab after Problem, `ReviewContext` provider,
    the four artefact tabs wrapped in `Refinable`, `review` passed to `Lifecycle`);
    `Lifecycle.tsx` (refine note with "Open the review →" / "Sign off →");
    `CheckpointView.tsx` (reviewer name from the context, `RevisionLine` imported).
  - Tests: `lib/refine.test.ts` (9: diff rows for components, claims and positional
    items, value display, stage mapping, sign-off blockers, history and cost, refine
    note, brief index). 36 Vitest tests, typecheck and build clean; pytest unchanged
    (no Python touched).
  - Docs: D49, README paragraph, USAGE UI section, TIMELOG, this file and the index.
  - Live (the ST12d Missouri run `20261102-200113-0557af`, copied into the worktree and
    afterwards to the main checkout's `runs/st12e/`, gitignored), Playwright on the built
    UI: an H2 chip opened the constraints paragraph with "written by Dana Reviewer";
    the instruction "rename C01 … Azure, add an assumption about 500 historical
    descriptions" was applied (V02, $0.0112, 18 s): solution v2, diff showed the title
    and description before → after, the added claim and assumption; risks stale ("solution
    changed in V02 (v2)"), sign-off blocked with "Risks is stale", banner "Stale: risks";
    Regenerate risks (V03, $0.0089, 21 s) cleared it and enabled sign-off; solution v1
    shown read-only (old C01 title, no edit panel) and back; signed off with a note:
    record with versions (requirements v3, problem v1, solution v2, risks v2), tabs
    frozen, banner "Signed off", `summary.md` carries the review history. 390 px: no page
    overflow (the tab strip scrolls as before); no console errors or warnings. $0.020.
- **Deviations from plan:** the views were not edited: a `Refinable` wrapper in
  `RunPage.tsx` does the bar, the swap and the panel, so `*View.tsx` stay as they were.
  `versionBody` was not needed: a version file has the same shape as the live artifact.
  The reviewer name moved into a context shared with the checkpoint form, so the two
  cannot disagree.
- **Open issues:**
  - Citation chips on an old version still describe the current outputs (the index is
    built from current data); the read-only strip says so.
  - Solution and risks versions created by a requirements removal (realignment) have no
    record of their own, so the version bar can show a version no history line explains.
  - The header's "Wall" is started → finished and grows with every revision (42 min on
    the live run); it predates ST12e and could show the drafting wall instead.
  - The Review tab and the panels were checked on a run with a checkpoint; an unattended
    run shows "unattended: no checkpoint" in the history (by code, not live).
  - `hitl` → `main`: decision numbers clash (main has D42 = ST2) and `UploadForm.tsx`
    needs both checkboxes kept (ST12d's note).
- **Decisions:** D49
