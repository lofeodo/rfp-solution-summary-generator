# TIMELOG.md

Hours per part, as the assignment asks. Two views: per deliverable (what the reviewer
wants) and per session (how the work actually happened).

**How these were measured.** Hours are the author's wall-clock time, not agent time.
Step times come from the git history (from the plan commit, or the previous merge, to
the step's merge), rounded to the quarter hour, and were then checked with the author:
gaps between steps were breaks and are not counted, except two on 2026-11-02 that were
human-in-the-loop design and planning (git only shows when an agent commits). Several steps ran at the same time
in parallel agents; those share one row and one time window, so the rows add up to the
real total. An earlier version of this file estimated each step on its own and came to
42.75 h; that overcounted parallel work and breaks by nearly half.

## Per deliverable

| Deliverable | Hours | Notes |
|---|---|---|
| 0. Reading, research, planning | 4.0 | 2.0 assignment, public RFPs and brainstorming; 2.0 input inspection, roadmap, working rules and living docs |
| 1. Working app (pipeline, parsing, agents, CLI) | 3.5 | S0 scaffold 0.5; S1, S2, S9 LLM layer, parsing, renderer 0.25; S3, S4 splitting and parse-quality pass 0.5; S5, S6 requirements and problem statement 0.75; S7 solution generator 0.25; S8 risk assessor 0.75; S10 pipeline graph, CLI and live runs 0.5 |
| 2. Prompt assets and notes | 1.75 | Prompt writing, live runs and tuning rounds inside S5, S6 (0.5), S7 (0.25), S8 (0.5); S13 judge_match and solution rules with before/after runs 0.5 |
| 3. Evaluation harness and sample results | 2.0 | S11 gold labels 0.5; S12 harness, baseline judged runs and agreement sample 0.5 (shared window with S14, S15); S13 rescoring, diff, two ablations and fix runs 1.0 |
| 4. Observability | 0.5 | S1 run recorder, cost, Langfuse handler 0.25; S10 stage records, stage events, per-stage cost 0.25 |
| 5. DECISIONS.md and other docs | 1.0 | S16 Dockerfile, regenerated samples, README, demo script 0.5; S16 follow-up README rewrite and PIPELINE/USAGE/AUTHOR docs 0.5. Step docs and decisions were written inside each step and are counted there |
| 6. Demo | 0.5 | Recording, from the script in docs/AUTHOR.md |
| UI (part of 1, tracked separately) | 0.5 | S14 backend and S15 frontend, shared window with S12 |
| **Core total** | **13.75** | S0 to S16 plus the demo, well inside the 36 h framing |
| Stretch (after core) | 8.5 | Human-in-the-loop design 1.0; ST2 vision-model transcription, ST13 prompt structure and ST12a checkpoint in parallel 1.0; ST12b to ST12e human in the loop (with 1.75 of ST12b planning) and branch sync 4.5; merges into `main` 0.75; remove runs 0.25; README chart and reshape 1.0. Human in the loop alone is about 6 to 6.5 |
| **Total** | **22.25** | |

## Per session

| Date | Step(s) | Window | Hours | Deliverable | Notes |
|---|---|---|---|---|---|
| 2026-10-29 | Reading | — | 2.0 | 0 | Read assignment, studied public RFPs, brainstormed the solution |
| 2026-10-30 | Planning | to 08:40 | 2.0 | 0 | Inspected the four RFPs, surfaced assignment points, wrote ROADMAP, CLAUDE.md, living docs |
| 2026-10-30 | S0 | 08:40–09:16 | 0.5 | 1 | Scaffold: conda env, pins, config, schemas, tests, CI, README skeleton, docs |
| 2026-10-30 | S1, S2, S9 (parallel) | 09:20–09:51 | 0.5 | 1, 4 | S1 LLM factory, structured_call with retry, run recorder, Langfuse, DeepSeek thinking-mode fix; S2 PDF parsing, normaliser, header strip, flags, tests; S9 assembler with citation check, markdown renderer, golden tests, D16 |
| 2026-10-30 | S11 | 10:03–10:32 | 0.5 | 3 | Gold format and script, Claude drafts ($1.6), F4/F5 fixes, correction of all four RFPs, Federal Way image table |
| 2026-10-30 | S3, S4 (parallel) | 10:32–11:03 | 0.5 | 1, 2 | S3 outline-located headings, 300-word chunks with overlap, kind tags, invariant and golden tests, D25 to D27; S4 parse-quality judge, attribution rule, VLM hook, live run on four RFPs ($0.005), D24 |
| 2026-10-30 | S5, S6 (parallel) | 11:03–12:23 | 1.25 | 1, 2 | S5 requirements extractor with verified quotes, dedupe with fallback, single-call mode, 23 fake-model tests, two prompts tuned, five live runs ($0.25), D29 to D31, F8, F9; S6 problem statement with per-chunk summaries, full-text baseline, live runs in both modes ($0.25), .gitattributes LF fix, D28 |
| 2026-10-30 | S7 | 13:24–13:55 | 0.5 | 1, 2 | Solution generator: code-computed coverage, LangGraph generate/check/revise loop, 23 fake-model tests, live runs on four RFPs twice ($0.45), D32, F10, F11 |
| 2026-10-30 | S8 | 13:55–15:14 | 1.25 | 1, 2 | Risk assessor: code-computed findings block, must-cite and count band, 18 fake-model tests, live runs on four RFPs twice ($0.08), D33, F12 |
| 2026-10-30 | S10 | 15:14–16:03 | 0.75 | 1, 4 | Pipeline graph with the S5/S6 fan-out, stage records and events, run CLI with ablation flags, 13 stubbed-stage tests, live runs, committed samples, D34 |
| 2026-10-30 | S12, S14, S15 (parallel) | 16:03–17:06 | 1.0 | 3, UI | S12 eval harness (gold matching, precision, grounding, checklist, rubric, risks, consistency, pairwise, agreement), 30 scripted-judge tests, 12 judged runs (about $6.7), 40 hand labels, D36, D37, F13, F14; S14 FastAPI backend, run queue, SSE, 27 tests, API contract, D35; S15 Vite/React frontend, live timeline, citation chips with source slide-over, 11 Vitest tests, Playwright passes, D38, F15 |
| 2026-10-30 | S13 | 18:22–19:51 | 1.5 | 2, 3 | Harness `--only` rescoring and `diff`; F14 judge_match rule and baseline rescore; full-text and single-call ablations (16 runs); solution "name what you cite" rule on 8 fresh runs; D39, D40, F16 (about $4.3) |
| 2026-10-30 | S16 | 20:23–20:43 | 0.5 | 5 | Two-stage Dockerfile built and smoke-tested, four samples regenerated ($0.29), README status, Docker, demo script and live-change rehearsals, PROMPTS management notes, D41, PR `core` → `main` |
| 2026-11-02 | S16 follow-up | to 09:03 | 0.5 | 5 | README rewrite (GUI-first, diagrams, screenshot, results table), docs/PIPELINE.md, docs/USAGE.md, docs/AUTHOR.md; shell-neutral run steps; `core` merged into `main` |
| 2026-11-02 | ST12 design | 09:03–10:11 | 1.0 | Stretch | Human-in-the-loop design from the pursuit lead's chair: three rounds (two modes, then one mode), roadmap entry with five sub-steps, D43 |
| 2026-11-02 | ST2, ST13, ST12a (parallel) | 10:11–11:38 | 1.0 | Stretch | ST2 VLM transcription of escalated pages, 15 tests, two ablations ($1.0), D42; ST13 one structure for all prompts, structure test, baseline rejudged and new-prompt eval runs (about $12 judge), D51, F17; ST12a checkpoint in the pipeline, pause and resume, CLI `checkpoint`, 24 tests, D44, D45 |
| 2026-11-02 | ST12b | 11:38–14:10 | 2.5 | Stretch | Planning the revise loop 1.75, then the revise primitive and versioning: versions module, four revise agents and prompts, refine orchestration, CLI `revise`/`regenerate`/`sign-off`/`history`, 31 tests, live Missouri loop fixed a stale-flag bug, roadmap moved to `docs/hitl/`, D46, D47 |
| 2026-11-02 | ST12c | 14:10–14:48 | 0.5 | Stretch | Backend for the human loop: eight run states, checkpoint/revise/regenerate/sign-off endpoints, SSE state events, restart adoption, 9 tests, live loop through the API, D48 |
| 2026-11-02 | ST12d | 14:48–15:17 | 0.5 | Stretch | Frontend checkpoint: Checkpoint tab, brief preview, lifecycle banner, versioned refetch, 16 Vitest tests, live checkpoint through the UI, D49 |
| 2026-11-02 | ST12e | 15:17–15:56 | 0.75 | Stretch | Frontend refine and sign-off: Suggest edits panel, version bar and stale banner, Review tab with history and diffs, 9 Vitest tests, live loop with Playwright, D50 |
| 2026-11-02 | ST12 sync | 15:56–16:15 | 0.25 | Stretch | Renumbered ST12 decisions to D43–D50 and merged `main` (ST2) into `hitl` |
| 2026-11-03 | Merges into `main` | 08:15–08:51 | 0.75 | Stretch | `hitl` merged into `main`; `main` merged into `prompt-structure` (pursuit-guidance rule carried into the restructured prompts, ST12 renumbered ST13, D43 to D51) and merged |
| 2026-11-03 | ST13 README | 08:51–09:24 | 0.5 | Stretch | `evals.harness chart` (SVG dumbbell chart, light and dark), old vs. new prompts chart and table in the README, 3 tests |
| 2026-11-03 | Remove runs | 09:24–09:39 | 0.25 | Stretch | `DELETE /api/runs/{id}` and a two-click Remove control on own runs, 4 backend tests, Playwright check, D52 |
| 2026-11-03 | README reshape | to 13:45 | 0.5 | Stretch | README reshaped for reviewers with the readme-writing skill, vision-model chart, docs/EVALUATION.md and docs/REPOSITORY.md |
| 2026-11-03 | Demo | — | 0.5 | 6 | Demo recorded |
| 2026-11-03 | Time log | — | — | 5 | This file rewritten from git timestamps after an interview with the author |
