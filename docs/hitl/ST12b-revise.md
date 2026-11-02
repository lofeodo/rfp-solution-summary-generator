# ST12b. Revise primitive and versioning

- **Status:** in progress
- **Summary:** (draft) A natural-language instruction revises any artefact under its stage's validators, every change is versioned with a code-computed diff and an audit log, downstream artefacts go stale until regenerated, and sign-off freezes the run.
- **Goal:** `agents/revise.py` applies a natural-language instruction to any artefact
  with the producing stage's contract and validators; versioned storage
  (`<artefact>.vN.json`, `current.json` with stale flags), code-computed diff,
  append-only `revisions.json` with reviewer, instruction and cost; CLI `revise`,
  `regenerate`, `sign-off`.
- **Detailed plan:** (written 2026-11-02 from the approved plan.) Asked and answered:
  mixed revise contract (whole artefact for problem, solution, risks; a patch for
  requirements); requirements may be revised while the run waits at the checkpoint;
  the summary is re-assembled automatically after every change; sign-off refuses while
  anything is stale; ST12 moved to this folder first. Decided by the agent: regenerate
  one stage at a time (never cascades); a revise or regenerate clears that artefact's
  stale flag; ambiguities and gaps are not revised (only references stripped).
  1. **Run directory.** Live files stay where readers expect them
     (`requirements_confirmed.json`, `problem.json`, `solution.json`, `risks.json`);
     copies `<stem>.vN.json`, v1 made on the first change; `current.json`
     (`VersionState`: version, stale, reason, updated per artefact; sign-off);
     `revisions.json` (append-only `RevisionLog`, V01, V02...). Requirements or problem
     change → solution and risks stale; solution change → risks stale. Removing a
     requirement strips its ID from solution and risks on disk and recomputes coverage,
     so the strict assembler still passes.
  2. **Schemas.** `Artefact`, `RevisionKind`, `RevisionStatus`; patch contract
     `RequirementEdit`, `RequirementsPatch(edits, additions: CitedRequirement, removals)`;
     revise contracts with an optional stable `id` (`ComponentRevision`,
     `SolutionRevision`, `RiskRevision`, `RiskAssessmentRevision`); `ArtefactVersion`,
     `SignOff`, `VersionState`, `FieldChange`, `DiffSummary`, `RevisionRecord`,
     `RevisionLog`; `ReviewHistory` gains `revisions` and `sign_off`.
  3. **Graph.** `end_stage` on `build_pipeline` and `_invoke` (band
     `start <= order <= end`, final edge `end_stage → END`); `REVISE` stage name and
     `revise_` node prefix; `review` in the state, used by assemble;
     `load_state(confirmed=True)` reads `requirements_confirmed.json`; `resume_pipeline`
     applies decisions on top of the confirmed copy and bumps its version if versioned.
  4. **`versions.py`** (pure): paths, load and save, snapshot of v1 (requirements also
     creates the confirmed copy), `commit`, `mark_stale`, `stale_artefacts`, revision log
     helpers, and `diff` (lists of dicts by `id`, claims by text, scalar lists as sets,
     field changes with before and after).
  5. **`agents/revise.py`**: requirements patch through a validator that refuses unknown
     or duplicate IDs, empty edits, unpaired quote and chunk, and quotes not verbatim in
     the named chunk; `apply_patch` (next free IDs, `origin = reviewed`, references
     stripped through `checkpoint.strip_references`). Problem through `problem_schema`
     over its evidence plus `H` IDs. Solution and risks through `solution_schema` and
     `risk_schema` with new `base`/`extra` hooks: unknown or duplicate IDs refused, a
     solution revision that uncovers a mandatory requirement covered today refused,
     coverage recomputed by code; IDs kept, new ones `max+1`, risks never renumbered.
  6. **Prompts** `revise_requirements`, `revise_problem`, `revise_solution`,
     `revise_risk`: instruction, current artefact, the producing stage's context; apply
     only the instruction, keep the rest verbatim, cite only shown IDs, guidance never
     waives a mandatory requirement.
  7. **`refine.py`**: `revise`, `regenerate`, `sign_off`, `review_history`,
     `realign_downstream`; continues the run log, emits `revise` stage events, records
     calls and cost per revision, re-assembles when drafted, keeps a waiting run paused;
     a failed revision is a failed record, never a failed stage. `RefineError` (exit 2),
     `RevisionFailed` (exit 1).
  8. **CLI** `revise`, `regenerate`, `sign-off`, `history`; **renderer** sign-off
     header line, "Revisions" and "Sign-off" in the review history.
  9. **Tests** `tests/test_versions.py`, `tests/test_revise.py`,
     `tests/test_graph_refine.py`, plus render and schema cases; no paid calls.
  10. **Live check** on Missouri: pause, revise requirements, checkpoint with a brief,
      revise the solution, sign-off refused while risks are stale, regenerate risks,
      sign off. **Docs:** D45, D46, assumptions, prompt notes, usage, README, time log.
- **What was done:**
- **Deviations from plan:**
- **Open issues:**
- **Decisions:**
