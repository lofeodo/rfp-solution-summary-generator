# TIMELOG.md

Rough hours per part, as the assignment asks. Two views: per deliverable (what the
reviewer wants) and per roadmap step (how the work actually happened). Update both at
the end of every step. Times are estimates to the nearest half hour.

## Per deliverable

| Deliverable | Hours | Notes |
|---|---|---|
| 0. Reading, research, planning | 4.0 | 3.0 assignment + public RFPs + brainstorming; 1.0 input inspection, roadmap, working rules |
| 1. Working app (pipeline, parsing, agents, CLI) | 12.5 | S0 scaffold: env, config, schemas, tests, CI; S1 LLM layer; S9 assembler and renderer; S2 parsing 2.0; S4 parse-quality pass 1.0; S3 splitting 1.5; S6 problem statement 1.0; S5 requirements extractor 2.0; S7 solution generator with coverage loop 1.0; S10 pipeline graph, CLI, four live runs 1.0 |
| 2. Prompt assets and notes | 4.0 | S11 gold drafting prompts and notes; S4 parse_quality prompt and notes; S6 problem prompts, live runs and notes; S5 extraction and dedupe prompts, one tuning round, notes 1.0; S7 solution prompt, live runs on four RFPs, one tuning round, notes 1.0; S12 seven judge prompts, one tuning round, notes 0.5 |
| 3. Evaluation harness and sample results | 4.75 | S11 gold labels: format, labelling script, drafts, correction of 265 items; S12 harness, scripted-judge tests, 8 fresh runs, 12 judged runs, hand-labelled agreement sample 2.25 |
| 4. Observability | 1.75 | S1 run recorder, cost, Langfuse handler; S10 stage records, stage events, per-stage cost 0.5; S12 retry cause in the run log (F7), judge cost logs 0.25 |
| 5. DECISIONS.md and other docs | 3.0 | S0 plan, decisions, README skeleton; S9 plan and D16; S6 plan, D28, F6, F7; S7 plan, D32, F10, F11 0.5; S10 plan, D34, README run section 0.5; S12 plan, D36, D37, F13, F14, results README 0.5 |
| 6. Demo | | |
| UI (part of 1, tracked separately) | 3.5 | S14 backend: API, run queue, SSE, tests, live run, API contract, D35; S15 frontend: views, source reveal, live timeline, Playwright passes, live run, D38 2.0 |
| **Total** | **33.5** | |

## Per step

| Date | Step | Hours | Deliverable | Notes |
|---|---|---|---|---|
| 2026-10-29 | — | 3.0 | 0 | Read assignment, studied public RFPs, brainstormed the solution |
| 2026-10-30 | Planning | 1.0 | 0 | Inspected the four RFPs, surfaced assignment points, wrote ROADMAP, CLAUDE.md, living docs |
| 2026-10-30 | S0 | 1.5 | 1, 5 | Scaffold: conda env, pins, config, schemas, tests, CI, README skeleton, docs |
| 2026-10-30 | S1 | 2.0 | 1, 4 | LLM factory, structured_call with retry, prompt loader, run recorder, Langfuse, live DeepSeek fix (thinking mode) |
| 2026-10-30 | S9 | 1.5 | 1, 5 | Assembler with citation check, markdown renderer, golden tests, D16 |
| 2026-10-30 | S2 | 2.0 | 1 | PDF parsing: inspection of the four RFPs, normaliser, header strip, flags, references, tests, docs |
| 2026-10-30 | S11 | 3.0 | 2, 3 | Gold format and script, Claude drafts ($1.6), F4/F5 fixes, correction of all four RFPs, Federal Way image table by hand |
| 2026-10-30 | S4 | 1.5 | 1, 2 | Parse-quality judge, attribution rule, VLM hook, fake-model tests, live run on four RFPs ($0.005), D24 |
| 2026-10-30 | S3 | 1.5 | 1 | Splitting: outline located in text, heading promotion, 300-word chunks with overlap, kind tags, invariant and golden tests, D25 to D27 |
| 2026-10-30 | S6 | 2.0 | 1, 2, 5 | Problem statement: per-chunk summaries in a thread pool, schema-validated citations, full-text baseline, debug CLI, live runs on four RFPs in both modes ($0.25), .gitattributes LF fix, D28 |
| 2026-10-30 | S5 | 3.0 | 1, 2 | Requirements extractor: verified calls with feedback, exact and LLM-grouped dedupe with sanitised fallback, single-call mode, concurrency, 23 fake-model tests, two prompts tuned after a live run, five live runs on the four RFPs ($0.25), D29 to D31, F8, F9 |
| 2026-10-30 | S7 | 2.5 | 1, 2, 5 | Solution generator: no RFP text, citations checked in the schema, code-computed coverage, LangGraph generate/check/revise loop with a round cap, debug CLI, 23 fake-model tests, live runs on four RFPs twice (first prompt and tuned prompt, $0.45 including S5 and S6 inputs), D32, F10, F11 |
| 2026-10-30 | S8 | 2.5 | 1, 2, 5 | Risk assessor: code-computed findings block, must-cite and count band in the schema, sort-then-number, debug CLI with the S4 pass, 18 fake-model tests, live runs on four RFPs twice ($0.08), D33, F12 |
| 2026-10-30 | S10 | 2.0 | 1, 4, 5 | Pipeline graph with the S5/S6 fan-out, stage wrappers with events and stage records, run CLI with ablation flags, 13 stubbed-stage tests, live runs on four RFPs, committed samples, D34 |
| 2026-10-30 | S14 | 1.5 | UI, 5 | UI backend: FastAPI app over run_pipeline, one-worker queue, condition-backed SSE, samples served as runs, stubs shared with the graph tests, 27 tests, one live run through the API ($0.05), API contract, D35 |
| 2026-10-30 | S12 | 3.5 | 2, 3, 4, 5 | Eval harness: code-then-judge gold matching, per-item precision, grounding (entity check plus cited-text judge), checklist, solution rubric and judged coverage, risk levels and findings, consistency, pairwise, agreement; F7 fix; 30 scripted-judge tests; 8 fresh runs and 12 judged runs ($0.56 generation, about $6.1 judge including the calibration rescore); 40 hand labels; D36, D37, F13, F14 |
| 2026-10-30 | S15 | 2.0 | UI, 5 | UI frontend: Vite/React/TS/Tailwind app over the S14 API, live SSE timeline, six output tabs, citation chips with a source slide-over (quote highlight, PDF at page), 11 Vitest tests on real sample data, CI job, four Playwright MCP passes at desktop and phone width, one live run through the UI ($0.06), D38, F15 |
