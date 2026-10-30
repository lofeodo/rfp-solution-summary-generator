# CLAUDE.md — working rules for this repo

RFP solution-summary agent: a LangGraph pipeline that reads an RFP PDF and produces a
structured solution summary (requirements, approach, risks) with an eval harness and
observability. This is a 36-hour take-home; the author must be able to explain and
defend every decision live. **Doing less, cleanly and well-reasoned, beats a sprawling
half-build.**

## Memory model

- Context is cleared between steps. **`docs/ROADMAP.md` is the only memory.** Read it
  first in every session. Do not re-read the whole codebase; the roadmap's "what was
  done" sections must be specific enough to continue from and to write a PR description.
- Living docs, all under `docs/`: `ROADMAP.md`, `DECISIONS.md`, `ASSUMPTIONS.md`,
  `TIMELOG.md`, `PROMPTS.md` (prompt change notes). Prompts themselves live in
  `prompts/`, one file per agent. `README.md` at root.
- Project brief and architecture are summarised at the top of `docs/ROADMAP.md`;
  the assignment itself is `assignment.pdf` at root.

## Per-step loop (one roadmap step = one PR)

1. Read `docs/ROADMAP.md`. Find the next step whose "depends on" steps are all `done`.
2. Set its status to `in progress`. Flesh it out in plan mode.
3. **Ask the author every question the plan depends on, in one batch, before writing
   any code**: scope ambiguities, choices between approaches, anything the roadmap does
   not settle. Target zero mid-implementation questions. If something was genuinely
   missed, stopping to ask during implementation is acceptable but is the exception.
4. Write the detailed plan into the step's "Detailed plan" section. Commit it.
5. Implement. Each unit of progress is one commit.
6. Update the step's "What was done", "Deviations from plan", "Open issues".
7. Add entries to `docs/DECISIONS.md` (trade-offs, failure modes hit, fixes) and
   `docs/TIMELOG.md` (hours, mapped to the deliverable). If a prompt changed, add a
   line to `docs/PROMPTS.md` saying what changed and why.
8. Update `README.md` if behaviour or how-to-run changed.
9. Commit, push, open the PR, mark the step `done`, sync the branch.

## Definition of done per step

Tests pass, roadmap updated, README updated if behaviour changed, decisions and time
logged, PR opened.

## Branches and PRs

- All core work happens on one long-lived feature branch: `core`.
- Each roadmap step is a short-lived branch off `core` named `step-NN-<slug>`, opened
  as a PR into `core`, merged, then deleted. Several agents may work on independent
  steps at once; steps are scoped to touch separate files where possible, and the
  roadmap's dependency table says which steps may run in parallel.
- Before starting a step, sync `core` (`git pull`) and branch from it.
- When all core steps are done: merge `core` into `main`, delete `core` locally and
  remotely, sync `main`. Stretch goals get their own branches off `main`.
- Never push to `main` directly. Never force-push. Never merge without the author.

## Environment

- Conda env `rfp-solution-gen`. The agent creates it in the scaffold step
  (`conda create -n rfp-solution-gen python=3.12` then `pip install -r requirements.txt`)
  and runs all Python through it (`conda run -n rfp-solution-gen ...`). Keep
  `requirements.txt` up to date whenever a dependency is added; pin versions.
- `assignment.pdf` is gitignored; the public RFPs under `data/rfps/` are committed.
- Keys live only in `.env` (never committed). `.env.example` lists every variable.
- Provider and model are a single config setting. Default generator: DeepSeek.
  Judge for evals: Claude. Langfuse is optional and must become a no-op when its keys
  are absent.
- When writing LLM client code for Anthropic models, load the `claude-api` skill first.

## Code conventions

- Python 3.12, Pydantic v2 schemas in `src/rfp_agent/schemas.py` are the contract
  between agents. Change a schema only in a step that owns it, and note the change in
  the roadmap.
- Markdown output is rendered by code from the JSON, never by an LLM.
- Every factual claim an agent emits cites a chunk ID or requirement ID (see
  Traceability in the roadmap). Code validates citations; do not rely on prompts alone.
- Tests under `tests/`, run with `pytest`. Unit tests must not call paid APIs; mark
  anything that does with `@pytest.mark.llm` and skip it by default.
- No real client data anywhere. Only the public RFPs in `data/rfps/`.
- Do not build scrapers or fetch external documents in core steps.

## Communication with the author

- Batch questions at planning time. Give a recommendation with each question.
- Report outcomes faithfully: if tests fail, say so with the output.
- Keep PR descriptions derivable from the roadmap's "what was done".
