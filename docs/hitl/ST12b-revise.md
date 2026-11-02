# ST12b. Revise primitive and versioning

- **Status:** done
- **Summary:** A reviewer's instruction revises any artefact under its stage's own checks (requirements as a quote-verified patch, the rest whole with stable IDs and no coverage loss), every change is versioned with a code-computed diff and cost, dependants go stale until regenerated, and sign-off freezes the run; live loop on Missouri cost $0.11.
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
- **What was done:** (2026-11-02, branch `st12b-revise` → `hitl`)
  - Roadmap: ST12 moved from `docs/ROADMAP.md` section 3.1 into `docs/hitl/` (index
    plus one file per step, text verbatim); section 3.1 is now a pointer; the project
    `CLAUDE.md` names the folder.
  - `schemas.py` (shared, schema owned by this step): `Artefact`, `RevisionKind`,
    `RevisionStatus`, `REVISION_ID_RE`; `RequirementEdit`, `RequirementsPatch`;
    `ComponentRevision`, `SolutionRevision`, `RiskRevision`, `RiskAssessmentRevision`;
    `ArtefactVersion`, `SignOff`, `VersionState`, `FieldChange`, `DiffSummary`,
    `RevisionRecord`, `RevisionLog`; `ReviewHistory` gains `revisions` and `sign_off`
    (defaults keep ST12a JSON valid).
  - `versions.py` (new, pure): `LIVE_FILES`, `DOWNSTREAM`, `live_path`, `version_path`,
    `is_versioned`, `ensure_live` (starts `requirements_confirmed.json` from the
    extractor's file), `load_/save_version_state`, `load_revisions`, `append_revision`,
    `next_revision_id`, `commit`, `mark_stale(present=...)`, `stale_artefacts`,
    `is_signed_off`, `review_history`, `diff`.
  - `graph.py` (shared): `END_STAGES`, `end_stage` on `build_pipeline` and `_invoke`;
    `REVISE` stage name with the `revise_` node prefix; `review` in the state, used by
    assemble; `load_state(confirmed=True)`; `resume_pipeline` applies decisions on top of
    the confirmed copy, versions it when it was revised while waiting, and carries the
    review history.
  - `checkpoint.py`: `strip_references` factored out of `apply_checkpoint`.
  - `agents/solution.py`, `agents/risk.py`: `base` and `extra` keyword hooks on
    `solution_schema` and `risk_schema`.
  - `agents/revise.py` (new): `requirements_patch_schema`, `apply_patch`,
    `revise_requirements`, `problem_evidence`, `revise_problem`,
    `solution_revision_checks`, `rekey_components`, `revise_solution`, `format_risks`,
    `risk_revision_checks`, `rekey_risks`, `revise_risks`; `NODES`, `PROMPTS`.
    Prompts `prompts/revise_{requirements,problem,solution,risk}.md`.
  - `refine.py` (new): `revise`, `regenerate`, `sign_off`, `open_run`, `drafted`,
    `body_of`, `realign_downstream`; `RefineError`, `RevisionFailed`, `RefineResult`.
    Each takes `on_event` (StageEvent `revise` started/finished/failed) for ST12c.
  - `render/markdown.py`: header "Signed off" line; review history "Revisions" (one
    line per record: kind, artefact, reviewer, instruction, versions, diff counts, what
    went stale, calls and cost, or the failure) and "Sign-off".
  - `cli.py`: `revise RUN ARTEFACT --reviewer (--instruction | --instruction-file)`,
    `regenerate RUN solution|risk --reviewer`, `sign-off RUN --reviewer [--note]`,
    `history RUN`; exit 2 for a request the run cannot take, 1 for a model or stage
    failure.
  - Tests: `tests/test_versions.py` (8), `tests/test_revise.py` (10),
    `tests/test_graph_refine.py` (13). Full suite 444 passed, 10 paid-API tests
    deselected.
  - Live run (Missouri, `runs/st12b/missouri`, gitignored), all through the CLI: `run`
    paused with 124 requirements ($0.054, 141 calls); `revise requirements` while
    waiting merged a duplicate pair (R034 removed, R047 reworded, references stripped;
    1 call, $0.006); `checkpoint` with a four-paragraph brief drafted 11 components and
    12 risks, coverage 77/77 ($0.027); `revise solution` added C12 "Surveyor review time
    saved per description, measured on MoDOT deeds" citing `H4` plus two assumptions (1
    call, $0.013); `sign-off` refused while the risks were stale (exit 2);
    `regenerate risk` (1 call, $0.009); `sign-off` froze requirements v2, problem v1,
    solution v2, risks v2. Whole run $0.109, 147 calls.
  - Docs: D45, D46; `ASSUMPTIONS.md` three bullets; `PROMPTS.md` design block and
    changelog row; `prompts/README.md`; `USAGE.md` "Refine and sign off"; README
    checkpoint paragraph; `TIMELOG.md`.
- **Deviations from plan:** the orchestration lives in a new `refine.py` and
  `review_history` in `versions.py` (so `graph.py` can import it without a cycle);
  `snapshot_if_first` became part of `commit` plus `ensure_live`. `mark_stale` gained
  `present`: the live run showed that a requirements revision made while waiting
  flagged the not-yet-drafted solution and risks stale, and the flag survived the
  draft (fixed, with a regression assertion). An empty diff records the revision with
  no new version and clears the artefact's own stale flag.
- **Open issues:** a regenerated risk assessment is renumbered by the risk stage, so its
  diff against the previous version matches unrelated risks by ID (63 added, 52 removed,
  56 changed on Missouri); matching regenerated items by title would read better. For
  ST12c: a failed `regenerate` leaves a FAILED stage record (from the graph wrapper),
  so `state_from_log` should judge a run by its last record per stage; runs now carry
  `revise` stage records, `current.json` and `revisions.json`. A requirement added by
  revision leaves the solution's coverage figure as drafted until the solution is
  regenerated or revised (it is marked stale). The live run's extraction skipped one
  chunk (S75.1, no structured output after three attempts), a pre-existing extractor
  behaviour unrelated to this step.
- **Decisions:** D45, D46
