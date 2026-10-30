# TIMELOG.md

Rough hours per part, as the assignment asks. Two views: per deliverable (what the
reviewer wants) and per roadmap step (how the work actually happened). Update both at
the end of every step. Times are estimates to the nearest half hour.

## Per deliverable

| Deliverable | Hours | Notes |
|---|---|---|
| 0. Reading, research, planning | 4.0 | 3.0 assignment + public RFPs + brainstorming; 1.0 input inspection, roadmap, working rules |
| 1. Working app (pipeline, parsing, agents, CLI) | 2.0 | S0 scaffold: env, config, schemas, tests, CI; S1 LLM layer |
| 2. Prompt assets and notes | | |
| 3. Evaluation harness and sample results | | |
| 4. Observability | 1.0 | S1 run recorder, cost, Langfuse handler |
| 5. DECISIONS.md and other docs | 0.5 | S0 plan, decisions, README skeleton |
| 6. Demo | | |
| UI (part of 1, tracked separately) | | |
| **Total** | **7.5** | |

## Per step

| Date | Step | Hours | Deliverable | Notes |
|---|---|---|---|---|
| 2026-10-29 | — | 3.0 | 0 | Read assignment, studied public RFPs, brainstormed the solution |
| 2026-10-30 | Planning | 1.0 | 0 | Inspected the four RFPs, surfaced assignment points, wrote ROADMAP, CLAUDE.md, living docs |
| 2026-10-30 | S0 | 1.5 | 1, 5 | Scaffold: conda env, pins, config, schemas, tests, CI, README skeleton, docs |
| 2026-10-30 | S1 | 2.0 | 1, 4 | LLM factory, structured_call with retry, prompt loader, run recorder, Langfuse, live DeepSeek fix (thinking mode) |
