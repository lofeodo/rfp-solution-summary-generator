# ST12a. Checkpoint in the pipeline

- **Status:** done
- **Summary:** The pipeline pauses after requirements and problem extraction, takes a named reviewer's decisions and a pursuit brief that becomes citable evidence (H1, H2...), and resumes drafting from the run directory; unattended runs are unchanged.
- **Goal:** the pipeline can stop after requirements and problem extraction, take a
  checkpoint record (reviewer, per-requirement decisions, pursuit brief) and resume from
  `solution` with the brief as citable evidence; the summary carries the review
  history; unattended runs are unchanged.
- **Detailed plan:** (written 2026-11-02 from the approved plan; decisions made by the
  agent rather than asked: row actions deterministic, brief as `H` chunks, reviewer as a
  free-text name, regeneration never automatic)
  1. **Schemas** (`schemas.py`). `BRIEF_CHUNK_ID_RE = ^H\d+$`; `EVIDENCE_ID_RE` accepts
     either a split chunk or a brief chunk and replaces `CHUNK_ID_RE` on `ChunkRef.id`
     only (split `Chunk.id` and requirement quotes stay RFP-only). `ChunkRef` gains
     `source: EvidenceSource` (`rfp` | `brief`) and nullable pages for brief refs.
     `BriefChunk(id, text)`, `Brief(text, chunks)`. `RequirementOrigin`
     (`generated` | `reviewed`) with `Requirement.origin` defaulting to `generated`.
     `RequirementDecision(requirement_id, action accept|reject, strictness?, type?,
     note?)`, `CheckpointRecord(reviewer, confirmed_at, waited_s, decisions, brief?,
     note?)`, `ReviewHistory(checkpoint?)`, `SolutionSummary.review: ReviewHistory |
     None`. `StageStatus.WAITING` for the checkpoint stage record.
  2. **Brief** (`brief.py`). `parse_brief(text)` splits on blank lines into `H1..Hn`
     chunks (headings attach to the paragraph that follows), `None` when blank;
     `brief_chunk_refs(brief)`; `format_brief(brief)` renders `H1: text` lines or
     "None provided." for the prompts.
  3. **Checkpoint** (`checkpoint.py`). `apply_checkpoint(requirements, record)`:
     rejects unknown or duplicate IDs with a `ValueError` naming them; `reject` drops
     the requirement and strips its ID from `conflicts_with` and ambiguity
     `requirement_ids`; a strictness or type change sets `origin = reviewed`. Pure, so
     the backend can validate before resuming.
  4. **Agents.** `build_solution(..., brief=None)` and `build_risks(..., brief=None)`:
     `allowed_chunk_ids` adds the brief IDs, `render_prompt` fills a new `{{brief}}`
     section. `prompts/solution.md` and `prompts/risk.md` gain "Pursuit team guidance"
     (what it is, cite `H` IDs for anything that rests on it, it may steer design
     choices but never waives a mandatory requirement) and keep the evidence rules.
  5. **Graph** (`graph.py`). `CHECKPOINT = "checkpoint"` (not in `STAGES`),
     `build_pipeline(start_stage=PARSE, pause_at_checkpoint=False)`: `START` →
     `start_stage`; `[requirements, problem]` → `checkpoint` → conditional edge to
     `solution` or `END`. When pausing, the node records `StageRecord(checkpoint,
     WAITING)` and emits the event; unattended, it is a no-op and records nothing, so
     the run log matches today's. `assemble` adds the brief chunk refs and
     `review`. `load_state(run_dir)` reads the stage files back into the typed models.
     `resume_pipeline(run_dir, record, ...)`: `RunRecorder.from_log` reloads
     `run_log.json`, the WAITING record becomes FINISHED with `latency_s = waited`,
     `checkpoint.json` and `requirements_confirmed.json` are written, the graph is
     invoked from `solution` with the confirmed requirements. `run_pipeline(...,
     pause_at_checkpoint=False)`; `PipelineResult.summary` becomes optional and
     `paused` says where it stopped.
  6. **CLI** (`cli.py`). `run` pauses at the checkpoint by default and prints the next
     command; `--unattended` runs through. `checkpoint <run_id> --reviewer NAME
     [--brief FILE] [--reject R003]... [--strictness R005=desired]...
     [--type R007=technical]... [--note ...]` confirms and resumes in one command.
  7. **Renderer** (`render/markdown.py`). Brief refs cite as `(Pursuit brief [H2])`;
     header gets the reviewer; a "Review history" section lists the checkpoint
     decisions and the brief.
  8. **Tests** (`tests/test_graph.py`, `test_checkpoint.py`, `test_brief.py`,
     `test_solution.py`, `test_risk.py`, `test_render.py`, `test_schemas.py`): paused
     run writes every read-stage file and a WAITING record; resume reproduces the
     unattended output; decisions applied (rejected ID absent everywhere, strictness
     changed, origin reviewed, unknown ID refused); brief chunks reach the prompts and
     the allowed IDs, an `H` citation passes the solution validator and the assembler;
     renderer output for brief citations and the history; CLI `checkpoint` round trip.
  9. **Docs.** D42 (the design and its guards), D43 (pause via the run directory),
     D44 (brief as citable chunks); `ASSUMPTIONS.md` "Human in the loop";
     `PROMPTS.md` two lines; README "Checkpoint and refine"; `TIMELOG.md`.
- **What was done:** (2026-11-02, branch `st12a-checkpoint` → `hitl`)
  - `schemas.py`: `BRIEF_CHUNK_ID_RE`, `EVIDENCE_ID_RE`; enums `EvidenceSource`,
    `RequirementOrigin`, `DecisionAction`; `Requirement.origin`; `BriefChunk`, `Brief`,
    `RequirementDecision`, `CheckpointRecord` (with `rejected_ids`, `edited_ids`),
    `ReviewHistory`; `ChunkRef.source` and nullable pages; `SolutionSummary.review`;
    `StageStatus.WAITING`. Shared file, schema owned by this step.
  - `brief.py` (`parse_brief`, `brief_chunk_ids`, `brief_chunk_refs`, `format_brief`)
    and `checkpoint.py` (`validate_checkpoint`, `apply_checkpoint`, `CheckpointError`,
    the two file names). Both pure.
  - `agents/solution.py` and `agents/risk.py`: `brief` parameter on `allowed_chunk_ids`,
    `render_prompt`, `build_solution`, `build_risks`; `prompts/solution.md` and
    `prompts/risk.md`: "Pursuit team guidance" block (`{{brief}}`) and rule.
  - `graph.py`: `CHECKPOINT` node after the `[requirements, problem]` join with a
    conditional edge to `solution` or `END`; `build_pipeline(start_stage,
    pause_at_checkpoint)` builds only the nodes from `start_stage` on (`START_STAGES`);
    `load_state`, `waiting_checkpoint`, `resume_pipeline`, `PipelineStateError`;
    `run_pipeline(pause_at_checkpoint)`; `PipelineResult.summary` optional with
    `paused_at`; the shared `_invoke`. `observability.py`: `RunRecorder.from_log`,
    `pause`. `render/assemble.py`: `brief` and `review`; `render/markdown.py`: page-less
    brief citations, checkpoint line in the header, "Review history" section.
  - `cli.py`: `run` pauses by default and prints the next command, `--unattended`;
    `checkpoint <run_id> --reviewer --brief --reject --strictness --type --note`;
    `waiting` event line; wall time of a paused run counted to now.
  - Tests: `tests/test_checkpoint.py` (13: brief parsing, decisions, validators,
    assembler, renderer) and `tests/test_graph_checkpoint.py` (11: pause, unattended
    unchanged, `load_state` round trip, partial graph, resume on the same log,
    rejection, refusals, CLI round trip and error exits); stubs take `brief`; two CLI
    tests pass `--unattended`; placeholder sets include `brief`. 426 tests pass.
  - Live run (Missouri, `runs/st12a/missouri`, gitignored): read stages 141 calls,
    $0.051, paused with 128 requirements, 51 ambiguities, 12 gaps; `checkpoint` with
    a five-paragraph brief, `--reject R086`, `--strictness R048=mandatory`,
    `--type R107=legal_contractual` after 139 s: 3 more calls, $0.024, 127
    requirements, 9 components, 12 risks, coverage 75/75, 0 retries; the summary cites
    the brief 14 times (`(Pursuit brief [H2])`), the review history lists the reviewer,
    the note, the rejection and the two edits. Whole run $0.075, 246 s wall.
  - Docs: D42 to D44, `ASSUMPTIONS.md` "Human in the loop", `PROMPTS.md` design notes
    and changelog row, `USAGE.md` CLI section, README checkpoint paragraph, `TIMELOG.md`.
- **Deviations from plan:** the brief lives inside `CheckpointRecord` rather than as
  a separate `brief_chunks` field of `ReviewHistory`, so one file (`checkpoint.json`)
  holds the whole touchpoint. `START_STAGES` also admits `split`, `requirements`,
  `risk` and `assemble`, which ST12b's regeneration will use. A no-op edit (same
  strictness or type) leaves `origin = generated`.
- **Open issues:** the UI backend's `RunState` and the frontend's stage status type do
  not know `waiting` yet (ST12c, ST12d); a run paused from the UI is not yet possible
  because the backend always runs unattended. Rendered brief chunks keep their markdown
  heading marks (`# Win themes ...`); ST12e's brief form can drop them. The eval harness
  and the samples stay unattended by construction; no harness flag exposes the brief.
- **Decisions:** D42, D43, D44
