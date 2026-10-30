# ROADMAP.md

**This file is the only memory between sessions.** Read it first. Each step is one PR.
Follow the per-step loop in `CLAUDE.md`. Fill in "Detailed plan" when a step starts;
fill in "What was done", "Deviations from plan", "Open issues" when it ends.

Status values: `todo` · `in progress` · `done` · `dropped`.

---

## 0. Project summary (for sessions with cleared context)

36-hour take-home for an AI Engineer (LLM Apps and MLOps) role. Build an LLM/agent
app that ingests the RFP brief in `inputs/` and produces a structured solution summary
(requirements, approach, risks), as a real agentic workflow with an evaluation harness
and observability (tokens, latency, cost). Deliverables: working app plus README,
prompt assets with notes, eval harness with sample results, observability, DECISIONS.md,
3 to 5 minute demo. Also ASSUMPTIONS.md and a rough time log per part. Grading: agentic
depth 30%, eval and observability 20%, LLMOps fluency 15%, craft 15%, communication
10%, novelty 10%. The author defends every decision in a live 60-minute follow-up with a
small live change. **Doing less, cleanly, beats a sprawling half-build.**

Inputs: no brief was provided, so public RFPs stand in (see `docs/ASSUMPTIONS.md`).
Primary brief `data/rfps/missouri.pdf` (copied to `inputs/rfp_brief.pdf`); eval set
adds `NYESD.pdf`, `colfax.pdf`, `federal_way.pdf`. All four are text-native, 4k to 10k
words, fit one context window, have tables that pymupdf4llm renders correctly. Two have
PDF outlines, two do not. Missouri pages 19 to 20 are blank scanned forms; Federal Way
page 5 holds a requirements table as an image.

### Architecture (decided)

```mermaid
flowchart LR
    PDF[RFP PDF] --> P0[0. Parse PDF to markdown<br/>+ flag pages, links, images, referenced docs]
    P0 --> P1[1. Split: sections and citable chunks<br/>stable IDs S3.2]
    P1 --> P2[2. Requirements extractor<br/>per chunk, validated, deduped]
    P1 --> P3[3. Problem statement<br/>hierarchical summaries]
    P2 --> P4[4. Solution generator]
    P3 --> P4
    P4 --> P5[5. Risk assessor]
    P2 --> P5
    P3 --> P5
    P5 --> P6[6. Assemble JSON, render markdown]
```

Framework LangGraph. Generator DeepSeek, judge Claude, provider and model one config
setting. Keys only in `.env`.

**Traceability rule (steps 2 to 5).** Factual assertions about the client or project
cite the chunk ID that supports them, or are labelled as inferences with the chunk IDs
they come from, or are dropped. Judgments (design choices, severities, mitigations)
need no support but cite the requirement or chunk IDs they respond to. Citations are
IDs, not quotes, except requirements, which keep a verbatim quote verified by string
match. Code checks that every cited ID exists.

**Agentic decision points (minimum).** Validate-and-retry with error feedback on every
structured output; quality-flag escalation in parsing (code flags, LLM confirms, VLM
hook); dedupe grouping with assertion. Critic, revision loop, ReAct are stretch and
only added if evals show a weakness they would fix.

### Repo layout (target)

```
CLAUDE.md  README.md  requirements.txt  .env.example  Dockerfile  pyproject.toml
inputs/rfp_brief.pdf          default input (copy of data/rfps/missouri.pdf)
data/rfps/*.pdf               the four public RFPs (committed)
src/rfp_agent/
  config.py  schemas.py  llm.py  observability.py  graph.py  cli.py
  parsing/   splitting/  agents/{requirements,problem,solution,risk}.py  render/
prompts/<agent>.md            one prompt file per agent
evals/  gold/  results/  harness code
ui/backend (FastAPI)  ui/frontend (Vite + React + Tailwind)
runs/                         local JSON run logs (gitignored except samples/)
tests/
docs/ROADMAP.md DECISIONS.md ASSUMPTIONS.md TIMELOG.md PROMPTS.md
```

---

## 1. Dependency graph

```mermaid
flowchart TD
    S0[S0 Scaffold] --> S1[S1 LLM layer + observability]
    S0 --> S2[S2 PDF parsing]
    S0 --> S9[S9 JSON assembly + markdown renderer]
    S0 --> S11[S11 Gold labels]
    S2 --> S3[S3 Splitting]
    S1 --> S4[S4 Parse quality pass]
    S2 --> S4
    S1 --> S5[S5 Requirements extractor]
    S3 --> S5
    S1 --> S6[S6 Problem statement]
    S3 --> S6
    S5 --> S7[S7 Solution generator]
    S6 --> S7
    S7 --> S8[S8 Risk assessor]
    S4 --> S10[S10 Graph wiring + CLI]
    S8 --> S10
    S9 --> S10
    S2 --> S11
    S10 --> S12[S12 Eval harness]
    S11 --> S12
    S12 --> S13[S13 Ablations + fixes]
    S10 --> S14[S14 UI backend]
    S14 --> S15[S15 UI frontend]
    S13 --> S16[S16 Docs, Dockerfile, demo script]
    S15 --> S16

    classDef done fill:#d4edda,stroke:#2e7d32,color:#1b5e20
    classDef ready fill:#fff3cd,stroke:#b8860b,color:#5c4400
    class S0,S1,S2,S3,S4,S5,S6,S9,S11 done
    class S7 ready
```

**Progress (2026-10-30):** done S0, S1, S2, S3, S4, S5, S6, S9, S11 (green). Ready
now, all dependencies done (amber): S7. Update the two `class` lines in
the diagram whenever a step is marked `done`.

| Step | Depends on | Can run in parallel with | Main files touched |
|---|---|---|---|
| S0 Scaffold | — | — (must land first) | everything top-level, `schemas.py`, `config.py` |
| S1 LLM layer + observability | S0 | S2, S9, S11 | `llm.py`, `observability.py`, `config.py` (pricing) |
| S2 PDF parsing | S0 | S1, S9, S11 | `parsing/` |
| S3 Splitting | S2 | S1, S4, S9, S11 | `splitting/` |
| S4 Parse quality pass | S1, S2 | S3, S5, S6, S9, S11 | `parsing/quality.py`, `prompts/parse_quality.md` |
| S5 Requirements extractor | S1, S3 | S4, S6, S9, S11 | `agents/requirements.py`, `prompts/requirements*.md` |
| S6 Problem statement | S1, S3 | S4, S5, S9, S11 | `agents/problem.py`, `prompts/problem*.md` |
| S7 Solution generator | S5, S6 | S4, S9, S11 | `agents/solution.py`, `prompts/solution.md` |
| S8 Risk assessor | S7 | S4, S9, S11 | `agents/risk.py`, `prompts/risk.md` |
| S9 JSON assembly + markdown renderer | S0 | S1 to S8, S11 | `render/` |
| S10 Graph wiring + CLI | S4, S8, S9 | S11 | `graph.py`, `cli.py` |
| S11 Gold labels | S2 | S1, S3 to S10 | `evals/gold/` |
| S12 Eval harness | S10, S11 | S14 | `evals/` |
| S13 Ablations + fixes | S12 | S14, S15 | prompts, agents, `evals/results/` |
| S14 UI backend | S10 | S12, S13 | `ui/backend/` |
| S15 UI frontend | S14 | S12, S13 | `ui/frontend/` |
| S16 Docs, Dockerfile, demo script | S13, S15 | — | `README.md`, `Dockerfile`, `docs/` |

Parallel work rule: two agents may run concurrently only on steps listed as parallel
with each other, and must not edit each other's "main files". Shared files
(`schemas.py`, `config.py`, `requirements.txt`, `README.md`) are edited only with a
one-line note in the step's "What was done" so merges are easy to resolve.

---

## 2. Core steps

### S0. Scaffold
- **Status:** done
- **Goal:** the common foundation every other step builds on: repo layout, conda env and
  pinned `requirements.txt`, `config.py` (provider/model single setting, paths, pricing
  table stub), Pydantic v2 `schemas.py` for every pipeline artefact (ParsedDocument with
  pages, tables, images, referenced_documents, flags; Section; Chunk with stable ID,
  section path, page; Requirement with ID, text, type, strictness, quote, chunk IDs;
  Ambiguity; ProblemStatement with cited claims; Solution with requirement coverage;
  Risk with severity, likelihood, justification, IDs; RunLog with per-node tokens,
  latency, cost), `.env.example`, GitHub Actions CI (ruff + pytest), `prompts/`
  directory with a README, `inputs/rfp_brief.pdf` copied from `data/rfps/missouri.pdf`
  (the four RFPs are already committed under `data/rfps/`), README skeleton with the
  pipeline diagram, `tests/` with a schema round-trip test. The agent creates the
  `rfp-solution-gen` conda env itself. Create the `core` branch.
- **Depends on:** —
- **Parallel with:** — (lands first)
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** generator default `deepseek:deepseek-flash`
    (DeepSeek V4.1 Flash; `deepseek-chat` is no longer on DeepSeek's pricing page);
    judge default `anthropic:claude-sonnet-5-5`; requirement `type` enum = functional,
    technical, security_compliance, legal_contractual, timeline, budget_pricing,
    submission, other; `strictness` = mandatory, desired, optional; risk `severity` and
    `likelihood` both low/medium/high.
  - **Branch:** `step-00-scaffold` off `core` as a worktree; one commit per unit below;
    PR into `core`.
  - **Packaging:** `pyproject.toml` (setuptools, `src/` layout, ruff and pytest config,
    `llm` marker skipped by default), `requirements.txt` with exact pins plus `-e .` so
    one `pip install -r requirements.txt` installs the package editable. Conda env
    `rfp-solution-gen` (Python 3.12) created by the agent.
  - **`config.py`:** pydantic-settings `Settings` (`RFP_` prefix, `.env`): `model`,
    `judge_model` as `provider:model_id` strings, `temperature`, `max_structured_retries`,
    the two S10 ablation flags (`full_text_problem`, `single_call_extraction`), API keys
    and Langfuse keys under their conventional unprefixed names; `split_model_spec()`;
    `langfuse_enabled`; path constants; `ModelPricing` + `PRICING` stub (DeepSeek peak
    rates, Claude opus/sonnet/haiku 5.5) + `pricing_for()`. Cost arithmetic is S1's.
  - **`schemas.py`:** Pydantic v2, `extra="forbid"`, StrEnums for every closed set, ID
    formats enforced by regex (`S3.2` chunk, `S3` section, `R001`, `A01`, `G01`, `C01`,
    `K01`). Models: parsing (`Page`, `Table`, `ImageBlock`, `ReferencedDocument`,
    `PageFlag`, `OutlineEntry`, `ParsedDocument`), splitting (`Chunk`, `Section`,
    `SplitDocument`), `Claim(text, kind=fact|inference, chunk_ids>=1)`, requirements
    (`Requirement` with quote, `chunk_ids`, `quote_verified`, `merged_from`,
    `conflicts_with`; `Ambiguity`; `Gap`; `RequirementsOutput`), problem (`ChunkSummary`,
    `ProblemStatement` as four lists of `Claim`), solution (`SolutionComponent` citing
    requirement IDs, `Coverage` computed by code, `Solution`), risk (`Risk`,
    `RiskAssessment`), final `SolutionSummary` with `ChunkRef` index for rendering,
    observability (`NodeMetrics`, `Escalation`, `RunLog.totals()`), and
    `validate_ids_exist()` for the agents.
  - **Skeleton:** `src/rfp_agent/{parsing,splitting,agents,render}/__init__.py`,
    `prompts/README.md` (one file per agent, `{{name}}` placeholders), `inputs/rfp_brief.pdf`
    copied from Missouri, `runs/samples/.gitkeep`, `.env.example`, GitHub Actions CI
    (ruff check, ruff format --check, pytest on Python 3.12), README skeleton with the
    pipeline diagram.
  - **Tests:** `tests/test_schemas.py` (round-trip of a full `SolutionSummary` and
    `RunLog`, ID regexes, forbid-extra, `validate_ids_exist`, totals) and
    `tests/test_config.py` (defaults, model spec parsing, env override, pricing lookup).
  - **Docs:** DECISIONS D13 to D15 (model ids and pricing source, schema conventions,
    install and config mechanics), TIMELOG row, ASSUMPTIONS line on peak pricing.
- **What was done:** (branch `step-00-scaffold`, PR into `core`)
  - Conda env `rfp-solution-gen` (Python 3.12) created; `requirements.txt` pins
    langgraph 1.2.18, langchain 1.4.7, langchain-core 1.7.3, langchain-deepseek 1.1.1,
    langchain-anthropic 1.7.7, langfuse 5.0.4, pymupdf4llm 1.28.2, pymupdf 1.28.2,
    pydantic 2.14.2, pydantic-settings 2.16.2, python-dotenv 1.2.4, typer 0.27.3,
    rich 15.0.0, pytest 9.2.0, ruff 0.17.3, and `-e .` (editable install of the package).
  - `pyproject.toml`: setuptools `src/` layout; ruff (line 100, py312, E/F/I/UP/B);
    pytest (`testpaths=tests`, `llm` marker, `addopts=-m 'not llm'`).
  - `src/rfp_agent/config.py`: `Settings` (pydantic-settings, `RFP_` prefix, reads
    `REPO_ROOT/.env`): `model`, `judge_model`, `temperature`, `max_structured_retries`,
    `full_text_problem`, `single_call_extraction`, provider keys and Langfuse keys under
    their unprefixed names; `generator`/`judge` properties; `langfuse_enabled`;
    `split_model_spec()`; path constants; `ModelPricing`, `PRICING`, `pricing_for()`;
    `get_settings()` (lru_cache).
  - `src/rfp_agent/schemas.py`: as planned. Extra helpers beyond the plan:
    `STRICTNESS_RANK` (for S5's keep-the-stricter merge), `SplitDocument.chunk_by_id()`,
    `RequirementsOutput.requirement_ids()/mandatory()`, `ProblemStatement.claims()`,
    `ParsedDocument.page_count`, `RunTotals` model returned by `RunLog.totals()`.
  - Empty packages `parsing/`, `splitting/`, `agents/`, `render/`; `prompts/README.md`;
    `inputs/rfp_brief.pdf`; `runs/samples/.gitkeep`; `.env.example`;
    `.github/workflows/ci.yml` (ruff check, ruff format --check, pytest on 3.12);
    README skeleton with the pipeline diagram and quickstart.
  - Tests: `tests/test_schemas.py` (10 tests incl. 9 parametrised bad-ID cases) and
    `tests/test_config.py`; 29 pass, ruff clean. Shared files touched: all of them
    (this is the scaffold).
- **Deviations from plan:**
  - `pymupdf4llm==2.0` and `pymupdf==2.0` on PyPI are empty placeholder releases
    (dist-info only, no modules). Pinned both to 1.28.2 and added `pymupdf` as a
    direct dependency since S2 will call it for links and images.
  - Status set to `done` in the same commit as the docs, before the PR is opened,
    to avoid a second docs-only commit on the branch.
- **Open issues:**
  - `langchain-openai` arrives transitively via `langchain-deepseek`; harmless, not pinned.
  - langchain/langgraph 1.x APIs: S1 must verify `init_chat_model("deepseek:...")`
    resolves to `langchain_deepseek` in these versions.
  - DeepSeek peak vs off-peak pricing: `PRICING` holds peak; S1 may add a time-aware
    rate if cost accuracy matters for the eval tables.

### S1. LLM layer and observability core
- **Status:** done
- **Goal:** `llm.py`: chat-model factory from config (DeepSeek default, Claude and any
  LangChain model swappable), a `structured_call()` helper that enforces a Pydantic
  schema with bounded retry feeding the validation error back, and records the retry
  count. `observability.py`: per-run JSON log under `runs/` with per-node input/output
  tokens, latency, cost from the pricing table (cache tokens if the provider reports
  them), model ID, temperature, prompt file hashes; Langfuse callback handler wired
  through LangChain and a no-op when keys are absent. Unit tests with a fake model.
- **Depends on:** S0
- **Parallel with:** S2, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** `structured_call` uses provider-native
    `with_structured_output(include_raw=True)` inside a bounded retry loop (not code-side
    JSON parsing); one `NodeMetrics` per logical LLM call (retries included), tagged with
    the node, aggregated in code; `.env` created with empty placeholders, live smoke test
    `@pytest.mark.llm` self-skips without a key; cost is a simple upper bound (peak
    DeepSeek rates, cache reads at the cached rate, cache writes at the input rate,
    unknown model costs 0 with a warning).
  - **Verified library facts:** `init_chat_model("deepseek:...")` builds `ChatDeepSeek`
    with kwargs unfiltered; `ChatDeepSeek` raises at construction without a key and both
    providers read keys from `os.environ` only, so the factory passes `api_key` from
    `Settings`; `ChatAnthropic` raises for Sonnet 5.5 / Fable 5 if temperature is set, so
    temperature goes to non-Anthropic providers only; DeepSeek rewrites `json_schema` to
    `function_calling`, where no tool call gives `parsed=None, parsing_error=None`;
    Anthropic uses `method="json_schema"`; both report `usage_metadata` with
    `input_token_details.cache_read`; Langfuse without keys is a no-op but
    `get_trace_url()` raises, so it is guarded.
  - **Branch:** `step-01-llm-observability` off `core` as a worktree; one commit per unit.
  - **`config.py` (shared):** `max_output_tokens` (None = provider default),
    `request_timeout_s` (120), `llm_transport_retries` (2, SDK-level 429/5xx retries,
    distinct from `max_structured_retries`); `.env.example` updated.
  - **`llm.py`:** `get_chat_model(spec=None, settings=None, **overrides)`,
    `get_judge_model()`, `MissingApiKeyError`; `structured_method(model)` (json_schema
    for Anthropic, function_calling otherwise); `structured_call(model, schema, messages,
    node=..., recorder=None, max_retries=None, config=None) -> StructuredResult` that
    appends the bad AIMessage plus a HumanMessage with the validation error and retries,
    refuses to retry a truncated output (`finish_reason == "length"` /
    `stop_reason == "max_tokens"`), raises `StructuredOutputError` with all attempts on
    exhaustion, and records one `NodeMetrics`; `load_prompt(name) -> Prompt` with
    `{{var}}` rendering (missing or unused variables are errors) and SHA-256 recorded on
    the active run.
  - **`observability.py`:** `estimate_cost()`, `usage_from_message()`, `new_run_id()`,
    `RunRecorder` (holds the `RunLog`; `record`, `record_prompt`, `record_escalation`,
    `per_node()`, `finish()`, `write()` to `runs/<run_id>/run_log.json`, `activate()`
    context manager setting a contextvar so nodes need no plumbing),
    `current_recorder()`; `make_langfuse_handler()`, `langfuse_trace_url()`,
    `shutdown_langfuse()`, all no-ops without keys and without importing `langfuse`.
  - **Tests:** scripted fake chat model; structured-call retry paths (success, bad args,
    no tool call, exhaustion, truncation, recording); factory per provider; prompt
    loader; cost arithmetic, recorder round-trip, Langfuse on/off; live smoke test
    marked `llm`.
  - **Docs:** DECISIONS D17 to D19, TIMELOG, ASSUMPTIONS (cache-write pricing), README
    configuration and observability sections.
- **What was done:** (branch `step-01-llm-observability`, PR into `core`)
  - `src/rfp_agent/llm.py`: `get_chat_model(spec=None, settings=None, thinking=None,
    **overrides)` builds any LangChain provider through `init_chat_model`, wiring the key
    from `Settings` (raises `MissingApiKeyError` naming the env var), timeout, transport
    retries, optional `max_tokens`; temperature is sent to every provider except
    Anthropic; DeepSeek gets `extra_body={"thinking": {"type": ...}}` from
    `Settings.deepseek_thinking` or the `thinking` argument. `get_judge_model()`.
    `model_spec_of(model)` (`provider:model_id` for logs and pricing).
    `structured_method(model)`: `json_schema` for Anthropic, `json_mode` for DeepSeek with
    thinking on, `function_calling` otherwise. `structured_call(model, schema, messages,
    node=..., settings=None, recorder=None, max_retries=None, config=None)` returns
    `StructuredResult(value, metrics, attempts)`; on failure it appends the model's reply
    plus feedback (a `ToolMessage` per tool call, else a `HumanMessage`) carrying the
    validation error (capped at 2000 chars) and retries; a missing structured output gets
    a fixed "no structured output" message; a reply cut by the output cap raises
    `StructuredOutputError(truncated=True)` without retry; exhaustion raises
    `StructuredOutputError` with every attempt. In JSON mode the schema is inserted as a
    system message after the caller's system messages. One `NodeMetrics` (summed tokens
    over attempts, cost, wall latency, `retries`) is recorded per call, on success and on
    failure. `load_prompt(name) -> Prompt(name, path, text, sha256)` with
    `Prompt.render(**vars)` (`{{var}}`; missing and unused variables raise) and the hash
    recorded on the active run.
  - `src/rfp_agent/observability.py`: `estimate_cost()` (cached input at the cached rate,
    unknown model costs 0 and warns once), `usage_from_message()`, `new_run_id()`
    (`YYYYMMDD-HHMMSS-<6 hex>`), `RunRecorder` (`log: RunLog`, `run_dir`, `record`,
    `record_prompt`, `record_escalation`, `set_trace_url`, `totals`, `per_node`, `finish`,
    `write` to `runs/<run_id>/run_log.json`, `activate()` context manager that sets the
    current recorder and writes the log on exit even if the run raises,
    `from_settings()`), `current_recorder()`; `make_langfuse_handler()`,
    `langfuse_trace_url()`, `shutdown_langfuse()`: no-ops without keys and never import
    `langfuse` then; the trace-URL lookup never raises.
  - `config.py` (shared file): `max_output_tokens`, `request_timeout_s`,
    `llm_transport_retries`, `deepseek_thinking`; `.env.example` lists them. Local `.env`
    created from `.env.example` with empty keys for the author to fill in.
  - Tests: `tests/fakes.py` (`ScriptedChatModel`, `tool_call_msg`, `text_msg`),
    `test_llm_structured.py`, `test_llm_deepseek_modes.py`, `test_llm_factory.py`,
    `test_prompts.py`, `test_observability.py`, `test_config.py` extended: 67 unit tests
    pass, ruff clean. `test_llm_live.py` (`-m llm`): DeepSeek Flash with thinking off and
    on both pass live (about $0.0002 per call, 1 to 1.5 s); the Claude test skipped (no
    `ANTHROPIC_API_KEY` yet).
- **Deviations from plan:**
  - Added `Settings.deepseek_thinking` (default off) and a `json_mode` structured method.
    The first live call failed with DeepSeek's 400 "Thinking mode does not support this
    tool_choice": thinking is on by default for `deepseek-flash` and LangChain's
    tool-calling structured output forces the tool. Both fixes were probed live (see
    DECISIONS D17 and F1).
  - Retry feedback is a `ToolMessage` per tool call rather than always a `HumanMessage`:
    both APIs reject a conversation with an unanswered tool call.
  - `NodeMetrics` is also recorded when a call exhausts its retries, so failed calls
    still show their cost.
  - Each module was committed with its tests instead of a separate tests commit, so every
    commit is green.
- **Open issues:**
  - The conda env's editable install still points at the deleted `step-00-scaffold`
    worktree, so `import rfp_agent` from a fresh shell fails until
    `pip install -e .` is re-run from the main checkout. This step ran everything with
    `PYTHONPATH=src`. CI is unaffected.
  - Claude path not yet exercised live (`json_schema` method via `output_config`);
    run `pytest -m llm` once `ANTHROPIC_API_KEY` is in `.env` (S11/S12 need it anyway).
  - Thinking on vs off for DeepSeek is a quality question for S13: off is the cheap
    default; S7 and S8 can pass `thinking=True` per model if evals show a benefit.
  - S10 wraps the graph run in `RunRecorder.activate()` and passes
    `make_langfuse_handler()` in `config["callbacks"]`; LangGraph propagates it to calls
    inside nodes.

### S2. PDF parsing (library path)
- **Status:** done
- **Goal:** `parsing/`: pymupdf4llm to markdown per page with tables kept as markdown
  tables; use the PDF outline when present. Code heuristics flag suspicious pages (low
  word count, large image blocks, broken table rows, fragmented lines) into a
  `flags` list with the reason. Extract every hyperlink (annotation and plain-text URL)
  and every reference to an attachment, appendix, exhibit, schedule or addendum, with
  the section it appears in, into `referenced_documents`. Record image blocks per page
  (page, size, nearby caption). Unicode normalisation (curly quotes, split URLs inside
  table cells). Output a `ParsedDocument`. Tests on all four RFPs with assertions on
  page count, table count, known flags (Missouri p19 to 20, Federal Way p5) and known
  references (Colfax Attachments A to G). Leave a `escalate(page)` hook stub for S4.
- **Depends on:** S0
- **Parallel with:** S1, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** a referenced document is `present` only when
    a matching heading exists and its section body has at least 40 words; the four-RFP
    tests always run (one session-scoped parse per file, about 45 s); repeated page
    headers and footers are stripped; `mailto:` links are not recorded.
  - **Findings that shape the design** (pymupdf4llm 1.28.2): `to_markdown(page_chunks=True)`
    returns per-page `text` plus layout `page_boxes` (classes text, section-header,
    list-item, table, picture, page-header, page-footer, each with bbox and char span);
    no separate tables or images keys. About 10 s per document. Merged-cell tables render
    as one column with `<br>`-joined cells (Missouri p12, Federal Way p14). Bold URLs split
    inside table cells (Missouri p6). Real link targets live only in link annotations.
  - **Branch:** `step-02-pdf-parsing` off `core`; PR into `core`.
  - **Files:** `parsing/pdf.py` (`parse_pdf`, orchestration), `parsing/normalize.py`
    (NFC, curly quotes and Unicode spaces to ASCII, ligatures, split-URL join, header and
    footer strip), `parsing/heuristics.py` (flag thresholds as constants, table blocks,
    broken-table rules), `parsing/references.py` (hyperlinks from annotations and plain
    text, Attachment/Appendix/Exhibit/Schedule/Addendum regex, section lookup, `present`),
    `parsing/quality.py` (`escalate()` stub for S4), `parsing/__main__.py` (debug dump).
  - **Heuristics:** low word count < 50; picture box >= 25% of page area; broken table =
    ragged pipe counts or a one-column block with `<br>`-merged cells; fragmented lines =
    at least 6 lines of <= 2 words making up >= 50% of prose lines.
  - **Title:** PDF metadata title if most of its words occur on page 1, else the first
    heading on page 1.
  - **Tests:** unit tests on literal strings for every rule; four-RFP tests for page,
    outline and table counts, known flags (Missouri p12, p19, p20; Federal Way p5, p14;
    NYESD none), image sizes and captions, references (Colfax A to G with E/F/G absent,
    NYESD Schedule A and Appendix A/B, Missouri Exhibits and the joined MoDOT URL), no
    curly quotes, header stripped, titles.
  - **Docs:** DECISIONS D20 to D22, ASSUMPTIONS lines, TIMELOG row, README parsing section.
- **What was done:** (branch `step-02-pdf-parsing`, PR into `core`)
  - `parsing/pdf.py`: `parse_pdf(path) -> ParsedDocument`. One
    `pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)` call; per page:
    header/footer strip, normalisation, `Page` with `word_count`, `Table` per pipe block,
    `ImageBlock` per image from `get_image_info()` (clipped, >= 20 pt, caption = nearest
    text block within 40 pt above or below), flags, link annotations with anchor text
    (whole words under the link rectangle). Outline from `get_toc()`. Title = metadata
    title if 60% of its words are on page 1, else first heading on page 1.
  - `parsing/normalize.py`: NFC; curly quotes, Unicode spaces and hyphens to ASCII;
    ligatures expanded; soft hyphen and zero-width characters dropped; en/em dashes kept;
    bold URLs split across `<br>` in table cells rejoined; header/footer stripping (see
    D21).
  - `parsing/heuristics.py`: `count_words` (ignores tags, pipes, separator rows),
    `table_blocks`, `broken_table_reason` (ragged, or one-column with `<br>`-merged
    cells), `flag_page`; thresholds are module constants.
  - `parsing/references.py`: `document_lines` (every line tagged with its section:
    nearest heading, else outline entry), `document_references` (regex, first non-TOC
    occurrence), `mark_present` (heading plus >= 40 words), `hyperlinks` (annotation URIs,
    plus plain-text URLs no annotation covers; http(s) only).
  - `parsing/quality.py`: `escalate(page, flags) -> Escalation | None` stub for S4.
  - `parsing/__main__.py`: `python -m rfp_agent.parsing <pdf> [--out file.json]`.
  - Results on the four RFPs (about 5 to 9 s each):

    | RFP | pages | outline | tables | flagged pages | references (present) | links |
    |---|---|---|---|---|---|---|
    | Missouri | 20 | 64 | 8 | 12, 19, 20 | Exhibit A, B (both absent) | 9 |
    | NYESD | 27 | 0 | 2 | none | Schedule A, B; Appendix A, B (all absent) | 32 |
    | Colfax | 22 | 29 | 4 | 1, 2, 3, 20, 21, 22 | Attachments A-D present, E-G absent | 1 |
    | Federal Way | 16 | 0 | 10 | 2, 5, 14 | Exhibit A, B (both present) | 0 |

  - Tests: `tests/test_parsing_units.py` (rules on literal strings) and
    `tests/test_parsing_rfps.py` (one session-scoped parse per RFP); 83 tests pass in
    about 22 s, ruff clean. Shared files touched: none (`README.md` and docs only).
- **Deviations from plan:**
  - Hyperlinks are deduplicated across the document (one entry per URL, at its first
    page) rather than per page: downstream steps want one gap per document, not one per
    mention.
  - Plain-text URLs are suppressed when an annotation anywhere in the document covers
    them, compared on letters and digits only. NYESD's text layer mangles long URLs at
    line breaks (lost hyphens), which otherwise produced seven bogus duplicates (F2).
  - Header/footer stripping needed two extra cases beyond the plan: a repeated header
    merged into the same box as the next heading (prefix removed, heading kept), and a
    header split across two header boxes (Federal Way p7, p9, p11; F3).
  - `escalate()` takes a page and all its flags, not one flag: S4 judges each page once.
  - OCR is passed off explicitly (`use_ocr=False`); the layout path defaults it on (D20).
  - Image captions use the whole nearest text block (Missouri p19's caption block starts
    with a blank line and overlaps the image by one point).
- **Open issues:**
  - Colfax's title comes out as "CITY OF COLFAX" (its first heading); the RFP name is
    in the next two headings. Good enough for display; S9 may prefer the source path.
  - Low-word flags on cover and contents pages (Colfax p1, p3; Federal Way p2) and the
    broken-table flag on Colfax's one-column contents table are expected false
    positives for S4's judge to clear.
  - Section titles can be split across two headings (Missouri "SECTION (1):" then
    "GENERAL DESCRIPTION AND BACKGROUND"); S3 should merge a heading with no body into
    the next.
  - URLs without a scheme (`www.colfax-ca.gov` in text) are not recorded; Colfax's link
    annotation is `http://www.colfax-ca.go/`, a typo in the source, kept as-is.

### S3. Section and chunk splitting
- **Status:** done
- **Goal:** `splitting/`: split on the RFP's own headings (outline first, heading
  detection fallback for documents without an outline), keep the title attached; split
  each section into citable chunks by subsection where present, otherwise by a size cap
  of a few hundred tokens with small overlap. Deterministic stable IDs (`S3.2`), section
  path and page on every chunk. Tag sections narrative vs requirement-bearing by cheap
  heuristics (modal verbs, "shall", numbered lists). Tests: determinism across runs,
  every character of the document lands in exactly one section, chunk size bounds,
  fixtures for both an outlined and a non-outlined RFP.
- **Depends on:** S2
- **Parallel with:** S1, S4, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** 300-word cap (`count_words`), split at
    paragraph boundaries, sentences only inside an over-cap paragraph, tables atomic,
    tail under 50 words merges back, **one-sentence overlap** between consecutive chunks
    of a section (prose only), so coverage is "every body line in at least one chunk";
    **every heading is a Section** (outline subsections included; flat list, `level` and
    `path` give the tree; containers with no own body have zero chunks); short bold-only
    lines are **promoted to headings** when their label matches a numbering scheme an
    existing heading uses; **golden split JSON** for Missouri and NYESD under
    `tests/fixtures/` with `--update-golden`.
  - **Taken without asking:** unlocated outline entries are dropped; text before the first
    heading becomes a synthetic level-1 `Front matter` section; `#` lines over 20 words or
    ending in a period are body text; section IDs number sections in document order
    (`S5` is not the RFP's "Section 5").
  - **Findings that shape the design:** Missouri's outline has 64 entries but only about
    35 render as `#` lines; the rest are bold run-in labels (`**(A) Services:** The
    Offeror shall ...`), so outline titles are located in page text by key prefix; split
    titles (`## SECTION (1):` + `## GENERAL DESCRIPTION ...`, `## Task 1` +
    `## Project Management`); outline entry "Expenses" is a table cell. Federal Way
    "SECTION 4" and NYESD criterion "A." are bold lines, not headings.
  - **Branch:** `step-03-splitting` off `core` as a worktree; PR into `core`. No schema
    change, no new dependency.
  - **Files:** `splitting/headings.py` (markdown headings with demotion and split-title
    merge, outline location in text, bold-line promotion, `detect_headings`),
    `splitting/chunker.py` (blocks, greedy cap fill, sentence split, tail merge, overlap),
    `splitting/kind.py` (modal-verb cue density plus enumerations), `splitting/split.py`
    (`split_document(parsed) -> SplitDocument`), `splitting/__main__.py` (debug dump).
  - **Tests:** unit tests on literal strings for every rule; four-RFP tests for
    determinism, line coverage, size bounds, ID sequence, page ranges, round-trip, known
    sections (Missouri Section (5) with (A) to (Y), no "Expenses"; Colfax Tabs; NYESD X.
    and promoted "A."; Federal Way SECTION 4), kinds; two goldens.
  - **Docs:** DECISIONS D25 to D27, TIMELOG row, ASSUMPTIONS line (words stand in for
    tokens), README splitting section.
- **What was done:** (branch `step-03-splitting`, PR into `core`)
  - `splitting/headings.py`: `Heading(page, line, title, raw_level, consumed, source)`
    where `consumed` lists the title lines removed from the body (empty for a run-in bold
    label, which stays in the body). `markdown_headings` (demotes `#` lines over 20 words,
    ending in a period, not starting with a letter, digit, `(` or `"`, or colon-ended
    with no numbering; merges split titles), `locate_outline` (title key search on the
    entry's page then the next, after the previous match, skipping table rows and
    contents pages; matches a `#` heading, a leading bold run with an optional label
    outside the bold, a whole line, or two bold lines), `promote_bold_lines` (no-outline
    documents only; schemes section, keyword Task/Tab/Exhibit/..., paren, decimal, roman,
    lower roman, letter), `detect_headings`, `heading_paths` (stack on raw levels; a
    contents heading never parents), `title_key`, `scheme_of`.
  - `splitting/chunker.py`: `blocks` (paragraphs on blank lines and page breaks, table
    runs atomic), `chunk_blocks` -> `ChunkText(text, own, page_start, page_end)`
    (greedy 300-word packing, sentence cuts inside an over-cap paragraph, < 50-word tail
    merged back, last sentence of the previous chunk prepended unless it ends in a table
    or is over 60 words), `overlap_of`, `own_text` (strips the overlap, for tests and
    any consumer that needs non-overlapping text), `sentences`.
  - `splitting/kind.py`: `section_kind(text)` requirement-bearing on any obligation cue
    or imperative instruction line, else narrative (D27).
  - `splitting/split.py`: `split_document(parsed) -> SplitDocument`; `Front matter`
    section for text before the first heading; contents-page sections are narrative;
    section `page_end` covers its descendants; `level == len(path)`.
  - `splitting/__main__.py`: `python -m rfp_agent.splitting <pdf> [--out file.json]`
    prints the section tree (id, pages, kind, chunks, words).
  - Results on the four RFPs:

    | RFP | sections | outline located | chunks | mean / max words | requirement-bearing |
    |---|---|---|---|---|---|
    | Missouri | 75 | 63 / 64 | 67 | 82 / 330 | 45 |
    | NYESD | 61 | no outline | 70 | 142 / 322 | 42 |
    | Colfax | 40 | 29 / 29 | 40 | 108 / 293 | 21 |
    | Federal Way | 15 | no outline | 21 | 178 / 362 | 7 |

    (max includes the repeated overlap sentence.)
  - Tests: `tests/test_splitting_units.py` (28 tests on literal strings) and
    `tests/test_splitting_rfps.py` (22 tests: determinism and round-trip, every word of
    every page in exactly one chunk or heading line once the overlap is removed, ID and
    page invariants, size bound, known sections per RFP, kinds, goldens
    `tests/fixtures/split_missouri.json` and `split_NYESD.json`). 210 tests pass, ruff
    clean. Shared files touched: none (README and docs only; README status line also
    lists S11, which had not been added).
- **Deviations from plan:**
  - Section kind uses "any obligation cue" instead of a cue-density threshold: the
    threshold (1.5 per 100 words) left 8 of Missouri's 25 agreement clauses narrative
    because long clauses say "shall" once (D27). Imperative instruction lines
    ("- Describe ...") count as cues so NYESD's selection criteria are caught.
  - Bold-line promotion allows up to 40 words, not 12: NYESD fuses heading "viii." and a
    sub-heading into one 33-word bold line. Promotion still needs a whole-bold line and
    a numbering scheme already in use.
  - Added a lowercase-roman scheme (NYESD "i." to "xiv.") and a numbering label outside
    the bold (`- (Y) **Information Technology:**`, Missouri p17), both found on the RFPs.
  - Colon-ended headings with no numbering ("Name of Respondent:", "Reference 1 :",
    "Submission Deadline:") are treated as form labels; without this, Colfax Attachment
    D's whole body sat under "Name of Respondent:".
  - The coverage test compares word multisets (document words = heading-line words +
    non-overlapping chunk words) rather than lines, because over-cap paragraphs are cut
    mid-line at sentences.
  - Sentence cuts do not split at colons (the plan listed `:`); colons inside RFP prose
    mostly introduce lists.
- **Open issues:**
  - Some front-page lines become one-line sections (Colfax "Shanna Stahl, Administrative
    Services Officer ..."; NYESD "Issued: August 8, 2025"). Harmless for citations;
    S6 may see them as tiny chunks.
  - In documents without an outline, the document title heading (`#`) is the parent of
    every section (NYESD, Federal Way), so paths start with the RFP title.
  - Missouri "(B) Background" is tagged requirement-bearing ("required" appears in the
    background prose); the kind is a hint only.
  - Section numbering `S<n>` changes if parsing changes (a new heading shifts every later
    ID). Gold labels (S11) store quotes, not chunk IDs, so they are unaffected; the
    goldens here will flag any shift.
  - Found while merging S4 (not an S3 change): on a Windows checkout with
    `core.autocrlf=true`, `prompts/parse_quality.md` gets CRLF line endings and
    `load_prompt` reads raw bytes, so `test_quality.py::
    test_page_without_images_and_empty_text_render_placeholders` fails locally (CI on
    Linux passes) and prompt hashes differ by OS. Fix in a later step: a `.gitattributes`
    with `eol=lf` for `prompts/` and fixtures, or newline normalisation in `load_prompt`.

### S4. Parse quality pass (LLM judge of flagged pages, VLM hook)
- **Status:** done
- **Goal:** for pages flagged by S2 heuristics, one LLM call judges whether the page's
  extracted text is usable; pages confirmed bad are passed to a VLM hook that in core
  only records "would escalate" (transcription is stretch). Log for every escalation
  whether code or the model triggered it. Prompt `prompts/parse_quality.md`. Tests with
  a fake model.
- **Depends on:** S1, S2
- **Parallel with:** S3, S5, S6, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** the judge returns two booleans,
    `text_usable` and `content_missing`, plus a page kind, the heuristic flags it
    confirms and a one-sentence reason; a page is bad when its text is unusable or
    content is missing. The pass replaces `ParsedDocument.flags` with the judged flags
    and attributes each escalation by match: `code` when the judge confirms a heuristic
    flag, `model` when it finds a problem no heuristic named. The generator model judges;
    a judge failure keeps the page's flags and the run continues. The prompt is one
    template rendered into one human message (the S11 convention).
  - **Branch:** `step-04-parse-quality` off `core` as a worktree; one commit per unit.
  - **`schemas.py` (shared, Parsing section):** `PageKind` enum; `PageJudgement` (LLM
    output contract, `bad` property); `ParseQualityReport` (judgements by page,
    escalations, judged pages). `Escalation` is unchanged.
  - **`parsing/quality.py`:** `judge_page()` renders `prompts/parse_quality.md` with the
    title, page number and count, flags, images and page markdown, and calls
    `structured_call(node="parse_quality")`, one call per flagged page. `escalate(page,
    flags, judgement, hook)` replaces the S2 stub and applies the attribution rule. The
    VLM hook is a callable `(page, judgement) -> action text`; the default
    `record_only_hook` returns "would escalate to VLM: <reason>" (ST2 swaps in
    transcription). `run_quality_pass(parsed, ...) -> (ParsedDocument, ParseQualityReport)`
    judges each flagged page, records every escalation on the run recorder, and returns a
    copy of the document holding only confirmed and model-raised flags.
  - **Debug CLI:** `python -m rfp_agent.parsing <pdf> --judge` runs the pass and prints
    each judgement.
  - **Tests:** fake-model unit tests for every branch (no flags, cleared, confirmed,
    model-raised, several flags on one page, judge failure, prompt content, recorder,
    custom hook, schema round-trip); a live `llm` test on Federal Way (p5 escalated, p2
    cleared); one live run on all four RFPs for the results table.
  - **Docs:** DECISIONS D24 plus failure modes hit, PROMPTS design note and changelog,
    ASSUMPTIONS (judge sees text only), TIMELOG, README parsing section.
- **What was done:** (branch `step-04-parse-quality`, PR into `core`)
  - `schemas.py` (shared file, Parsing section): `PageKind` enum (cover, contents, form,
    table, narrative, blank, other); `PageJudgement` (`text_usable`, `content_missing`,
    `page_kind`, `confirmed_flags: list[FlagReason]`, `reason`; property `bad`);
    `ParseQualityReport` (`judged_pages`, `judgements: dict[int, PageJudgement]`,
    `escalations`). Existing models unchanged.
  - `prompts/parse_quality.md`: one template, sent as one `HumanMessage`; lists each flag's
    typical false alarm and asks for the two booleans separately.
  - `parsing/quality.py` (replaces the S2 stub): `format_flags`, `format_images`,
    `render_prompt`; `judge_page(...) -> PageJudgement` (one `structured_call`, node
    `parse_quality`); `escalate(page, flags, judgement, hook=) -> (Escalation, kept_flags)`
    implementing the attribution rule, with `confirmed_flags` intersected with the page's
    real flags; `EscalationHook` type and `record_only_hook`; `run_quality_pass(parsed,
    model=None, settings=None, recorder=None, config=None, hook=) -> (ParsedDocument,
    ParseQualityReport)`: groups flags by page, one call per flagged page, records each
    escalation on the recorder, catches `StructuredOutputError` per page (flags kept,
    escalation `code`/bad with "judge failed after N attempts"), returns a deep copy with
    only surviving flags. No flags means no model is built and no call is made.
  - `parsing/__main__.py`: `--judge` runs the pass under a non-writing recorder and prints
    one row per judged page plus tokens, cost, latency and retries; the flags table and
    JSON afterwards show only surviving flags.
  - Tests: `tests/test_quality.py` (18 fake-model tests: no flags, cleared, confirmed,
    model-raised, shared call for several flags, invented flag name, confirmed flags on a
    fine page ignored, judge failure, prompt content and placeholders, recorder and
    written run log, custom hook, direct `escalate`, `bad` property, report JSON round
    trip, forbid-extra and unknown flag); `tests/test_quality_live.py` (`-m llm`, Federal
    Way, passes live). S2's obsolete `test_escalate_stub_returns_none` removed. 177 unit
    tests pass, ruff clean.
  - Live results, DeepSeek Flash, thinking off, 0 retries:

    | RFP | judged | cleared | escalated (trigger) | calls cost | latency |
    |---|---|---|---|---|---|
    | Missouri | 12, 19, 20 | 12 (merged cost table readable) | 19, 20 affidavit images (code) | $0.0013 | 4.1 s |
    | NYESD | none | — | — | $0 | 0 s |
    | Colfax | 1, 2, 3, 20, 21, 22 | all six (cover, contents, blank dividers) | none | $0.0026 | 8.4 s |
    | Federal Way | 2, 5, 14 | 2 (contents), 14 (pricing form readable) | 5 ERP table image (code) | $0.0007 | 4.5 s |

  - Docs: DECISIONS D24, PROMPTS design note and changelog line, ASSUMPTIONS (judge sees
    text only; unflagged pages are not judged), TIMELOG, README parse-quality subsection
    and layout line. Shared files touched: `schemas.py`, `README.md`.
- **Deviations from plan:**
  - The plan's "image page-area fraction" in the prompt was dropped: `ImageBlock` has no
    page size, and the `large_image_block` flag detail already carries the fraction.
  - S2's unit test for the stub was deleted, since the stub's contract (return None) no
    longer exists.
  - Status set to `done` in the docs commit, before the PR, as in S0.
- **Open issues:**
  - The `model` trigger (judge finds a problem no heuristic named) never fired on the four
    RFPs; it is covered by unit tests only.
  - Missouri p19 and p20 are escalated correctly by the rule, but they are blank affidavit
    forms, so ST2's VLM would add little there; Federal Way p5 is the page that matters.
  - S10 runs `run_quality_pass` as the node after parsing and passes the returned
    document on; S14 can serve `ParseQualityReport` as the parse-quality view.
  - Outside pytest, scripts in a worktree need `PYTHONPATH=src` because the editable
    install points at the main checkout (same as S1's note).

### S5. Requirements extractor
- **Status:** done
- **Goal:** `agents/requirements.py`: per-chunk structured extraction (ID, text, type,
  strictness as a separate field, verbatim quote, chunk ID) plus an ambiguities list.
  Around the LLM, code does: schema validation with bounded retry, quote verification
  by string match against the cited chunk (reject or mark unverified), merge, exact
  dedupe, then one LLM grouping pass for fuzzy dedupe; code merges groups, keeps all
  quotes and chunk IDs, keeps the stricter strictness, asserts every original ID lands in
  exactly one group, and flags conflicts rather than merging them. Gaps list optional
  and separate. Prompts `prompts/requirements_extract.md`, `prompts/requirements_dedupe.md`
  with design notes in `docs/PROMPTS.md`. Tests with a fake model for the code paths.
- **Depends on:** S1, S3
- **Parallel with:** S4, S6, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** **core-only scope**, the same
    include/exclude rule as `prompts/gold_requirements.md` (D23), so recall against gold
    is like for like and S7 is not flooded with boilerplate; a fuzzy-merged requirement
    keeps the **representative's quote only** (chunk IDs unioned, absorbed IDs in
    `merged_from`; no schema change); the **single-call ablation path**
    (`Settings.single_call_extraction`) is implemented now; a **live run on all four
    RFPs** fills the results table (DeepSeek Flash, under $0.30).
  - **Taken without asking:** ambiguities and gaps come from the per-chunk call (code
    assigns IDs; gaps deduped by normalised document name); an unverified quote gets one
    code-level retry with feedback naming the quote, then the item is kept with
    `quote_verified=False` (the requirement is real even if the quote is sloppy); chunk
    calls run in a thread pool (`Settings.llm_concurrency`, default 4) with the
    recorder passed explicitly (contextvars do not cross threads); `.gitattributes`
    pins `prompts/**`, `tests/fixtures/**` and `evals/gold/*.json` to LF (S3's open issue).
  - **Branch:** `step-05-requirements` off `core` as a worktree; PR into `core`.
  - **Files:** `textmatch.py` (`normalise`, `find_quote` moved from `evals/gold/`, which
    becomes a re-export shim); `schemas.py` (Requirements section: LLM output contracts
    `ExtractedRequirement`, `ExtractedAmbiguity`, `ExtractedGap`, `ChunkExtraction`,
    `Cited*` + `DocumentExtraction` for single-call, `DedupeGroup`,
    `RequirementConflict`, `DedupeOutput`; existing models unchanged); `config.py`
    (`llm_concurrency`); `agents/requirements.py`; `prompts/requirements_extract.md`,
    `prompts/requirements_dedupe.md`; debug CLI `python -m rfp_agent.agents requirements`.
  - **Pipeline:** per chunk, one `structured_call(node="requirements_extract")` →
    `verify_quotes` with `find_quote` → feedback retry if any quote is unverified (retry
    accepted only if it verifies at least as many items) → a failed chunk yields nothing
    and is counted. Code assigns `R001…` in document order, maps ambiguity indexes to
    IDs, then **exact dedupe** on normalised text or quote (the overlap sentence makes
    this common). One `structured_call(node="requirements_dedupe")` returns groups
    (representative + members) and conflict pairs; code checks every ID exists, no ID in
    two groups, representative not a member, no conflict pair inside a group; violations
    get one feedback retry, then **fallback**: unknown IDs ignored, first membership
    wins, ungrouped IDs are singletons, so "every original ID lands in exactly one group"
    holds by construction and the report records the fallback. Merge keeps the
    representative's id, text, quote, type; unions chunk IDs; max strictness; conflicts
    set `conflicts_with` symmetrically and add an `Ambiguity`. Single-call mode: one
    call over all chunks labelled by ID, quotes verified against the cited chunk,
    unknown chunk IDs rejected with feedback then dropped, grouping call skipped.
  - **Tests:** fake-model unit tests per stage (prompt rendering, quote retry paths,
    chunk failure, assemble, exact dedupe, group checks and fallback, conflict split,
    the exactly-one-group invariant, end-to-end with recorder, single-call path,
    concurrency order); a live `llm` test on Missouri.
  - **Docs:** DECISIONS D29 to D31 plus any failure modes hit, PROMPTS notes and
    changelog, ASSUMPTIONS, TIMELOG, README requirements section, `.env.example`.
- **What was done:** (branch `step-05-requirements`, PR into `core`)
  - `src/rfp_agent/textmatch.py`: `normalise`, `find_quote` moved from `evals/gold/`
    (now a re-export shim) so the package never imports `evals`.
  - `schemas.py` (shared file, Requirements section): LLM output contracts
    `ExtractedRequirement`, `ExtractedAmbiguity` (`requirement_indexes` into the same
    reply), `ExtractedGap`, `ChunkExtraction`; `CitedRequirement`/`CitedAmbiguity`/
    `CitedGap` + `DocumentExtraction` for single-call mode; `DedupeGroup`
    (`representative_id`, `member_ids`), `RequirementConflict`, `DedupeOutput`.
    `Requirement`, `Ambiguity`, `Gap`, `RequirementsOutput` unchanged.
  - `config.py` (shared): the extractor reads S6's `llm_concurrency` (default 4); its
    description now names both stages. No new setting.
  - `agents/requirements.py`: `extract_requirements(split, title=, model=, settings=,
    recorder=, config=, single_call=) -> (RequirementsOutput, RequirementsReport)`.
    Per chunk: `render_chunk_prompt` → `verified_call` (a `structured_call` followed by
    a code check and one feedback turn; the retry is kept only if it has no more
    problems than the first reply) with `verify_quotes` (`find_quote` against the chunk)
    → failed chunks skipped and listed in `report.calls_failed`. `extract_chunks` runs a
    `ThreadPoolExecutor` with the recorder passed explicitly, document order kept.
    `assemble_chunks` numbers `R001…`/`A01…`/`G01…`, cites the chunk, maps ambiguity
    indexes to IDs (out-of-range dropped with a warning). `exact_dedupe` folds equal
    normalised text or quote (`merge_into`: chunk IDs unioned, stricter strictness,
    `merged_from` lineage, a verified quote replaces an unverified one). `dedupe_llm`:
    one grouping call through `verified_call` with `check_groups` (unknown IDs,
    representative as member, ID in two groups, conflict pair inside a group) as the
    check, then `sanitise_groups` so any answer satisfies the contract (first membership
    wins, unknown IDs dropped, conflicting members removed from the group, empty groups
    dropped); `apply_groups` merges; `apply_conflicts` sets `conflicts_with` both ways and
    adds an `Ambiguity` per conflict; `dedupe_gaps` folds gaps naming the same document
    (prefix at a word boundary, so "Attachment F" and "ATTACHMENT F: SOFTWARE ..." are
    one). Single-call mode: `render_document_prompt` over every chunk, `verify_document`
    (cited chunk exists and quote found in it), items citing an unknown chunk dropped
    after the feedback turn, grouping call skipped. Node names `requirements_extract`,
    `requirements_extract_single`, `requirements_dedupe`.
  - `agents/__main__.py` (S6's agents CLI, shared): a `requirements` command,
    `python -m rfp_agent.agents requirements <pdf> [--single-call] [--out f.json]`, prints
    the report summary, per-node metrics, the requirements table, ambiguities and gaps.
  - Prompts `requirements_extract.md` (one file for both modes: `{{unit}}`,
    `{{mode_rules}}`, `{{title}}`, `{{input}}`; instructions first so the provider
    prefix cache hits, about 74% of input tokens were cache reads) and
    `requirements_dedupe.md` (`{{requirements}}`). Tuned once after the first Missouri
    run (F8, F9).
  - `.gitattributes`: added here for `prompts/**`, `tests/fixtures/**`, `evals/gold/*.json`;
    S6 landed a broader version first, which the merge kept.
  - Tests: `tests/test_requirements.py` (23 fake-model tests: prompt rendering, numbering
    and citation, quote feedback accepted / worse retry discarded / still unverified kept,
    markup-tolerant matching, failed chunk skipped, exact dedupe across the overlap,
    verified-quote adoption, group merge, violations → retry → fallback, conflict pair
    split and flagged, conflict IDs follow merges, grouping failure, a 60-round random
    grouping test of "every original ID lands in exactly one place", gap folding,
    recorder nodes and prompt hashes, 8 chunks on 4 threads in document order, single-call
    verification/drop/skip-grouping, settings default). `tests/fakes.py` gains a
    `responder` callable and a lock. `tests/test_requirements_live.py` (`-m llm`,
    Missouri, passes). 250 unit tests pass, ruff clean.
  - Live results, DeepSeek Flash, thinking off, concurrency 4. "Crude recall" is quote
    containment against gold either way after normalisation (a sanity number, not the
    S12 metric: several "misses" are the same requirement with a different span, e.g.
    every cover-page deadline was extracted). NYESD is the only run on the final prompt
    (the gap-naming line was added after the first three; see F9).

    | RFP | chunks | calls | pre-dedupe | exact | fuzzy | final | conflicts | ambiguities | gaps | gold | crude recall | cost | latency (summed) |
    |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
    | Missouri | 67 | 69 | 156 | 2 | 23 | 131 | 4 | 53 | 12 | 71 | 86% | $0.040 | 182 s |
    | NYESD | 70 | 72 | 263 | 4 | 43 | 216 | 1 | 70 | 38 | 54 | 80% | $0.056 | 207 s |
    | Colfax | 40 | 41 | 148 | 4 | 19 | 125 | 1 | 42 | 19 | 63 | 83% | $0.027 | 121 s |
    | Federal Way | 21 | 23 | 120 | 4 | 26 | 90 | 0 | 29 | 7 | 46 | 72% | $0.020 | 78 s |

    Zero failed chunks and zero unverified quotes on all four; one quote feedback turn
    on Missouri; the grouping call needed its feedback turn on three of four RFPs and
    was contract-clean after it (the first Missouri run fell back once: R030 in three
    groups twice). Wall time is about a quarter of the summed latency. Known catches:
    Colfax Attachments F and G as gaps and the 30-day vs 15-day notification conflict
    (S11's open issue) as a flagged conflict; Missouri's fixed milestone dates vs
    relative deadlines as four conflicts; Federal Way's separate Requirements document
    as a gap.
  - Docs: DECISIONS D29 to D31, F8, F9; PROMPTS notes and changelog; ASSUMPTIONS;
    TIMELOG; README requirements section; `prompts/README.md` rows already existed.
    Shared files touched: `schemas.py`, `config.py`, `.env.example`, `README.md`,
    `tests/fakes.py`, `evals/gold/textmatch.py`.
- **Deviations from plan:**
  - The debug CLI is a command on S6's `python -m rfp_agent.agents` app rather than a
    module of its own: a first version under a `__main__` guard inside the agent failed
    (with `from __future__ import annotations`, typer cannot resolve `Annotated` defined
    inside a function), and S6 had meanwhile added the shared app.
  - `extract_concurrency` was dropped on merge in favour of S6's `llm_concurrency`: one
    knob for every per-chunk stage.
  - One prompt file serves both modes (`{{unit}}`, `{{mode_rules}}`) instead of a second
    document-mode file.
  - Prompt tuned once after the first live run instead of shipping the first draft: the
    model reported other sections of the same RFP as ambiguities and gaps (F8) and
    listed NYESD forms twice, by name and by URL (F9). Requirements 144 → 131,
    ambiguities 105 → 53, gaps 39 → 12 on Missouri.
  - `exact_dedupe` lets a verified quote replace an unverified one on merge (not in the
    plan; costs nothing and improves the evidence).
- **Open issues:**
  - Volume: 90 to 216 requirements per RFP against 46 to 71 gold. Most of the surplus is
    `submission` (proposal-content lists split finely) and `legal_contractual`
    (boilerplate the prompt excludes but the model keeps when a clause reads as
    project-specific). S12 judges precision per item; S13 decides whether to tighten.
  - Ambiguities are still many (29 to 70): the "would change the bid" bar is applied
    loosely. S7 and S8 should treat them as a list to scan, not as facts; S13 can cut.
  - Run-to-run variance at temperature 0: NYESD gave 196 then 216 requirements on two
    runs of near-identical prompts. S12 should report variance over several runs (D7
    already plans this for the problem statement).
  - Conflicts over-flag alternatives (Missouri Oracle vs SQL Server, Missouri standard
    vs WCAG 2.1 AA) despite the prompt line; the four date conflicts are real.
  - The grouping call rarely passes its contract on the first try (3 of 4 RFPs needed the
    feedback turn); `sanitise_groups` makes it safe, but it is a second call per
    document. A smaller model-facing contract (groups only, conflicts in a separate call)
    is an option if S13 sees quality loss.
  - Single-call mode is unit-tested only; S13 runs it live for the D5 ablation.
  - `RequirementsReport` is a dataclass, not in the run log; S10 can log it as JSON next
    to the run log if the UI wants it.
  - The worktree needs a copy of `.env` for live runs (`cp ../../../.env .env`), since
    `Settings` reads `REPO_ROOT/.env` and `REPO_ROOT` is the worktree.

### S6. Problem statement (hierarchical)
- **Status:** done
- **Goal:** `agents/problem.py`: stage one summarises each chunk ("what is being built,
  for whom, why, under what constraints") tagged with its chunk ID, near-empty for
  irrelevant chunks; stage two synthesises client situation, goal, success criteria,
  main constraints, every factual claim citing chunk IDs, inferences labelled. Also a
  full-text baseline path behind a config flag for the S12 comparison. Code validates
  that cited IDs exist. Prompts `prompts/problem_chunk.md`, `prompts/problem_synthesis.md`.
- **Depends on:** S1, S3
- **Parallel with:** S4, S5, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** stage one is **one call per chunk, run
    concurrently** in a thread pool (new setting `RFP_LLM_CONCURRENCY`, default 4); code
    sets the chunk ID on each summary, so the model never writes a citation in stage one.
    In synthesis a claim citing a chunk ID that was not among the summaries shown is
    caught by a **validator on the output schema**, so `structured_call` feeds the bad IDs
    back and retries (the S11 F4 pattern); when the budget is exhausted the node raises
    and the run log shows why, no silent drops. The same validator rejects an **empty
    claim list** (an RFP always has a situation, goal, success criteria and constraints);
    the prompt asks for 3 to 8 claims per list but the upper bound is not enforced.
    A **`.gitattributes`** forces LF on `prompts/` and `tests/fixtures/` (S3's open
    issue: CRLF checkouts on Windows broke one S4 test and made prompt hashes differ by OS).
  - **Taken without asking:** every chunk is summarised, no code-side skipping (tiny
    front-matter chunks such as "Issued: August 8, 2025" carry facts); synthesis sees only
    summaries marked relevant, in document order, each with its chunk ID, section path and
    pages; the **full-text baseline** (`Settings.full_text_problem`) sends every chunk's
    own text (overlap stripped with `own_text`) with the same IDs through the same
    synthesis prompt, so the evidence is the only variable in the S13 comparison;
    `problem_synthesis.md` therefore takes `{{evidence}}` plus a one-line
    `{{evidence_kind}}`; a chunk whose stage-one call fails after its retries is kept as
    `relevant=False` with the error recorded on the summary (one flaky call must not kill a
    70-call stage), while a synthesis failure raises; the recorder and the prompt are
    resolved in the main thread before dispatch because contextvars do not cross
    `ThreadPoolExecutor`; node names `problem_chunk`, `problem_synthesis`,
    `problem_full_text` so per-node cost is visible.
  - **Branch:** `step-06-problem` off `core` as a worktree; one commit per unit; PR into
    `core`.
  - **`schemas.py` (shared, Problem statement section):** `ChunkSummaryDraft(summary,
    relevant)` as the stage-one LLM contract; `ChunkSummary` gains `error: str | None`.
    `ProblemStatement` itself stays permissive (S9 assembles empty ones); the validators
    live on a per-call subclass built with `pydantic.create_model` from the allowed IDs.
  - **`config.py` (shared):** `llm_concurrency` (`RFP_LLM_CONCURRENCY`, default 4);
    `.env.example` and the README table gain the row.
  - **`agents/problem.py`:** `render_chunk_prompt`, `summarise_chunk` (one call, node
    `problem_chunk`), `summarise_chunks` (thread pool, document order preserved),
    `format_evidence` (relevant summaries) and `format_full_text` (own text of every
    chunk), `problem_schema(allowed_ids)`, `synthesise` (one call, returns a plain
    `ProblemStatement`), `build_problem_statement(split, *, title, model, settings,
    recorder, config, full_text=None) -> ProblemResult(statement, chunk_summaries, mode)`;
    debug CLI `python -m rfp_agent.agents.problem <pdf> [--full-text] [--out]`.
  - **Prompts:** `prompts/problem_chunk.md` (what is being built, for whom, why, under
    what constraints; keep every number, date, amount, name and referenced document;
    `relevant=false` for contents, signature blocks and boilerplate that would apply to
    any contract) and `prompts/problem_synthesis.md` (four lists, one sentence per claim
    with the concrete value, `fact` vs `inference`, cite only IDs present in the evidence).
  - **Tests (`tests/test_problem.py`, fake model):** chunk prompt content and
    placeholders; chunk ID set by code; irrelevant chunk; failed chunk kept with error;
    concurrency preserves order; evidence lists only relevant summaries in order with
    section path; unknown ID rejected then accepted on retry; exhaustion raises; empty list
    rejected; full-text evidence has every ID and no overlap sentence; settings flag picks
    the mode; nodes recorded on the recorder. `tests/test_problem_live.py` (`-m llm`) on
    Missouri. The CRLF fix makes the failing S4 test pass on Windows.
  - **Live run:** both modes on the four RFPs once each; table of relevant chunks, claims
    per list, inferences, retries, cost and latency; spot check of each statement against
    the gold checklist by eye (S12 does it properly).
  - **Docs:** DECISIONS D28 (stage-one IDs set by code, citations checked by a schema
    validator inside the retry loop, concurrency) plus any failure mode hit; PROMPTS design
    notes and changelog; ASSUMPTIONS; TIMELOG; README problem-statement section, config
    row, layout line.
- **What was done:** (branch `step-06-problem`, PR into `core`)
  - `agents/problem.py`: `summarise_chunk` (one `structured_call` per chunk, node
    `problem_chunk`, schema `ChunkSummaryDraft`; code attaches the chunk ID; a relevant
    verdict with an empty summary is recorded as not relevant; a call that fails after its
    retries returns `relevant=False` with the error on the summary), `summarise_chunks`
    (thread pool of `Settings.llm_concurrency`, document order kept, prompt and recorder
    resolved on the calling thread), `format_evidence` / `evidence_ids` (relevant summaries
    labelled `[S3.2] section > path (pages n)`), `format_full_text` (own text of every
    chunk, overlap stripped with `own_text`, same labels), `problem_schema(allowed_ids)`
    (a `ProblemStatement` subclass per call via `pydantic.create_model`, named
    `ProblemStatement` so the tool name is unchanged, whose validator rejects an empty
    claim list and any chunk ID outside the evidence with a message naming the list and the
    IDs), `synthesise` (one call, node `problem_synthesis` or `problem_full_text`,
    returns the plain contract class), `build_problem_statement(split, *, title, model,
    settings, recorder, config, full_text=None) -> ProblemResult(mode, statement,
    chunk_summaries)`; `NoEvidenceError` when no chunk is relevant.
  - `agents/__main__.py`: `python -m rfp_agent.agents [-v] problem <pdf> [--full-text]
    [--out f.json]` runs parse, split and the agent under a non-writing recorder and prints
    per-node calls, tokens, cost, latency and retries, then the claims. S5, S7 and S8 add
    their commands here.
  - Prompts `prompts/problem_chunk.md` (title, chunk ID, section path, pages, text; the
    relevance list mirrors the gold checklist categories) and `prompts/problem_synthesis.md`
    (`{{title}}`, `{{evidence_kind}}`, `{{evidence}}`; four lists, one sentence per claim
    with the concrete value, `fact` vs `inference`, cite only labelled IDs, write about "the
    RFP" never "the evidence").
  - `schemas.py` (shared, Problem statement section): `ChunkSummaryDraft(relevant,
    summary)`; `ChunkSummary.error`. `ProblemStatement` unchanged. `config.py` (shared):
    `llm_concurrency` (`RFP_LLM_CONCURRENCY`, default 4). `.env.example`: that row plus
    `RFP_FULL_TEXT_PROBLEM`.
  - `.gitattributes` (new shared file): LF for every text file type and binary for PDFs,
    so Windows checkouts hash prompts and compare goldens like CI; the S4 test that failed
    locally passes.
  - Tests: `tests/test_problem.py` (18 fake-model tests: prompt placeholders and content,
    chunk IDs set by code in order, irrelevant and empty summaries, failed chunk kept with
    error and recorded, concurrent order, evidence formatting, full text without overlap,
    schema name, unknown ID fed back then accepted, empty list fed back, exhaustion raises,
    synthesis prompt content, hierarchical end to end with recorder and prompt hashes,
    full-text mode from the flag and from the argument, no evidence raises, JSON round
    trip); `tests/test_problem_live.py` (`-m llm`, Missouri). 245 unit tests pass, ruff
    clean.
  - Live results, DeepSeek Flash, thinking off, concurrency 4 (NYESD hierarchical run four
    times, Federal Way twice; cost ranges come from DeepSeek's automatic prefix caching on
    repeated runs). Latency is wall time including parsing and splitting:

    | RFP | mode | relevant chunks | claims sit/goal/crit/constr | inferences | calls | tokens in / out | cost | retries | wall |
    |---|---|---|---|---|---|---|---|---|---|
    | Missouri | hierarchical | 41 / 67 | 7 / 7 / 8 / 8 | 1 | 68 | 73.7k / 9.9k | $0.018 | 0 | ~35 s |
    | Missouri | full text | — | 7 / 8 / 8 / 8 | 1 | 1 | 11.5k / 2.3k | $0.006 | 0 | ~15 s |
    | NYESD | hierarchical | 60 to 63 / 70 | 6 / 6 / 7 / 8 | 1 | 71 | 90k / 15k | $0.026 to $0.043 | 1 in 2 of 4 runs | 63 s |
    | NYESD | full text | — | 7 / 7 / 8 / 9 | 0 | 1 | 18.5k / 2.2k | $0.008 | 0 | 21 s |
    | Colfax | hierarchical | 35 / 40 | 6 / 7 / 7 / 8 | 1 | 41 | 47.3k / 8.1k | $0.021 | 0 | ~30 s |
    | Colfax | full text | — | 6 / 7 / 8 / 8 | 2 | 1 | 8.6k / 1.9k | $0.005 | 0 | ~15 s |
    | Federal Way | hierarchical | 19 to 20 / 21 | 6 / 7 / 7 / 8 | 2 | 22 | 29.4k / 6.6k | $0.010 to $0.015 | 0 | 32 s |
    | Federal Way | full text | — | 7 / 7 / 8 / 8 | 1 | 1 | 7.4k / 1.9k | $0.004 | 0 | 20 s |

    Every citation resolved (the validator guarantees it); no stage-one call failed. A
    rough keyword check against the 12-fact gold checklists (numbers, dates, amounts of
    each fact found in the claims) gives 12 / 12 for every hierarchical output and 11 to
    12 / 12 for full text; read by eye, Federal Way and NYESD cover every checklist fact
    except Federal Way GC12 (the current systems live in the page-5 image table, absent
    from the parsed text; the statement says so, labelled as an inference) and Missouri
    full text drops the 1/1/2026 final-report date. Both modes surface the
    referenced-but-absent documents (Colfax Attachment F, NYESD Appendices A and B and
    Schedule A, Federal Way Requirements document) as constraints.
  - Docs: DECISIONS D28, F6; PROMPTS design notes and changelog (creation plus one wording
    fix); ASSUMPTIONS (problem statement section); TIMELOG; README problem-statement
    section, configuration rows, layout and status lines. Shared files touched:
    `schemas.py`, `config.py`, `.env.example`, `README.md`, `tests/test_config.py`,
    `.gitattributes` (new).
- **Deviations from plan:**
  - The debug CLI lives in `agents/__main__.py` (`python -m rfp_agent.agents problem`),
    not in `problem.py`: typer resolves the string annotations that
    `from __future__ import annotations` produces against module globals, so a CLI defined
    inside a function with local imports crashed with `NameError: Annotated`. The shared
    entry point also keeps typer and rich out of the agent module and gives S5, S7 and S8
    a place to add their commands. A `-v` flag prints every failed attempt.
  - `.gitattributes` forces LF on every text type (`*.py`, `*.md`, `*.json`, ...), not only
    `prompts/` and `tests/fixtures/`: the cost is nil and it stops the "LF will be replaced
    by CRLF" churn on every commit from Windows.
  - After the first live run the synthesis prompt gained a rule to write about "the RFP",
    never "the evidence" or "the summaries": three of four hierarchical outputs had a
    constraint reading "documents not included in the evidence". Fixed and re-run on
    NYESD and Federal Way (clean).
  - A stage-one `relevant=True` with an empty summary is downgraded to not relevant in
    code (the plan did not say; an empty summary carries no evidence to cite).
- **Open issues:**
  - The citation validator fired in 2 of 4 NYESD runs (one retry, then success), but the
    `structured_call` log line truncates the error at 200 characters and the run log keeps
    only the retry count, so which ID or list was wrong is not recorded. S12 or S13 should
    add the last validation error to `NodeMetrics` (S1-owned schema) so retries are
    diagnosable from the log.
  - DeepSeek Flash is not deterministic at temperature 0: four NYESD runs gave 60 to 63
    relevant chunks and different claim wording. S12's repeated-run consistency metric is
    therefore necessary, not optional.
  - Stage one compresses little on NYESD (76k input tokens become 13k of summaries, versus
    18.5k tokens of full text), so the hierarchical path costs 3 to 5x the full-text call
    on every RFP and buys per-chunk citations and scale rather than cheaper synthesis. A
    tighter length rule in `problem_chunk.md` is an S13 experiment, to be judged by
    checklist coverage.
  - Federal Way's current systems (page 5, image only) cannot reach the statement without
    ST2; the hierarchical output flags the gap as an inference, the full-text output does
    not mention it.
  - S10 wiring: the problem node calls `build_problem_statement(split, title=parsed.title,
    config=config)` and should keep `ProblemResult.chunk_summaries` in the graph state for
    S14's per-chunk view; `full_text_problem` is read from settings so the CLI only needs
    to expose the flag.

### S7. Solution generator
- **Status:** in progress
- **Goal:** `agents/solution.py`: inputs problem statement, requirements with quotes
  and chunk IDs, ambiguities. Output a structured approach whose components cite the
  requirement IDs they address so mandatory coverage is computable by code; factual
  claims cite chunk or requirement IDs. Code computes coverage of mandatory
  requirements and lists uncovered ones. Prompt `prompts/solution.md`.
- **Depends on:** S5, S6
- **Parallel with:** S4, S9, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** mandatory coverage counts every mandatory
    requirement **except type `submission`** (page limits, copies, forms are shown to the
    model as context but a component cannot "address" them); the coverage check is a
    **LangGraph loop**: generate → code computes coverage → revise with the uncovered IDs
    fed back while any in-scope mandatory requirement is uncovered, **capped at
    `RFP_SOLUTION_MAX_ITERATIONS` (default 3)**; requirements go into the prompt as
    `R012 [mandatory, technical] text (S4.2)` **without the quote** (the text is already a
    verified one-sentence statement, quotes would double the block); **live run on all
    four RFPs**, prompt tuned once if a failure mode shows.
  - **Taken without asking:** no chunk text is sent; the evidence is the problem
    statement (claims labelled with their chunk IDs), the requirements, the ambiguities
    and the gaps, and the model may cite only requirement IDs from the list and chunk IDs
    that appear in that evidence; component IDs `C01…` are assigned by code (D28), so the
    LLM contract is `SolutionDraft(summary, components: [ComponentDraft(title,
    description, requirement_ids, claims)], assumptions)`; a per-call subclass built with
    `create_model` rejects an empty component list, a component with no requirement IDs,
    an unknown requirement ID or an unknown chunk ID inside the `structured_call` retry
    loop (the S6 pattern); the revision happens in the same conversation (prompt, reply,
    feedback, reply, …) so the model sees its own answer; the draft with the fewest
    uncovered requirements is kept, so a worse revision cannot regress the output; the
    remaining uncovered IDs are listed in `Coverage` for S8 to turn into risks; node names
    `solution_generate` (first round) and `solution_revise` (later rounds).
  - **Branch:** `step-07-solution` off `core` as a worktree; PR into `core`.
  - **Files:** `schemas.py` (Solution section, S7-owned: `ComponentDraft`,
    `SolutionDraft`; `Solution`, `SolutionComponent`, `Coverage` unchanged); `config.py`
    (`solution_max_iterations`) and `.env.example`; `agents/solution.py`;
    `agents/__main__.py` (`solution` command: `python -m rfp_agent.agents solution <pdf>
    [--requirements f.json] [--problem f.json] [--max-iterations n] [--out f.json]`,
    running S5 and S6 first when no JSON is given); `prompts/solution.md`
    (`{{title}}`, `{{problem}}`, `{{requirements}}`, `{{ambiguities}}`, `{{gaps}}`,
    instructions first for the prefix cache).
  - **Pipeline:** `format_problem`, `format_requirements` (mandatory, desired, optional
    blocks; submission items in a "context, do not address" block), `format_ambiguities`,
    `format_gaps`, `allowed_chunk_ids` → `build_graph(...)` binds model, settings,
    recorder, prompt and allowed IDs in closures; state holds messages, latest and best
    draft, uncovered IDs, iteration and the per-round coverage history; nodes `generate`
    and `check`, conditional edge to `revise` (feedback lists each uncovered ID with its
    text) or `END`; `compute_coverage` is a pure function; `build_solution(requirements,
    problem, *, title, model, settings, recorder, config, max_iterations=None) ->
    SolutionResult(solution, rounds, iterations)`. Retry exhaustion in any round raises.
  - **Tests:** fake-model unit tests (prompt placeholders and content, allowed-ID union,
    coverage scope and order, validator feedback on unknown requirement and chunk IDs,
    empty components and component without requirements rejected, exhaustion raises,
    `C01…` numbering, one call when round one covers everything, revise then covered,
    worse revision discarded, cap from setting and argument, recorder nodes and prompt
    hash, assembled summary passes `dangling_citations` and renders); a live `llm` test
    on Missouri; `test_config.py` default.
  - **Docs:** DECISIONS D32 plus any failure mode hit, PROMPTS note and changelog,
    ASSUMPTIONS, TIMELOG, README solution section and config row.
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S8. Risk assessor
- **Status:** todo
- **Goal:** `agents/risk.py`: reads the solution and everything before it; covers
  risks inherent in the RFP (timelines, vague or conflicting requirements, missing
  budget, referenced-but-absent documents, flagged pages) and risks created by the
  solution. Structured output: risk, severity, likelihood (scales defined in this
  step's plan), justification, requirement and chunk IDs. Code validates IDs. Prompt
  `prompts/risk.md`.
- **Depends on:** S7
- **Parallel with:** S4, S9, S11
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S9. JSON assembly and markdown renderer
- **Status:** done
- **Goal:** `render/`: assemble the final `SolutionSummary` JSON (source of truth) and
  render markdown from it in code with citations shown as "section title, page" and
  requirement quotes inline. Golden-file tests from fixture JSON. No LLM.
- **Depends on:** S0
- **Parallel with:** S1 to S8, S11
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** citations render as
    `(Section title, p. 4 [S3.2])`, with the chunk ID kept so the markdown traces back to
    the JSON and UI; `assemble()` raises `CitationError` on dangling IDs by default
    (`strict=False` opts out) and the renderer falls back to the raw ID so it never
    crashes; requirements grouped by type, verbatim quote as a blockquote; risks as an
    overview table sorted by severity then likelihood, then per-risk details.
  - **Branch:** `step-09-render` off `core` as a worktree; one commit per unit; PR into
    `core`. No schema change, no new dependency.
  - **`render/assemble.py`:** `assemble(*, run_id, model, parsed, split, requirements,
    problem_statement, solution, risks, generated_at=None, strict=True)` builds
    `ChunkRef`s from `SplitDocument` (owning section title, chunk pages), copies
    `source_path`, `title`, `referenced_documents`, `flags` from `ParsedDocument`.
    `dangling_citations(summary)` walks every citation site (claims, requirement
    `chunk_ids` and `conflicts_with`, ambiguities, gaps, component `requirement_ids`,
    `uncovered_requirement_ids`, risk IDs) and returns `(location, id)` pairs;
    `merged_from` is not checked (pre-merge IDs are gone by design). Coverage stays S7's.
  - **`render/markdown.py`:** `render_markdown(summary)`, pure and deterministic. Order:
    title and metadata; problem statement (four subsections, claim bullets, inference
    marked); requirements (count line, one subsection per type present, quote
    blockquote, merged/conflicts lines, unverified-quote marker, ambiguities, gaps);
    proposed solution (summary, coverage line and uncovered IDs, components, assumptions);
    risks (sorted table, then details with why, mitigation, related requirements);
    referenced documents table; parse flags. Empty sections print "None." so the shape is
    stable. Citations group chunk IDs that share section title and page range.
  - **`render/io.py`:** `write_summary(summary, out_dir)` writes `summary.json` and
    `summary.md`; S10 decides the directory.
  - **Tests:** `tests/fixtures/summary_sample.json` hand-built to hit every render
    branch, golden `tests/fixtures/summary_sample.md`, `--update-golden` pytest option in
    `tests/conftest.py`; tests for determinism, risk sort, unknown-chunk fallback, table
    escaping, assembler chunk refs and metadata, strict and non-strict dangling
    citations, file writing. No LLM.
  - **Docs:** DECISIONS D16 (layout, citation format, strict assembler, golden tests),
    TIMELOG row, README render section. PROMPTS untouched (no prompt).
- **What was done:** (branch `step-09-render`, PR into `core`)
  - `src/rfp_agent/render/assemble.py`: `assemble()` (keyword-only, `generated_at`
    injectable, `strict=True`), `chunk_refs(split)`, `dangling_citations(summary)`
    returning `(location, id)` pairs such as `("risks.K01.chunk_ids", "S9.9")`,
    `CitationError` carrying `.dangling`. Uses `validate_ids_exist` from `schemas.py`.
  - `src/rfp_agent/render/markdown.py`: `render_markdown(summary)`, public helpers
    `cite(chunk_ids, index)` and `sorted_risks(summary)` (S14/S15 can reuse them),
    `TYPE_LABELS` and `SOURCE_LABELS` for human-readable enum labels. All free text is
    whitespace-collapsed in list items and table cells; table cells escape `|`.
  - `src/rfp_agent/render/io.py`: `write_summary(summary, out_dir)` writes
    `summary.json` (indent 2) and `summary.md` (LF newlines); S10 picks `out_dir`.
  - `render/__init__.py` re-exports `assemble`, `chunk_refs`, `dangling_citations`,
    `CitationError`, `render_markdown`, `write_summary`.
  - Tests: `tests/test_render.py` (14 tests: golden, determinism, section order, cite
    grouping, unknown-ID fallback, risk sort, table escaping, empty-summary placeholders,
    assembler chunk refs and metadata, default timestamp, strict raise, non-strict keep,
    dangling detection across sites, writer round-trip); fixture
    `tests/fixtures/summary_sample.json` and golden `tests/fixtures/summary_sample.md`;
    `tests/conftest.py` adds `--update-golden`. 43 tests pass, ruff clean.
  - Shared file touched: `pyproject.toml` gains `pythonpath = ["src"]` under pytest
    (see deviations). README: status line, output file names and citation format,
    `--update-golden`. DECISIONS D16. TIMELOG row.
- **Deviations from plan:**
  - The environment's editable install pointed at the deleted `step-00-scaffold`
    worktree, so `rfp_agent` was not importable. Fixed twice over: re-ran
    `pip install --no-deps -e` against the main checkout, and set pytest's
    `pythonpath = ["src"]` so every worktree tests its own source regardless of where
    the editable install points. Parallel steps should rely on the latter.
  - Risk details use `###` headings (plan said `####`) so heading levels do not skip.
  - Requirement notes (merged from, conflicts with) sit on the item line in italics
    rather than on separate lines, because a line after a blockquote would be swallowed
    into the quote.
- **Open issues:**
  - `merged_from` IDs are not checked by `dangling_citations` by design; if S5 ever
    reuses a pre-merge ID for a different requirement, nothing flags it.
  - The renderer trusts `Coverage` from S7; it does not recompute it.
  - S14/S15 may want per-claim anchors in the markdown for click-to-source; not added.

### S10. LangGraph wiring and CLI
- **Status:** todo
- **Goal:** `graph.py`: the pipeline as a LangGraph graph with the parallel fan-out
  (S5 and S6), per-node observability from S1, event streaming usable by the UI.
  `cli.py`: `python -m rfp_agent run inputs/rfp_brief.pdf` writes JSON, markdown and the
  run log; `--full-text-problem` and `--single-call-extraction` flags for ablations.
  First end-to-end run on the primary brief; commit the sample outputs and run log
  under `runs/samples/`; start the failure-modes list in `docs/DECISIONS.md`.
- **Depends on:** S4, S8, S9
- **Parallel with:** S11
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S11. Gold labels
- **Status:** done
- **Goal:** `evals/gold/`: for each of the four RFPs, gold requirements (text, type,
  strictness, quote) and a problem-statement checklist of 8 to 12 must-mention facts,
  drafted by Claude from the parsed text and hand-corrected; record the fraction of
  labels corrected per RFP. Federal Way's image-only ERP table is labelled by hand so
  the known parsing miss is visible. A labelling script and a README on the format.
- **Depends on:** S2
- **Parallel with:** S1, S3 to S10
- **Detailed plan:** (approved 2026-10-30)
  - **Author decisions, asked in one batch:** wait for S2 and verify gold quotes against
    its parsed text (S2 merged before implementation started); drafts come from the
    configured judge (`anthropic:claude-sonnet-5-5`) through a labelling script; the agent
    corrects every drafted item against the full text and the author spot-checks the diff
    in the PR; **gold is core-only**: requirements that shape the solution (functional,
    technical, security_compliance, timeline, budget_pricing, submission; legal_contractual
    only when it constrains the solution), about 25 to 50 per RFP, generic legal
    boilerplate excluded. Consequence for S12: recall is measured against gold, precision
    by a judge (an extracted boilerplate clause is not a false positive).
  - **Branch:** `step-11-gold-labels` off `core` (worktree); PR into `core`.
  - **Format (`evals/gold/schema.py`):** `GoldSet(rfp, source_pdf, drafted_with,
    drafted_at, requirements, checklist, notes)`; `GoldRequirement(id GR001, text, type,
    strictness, quote, page, section, source, quote_verifiable, note)`;
    `GoldChecklistItem(id GC01, fact, quote, page, source, quote_verifiable, note)`;
    `source` = draft | corrected | hand. Reuses the pipeline enums; own ID prefixes so gold
    and pipeline IDs never collide; no chunk IDs (gold must survive re-chunking).
  - **Quote matching (`evals/gold/textmatch.py`):** `normalise` (NFKC, quote and dash
    style, `<br>`, markdown markers and pipes, whitespace, case) applied to both sides;
    `find_quote`. S12 reuses it.
  - **Script (`python -m evals.gold.label`):** `draft` (S2 parse, pages joined with
    `[page N]` markers, two judge calls via S1's `structured_call` with prompts
    `gold_requirements` and `gold_checklist`, items whose quote is not in the text are
    dropped and reported, writes `<rfp>.draft.json`), `init` (draft to `<rfp>.json`,
    appends `<rfp>.hand.json` items, refuses to overwrite), `diff` (draft vs final per
    field; corrected fraction = (edited + removed) / drafted, additions counted
    separately), `check` (every verifiable quote is in the parsed text, checklist has 8
    to 12 items).
  - **Federal Way p5:** the ERP environment table is an image; labelled by hand from the
    page render in `federal_way.hand.json` with `quote_verifiable=false`.
  - **Tests (`tests/test_gold.py`):** schema, quote matching, draft with the scripted fake
    model, init, diff, and a check over every committed final gold file (parses the PDF).
  - **Docs:** `evals/gold/README.md` (format, workflow, scope rule, correction table),
    DECISIONS D23, PROMPTS design notes for both prompts, ASSUMPTIONS, TIMELOG, README.
- **What was done:** (branch `step-11-gold-labels`, PR into `core`)
  - `evals/gold/schema.py`: `GoldSet`, `GoldRequirement` (`GR001`), `GoldChecklistItem`
    (`GC01`), `GoldSource` (draft, corrected, hand), unique-ID validator,
    `checklist_size_ok()` (8 to 12). Pipeline enums reused; `rfp_agent/schemas.py`
    unchanged.
  - `evals/gold/textmatch.py`: `normalise` (NFKC, quote and dash style, any HTML tag,
    markdown markers and pipes, whitespace, case) and `find_quote`, for S12 to reuse.
  - `evals/gold/label.py` (`python -m evals.gold.label`): `draft` (S2 parse, `[page N]`
    markers, two `structured_call`s on the judge with `DRAFT_MAX_TOKENS=32000` and a
    600 s timeout, drops items whose quote is not in the text), `init` (draft to final,
    appends `<rfp>.hand.json` with fresh IDs, refuses to overwrite), `diff` (per-field
    draft vs final, corrected fraction = (edited + removed) / drafted), `check` (quotes
    and checklist size; exit 1 on failure). Prompts load from this checkout's `prompts/`.
  - Prompts `prompts/gold_requirements.md` and `prompts/gold_checklist.md`.
  - Gold data: `<rfp>.draft.json` (untouched Claude Sonnet 5.5 drafts) and `<rfp>.json`
    (final) for missouri, NYESD, colfax, federal_way; `federal_way.hand.json` (8 labels
    for the page 5 image table, `quote_verifiable=false`). Final counts: 71, 54, 63, 54
    requirements; 12 checklist facts each. Corrected fraction 19%, 26%, 20%, 21%;
    almost all removals for scope (table in `evals/gold/README.md`). Drafting cost about
    $1.6 including the failed and repeated runs.
  - `evals/gold/README.md` (format, workflow, scope, Federal Way exception, correction
    table and what the human pass changed).
  - Tests: `tests/test_gold.py` (schema, quote matching, draft with the scripted fake
    model incl. short-checklist retry, init, diff, unverified quotes, and a check of every
    committed final file against the parsed PDF).
  - Shared files: `pyproject.toml` (pytest `pythonpath` and ruff `src` gain `.` so
    `evals` imports), `README.md` (gold labels section), `prompts/README.md` (two rows).
  - Docs: DECISIONS D23, F4, F5; PROMPTS design notes and changelog; ASSUMPTIONS (gold
    scope, quotes tied to S2 text); TIMELOG.
- **Deviations from plan:**
  - S1 was already merged, so the script reuses `structured_call` and `load_prompt`
    instead of a local prompt loader. `load_prompt` gets an explicit `prompts_dir`
    because the editable install points at the main checkout.
  - The first run returned 3 checklist facts for Missouri and NYESD (F4); a validator now
    enforces 8 to 12 through the retry loop, and both RFPs were redrafted. The NYESD
    redraft hit the 16,000-token cap (F5); the drafting cap is 32,000.
  - `normalise` strips every HTML tag, not only `<br>`: NYESD and Missouri quotes sit
    next to `<u>` and `<mark>` tags left by the parser.
  - Corrections were applied with a throwaway script from a per-RFP spec (remove, edit,
    add); the committed draft-vs-final diff is the record, so the script is not kept.
  - Scope rulings applied consistently across RFPs: standard state certifications and
    affidavits, procurement-conduct and contact rules, public-records clauses, late-
    submission consequences and post-award compliance reporting are out; diversity
    participation goals, insurance amounts, deliverable ownership, key-personnel and
    subcontracting limits are in.
- **Open issues:**
  - Gold was corrected by the coding agent, not the author; the author spot-checks the
    diff in this PR. Any author edits should keep `source=corrected` and rerun `diff`.
  - S12 must judge precision per extracted item (gold is core-only) and should treat
    `quote_verifiable=false` items as recall the pipeline cannot reach without S4's VLM.
  - Colfax's Attachment D notification window conflicts (30 days p14 vs 15 days p19);
    noted in `colfax.json`, out of gold scope, a good ambiguity test for S5.
  - `tests/test_gold.py` parses all four PDFs for the committed-gold check (about 25 s).

### S12. Evaluation harness
- **Status:** todo
- **Goal:** `evals/`: run the pipeline over the four RFPs and score. Requirements:
  match extracted to gold, precision and recall, type and strictness accuracy on matched
  pairs. Grounding on every cited output: code checks (cited IDs exist; numbers, dates,
  amounts, proper nouns appear in the source) and a Claude judge that sees only the
  claim and the cited chunk; unsupported-claim count per output. Problem statement:
  checklist coverage by judge plus grounding. Solution: mandatory coverage by code and
  judge, rubric judge (specificity, feasibility, consistency with constraints),
  grounding, consistency across repeated runs, pairwise judge with order swapped for
  ablations. Reads the local run logs for cost and latency. Commit results under
  `evals/results/` with a short README; hand-score a sample for judge agreement.
- **Depends on:** S10, S11
- **Parallel with:** S14
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S13. Ablations and fixes driven by evals
- **Status:** todo
- **Goal:** run and commit: hierarchical vs full-text problem statement (several runs
  each, variance), per-chunk vs single-call extraction. Fix the failure modes the evals
  expose (prompt edits logged in `docs/PROMPTS.md`, code fixes), each with a
  before/after number in `docs/DECISIONS.md`. Decide with evidence whether any
  back-burner agentic feature (critic, revision loop) is justified; if not, say why.
- **Depends on:** S12
- **Parallel with:** S14, S15
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S14. UI backend (FastAPI)
- **Status:** todo
- **Goal:** `ui/backend/`: upload a PDF, start a run, stream LangGraph node events over
  SSE with per-node latency, tokens and cost, serve every intermediate output (parsed
  markdown, chunks, requirements, ambiguities and gaps, problem statement, solution,
  risks), the rendered markdown, the run summary with Langfuse trace link, JSON and
  markdown downloads, and a chunk lookup endpoint for source reveal. Define the API
  contract up front so S15 can start against it.
- **Depends on:** S10
- **Parallel with:** S12, S13
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S15. UI frontend (Vite, React, Tailwind)
- **Status:** todo
- **Goal:** `ui/frontend/`: upload and view the source PDF alongside; live per-node
  progress with metrics (doubles as the metrics dashboard); main view of the rendered
  solution; views for every intermediate output, requirements table filterable by type
  and strictness, risks sorted by severity; click any requirement, risk or cited claim
  to reveal its source (quote or chunk with section and page); run summary with totals
  and Langfuse link; download buttons. Visual language based on Emigre-era design
  (expressive display type, asymmetric grid, rules and whitespace, one accent, open-licence
  fonts; no copied layouts, no licensed Emigre faces), single aesthetic, no theme toggle.
  Functional first; screenshot-critique-adjust with Playwright MCP within budget, deeper
  polish is stretch ST1.
- **Depends on:** S14
- **Parallel with:** S12, S13
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

### S16. Documentation, Dockerfile, demo script
- **Status:** todo
- **Goal:** README complete (how to run CLI and UI, where the key goes, how to run
  evals, pipeline diagram, demo script listing what to click in what order, a short
  "live change rehearsal" list: swap model, edit a prompt, add a requirement type);
  Dockerfile for local run; `docs/PROMPTS.md` design notes complete; `docs/TIMELOG.md`
  totals per deliverable; `docs/DECISIONS.md` evidence fields updated; sample run logs
  and eval results committed. Then merge `core` into `main`, delete `core`, sync.
- **Depends on:** S13, S15
- **Parallel with:** —
- **Detailed plan:** _(fill in when the step starts)_
- **What was done:**
- **Deviations from plan:**
- **Open issues:**

---

## 3. Stretch goals (own branches off `main`, only after core is merged)

Priority order. Each gets the same entry structure when started.

| ID | Stretch goal | Depends on | Notes |
|---|---|---|---|
| ST1 | UI visual polish: Emigre-direction iteration with Playwright screenshots | S15 | First stretch item |
| ST2 | VLM transcription of flagged pages and images, compared against the library parser | S4, S12 | Measurable on Federal Way p5 |
| ST3 | Fetch and ingest hyperlinked or referenced external documents | S2, S5 | Colfax Attachments F and G as test |
| ST4 | Critic/reviewer agent | S13 | Only if S13 evidence shows a weakness it fixes |
| ST5 | Revision loop with hard iteration cap | ST4 | |
| ST6 | Per-theme drafting and sub-problem decomposition in the solution step | S13 | Needs baseline comparison |
| ST7 | Model-family benchmark: Claude vs DeepSeek on cost, latency, quality with identical prompts; third family for label drafting | S12 | Commit results |
| ST8 | Retrieval-based grounding beyond chunk citations | S12 | |
| ST9 | Observability dashboard in the UI beyond live progress | S15 | |
| ST10 | Cloud deployment | S16 | Only with all core and evals done |
| ST11 | Observability extras: retry and validation-failure counts per node, escalation events, cache tokens, prompt/config hash, code-computed quality signals per run | S1 | Lowest priority; not planned for implementation |

---

## 4. Known facts for planning (from the 2026-10-30 inspection)

- Missouri: budget not to exceed $175,000; contract Nov 2024 to Feb 2026 with a dated
  milestone table; Tasks 1 to 6; Section 5 has 24 lettered legal clauses; pages 13 to
  18 are IT standards with hard constraints (Python needs IS review-team approval, no
  PII in database tables, WCAG 2.1 AA). Good test for the risk assessor.
- NYESD: no PDF outline, 63 hyperlinks, references Appendix A/B and Schedule A.
- Colfax: has an outline, Attachments A to G provided separately; F and G hold the
  software requirements, so the "referenced but absent" gap case is real.
- Federal Way: no outline, 10 tables, page 5 ERP environment table is an image; the
  functional requirements live in a separate document not provided.
- pymupdf4llm artefacts seen: bold URLs split across lines inside table cells, curly
  apostrophes, a merged header cell in the cost-estimate table.
- Every document fits one context window, so single-call extraction is a fair baseline.
