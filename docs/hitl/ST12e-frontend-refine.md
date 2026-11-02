# ST12e. Frontend refine and sign-off

- **Status:** in progress
- **Summary:** (draft) Suggest-edits panel on every artefact tab, stored diffs, read-only old versions, stale banners with regenerate, a Review tab with sign-off and the full history, and clickable brief citations.
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
- **What was done:**
- **Deviations from plan:**
- **Open issues:**
- **Decisions:**
