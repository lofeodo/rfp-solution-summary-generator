# ST12b. Revise primitive and versioning

- **Status:** in progress
- **Summary:** (draft) A natural-language instruction revises any artefact under its stage's validators, every change is versioned with a code-computed diff and an audit log, downstream artefacts go stale until regenerated, and sign-off freezes the run.
- **Goal:** `agents/revise.py` applies a natural-language instruction to any artefact
  with the producing stage's contract and validators; versioned storage
  (`<artefact>.vN.json`, `current.json` with stale flags), code-computed diff,
  append-only `revisions.json` with reviewer, instruction and cost; CLI `revise`,
  `regenerate`, `sign-off`.
- **Detailed plan:**
- **What was done:**
- **Deviations from plan:**
- **Open issues:**
- **Decisions:**
