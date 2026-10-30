# DECISIONS.md

Trade-offs, failure modes hit, and fixes. Living file; every roadmap step adds to it.

Each decision uses the same shape so it can be defended live:

```
### D<n>. <title>
Context:   what forced the choice
Options:   what was considered
Choice:    what was picked
Why:       the reasoning, in two or three sentences
Evidence:  eval numbers, run logs, or "none yet" (update when evidence exists)
```

Failure modes go in the second section with the same discipline: observed, not
hypothetical, each with the fix and a before/after number where one exists.

---

## Part 1 — Decisions

### D1. LangGraph as the orchestration framework
Context: the assignment requires a genuine agentic workflow (tools, steps, multi-agent)
and names LangGraph/CrewAI, n8n and Flowise as options.
Options: LangGraph; CrewAI; hand-rolled asyncio pipeline; n8n/Flowise (no-code).
Choice: LangGraph.
Why: the pipeline is a DAG with one fan-out (requirements and problem statement in
parallel) and bounded retry loops; LangGraph expresses that explicitly, streams
per-node events for the UI, and integrates with Langfuse through the LangChain callback.
A hand-rolled pipeline would be less to defend but would re-implement streaming and
checkpointing. No-code tools make the eval harness and typed schemas awkward.
Evidence: none yet.

### D2. Hosted paid APIs instead of local models
Context: the assignment encourages free/open tooling (Ollama is named) and says no paid
cloud is required.
Options: Ollama with a small local model; hosted APIs; both with a switch.
Choice: hosted APIs, provider and model as a single config setting. No local fallback
in core.
Why: every stage depends on reliable long-context structured output, which small local
models do not deliver, and reviewers cannot be assumed to have GPUs. The author hands
reviewers a low-balance key out of band. The config switch keeps the door open to any
LangChain-supported model.
Evidence: none yet (the model-family benchmark is a stretch goal).

### D3. DeepSeek generates, Claude judges; single family per role
Context: the original plan benchmarked Claude vs DeepSeek and used three model families
(generator, judge, label drafter) to avoid self-preference in judging.
Options: three families; two families; one family for everything.
Choice: DeepSeek for the whole generation pipeline, Claude as the eval judge and label
drafter. Cross-family benchmarks are a stretch goal.
Why: time budget. Two families still keep the judge independent of the generator, which
is the bias that matters most. Labels are hand-corrected, so the drafter's family
matters less; the corrected fraction is recorded.
Evidence: none yet.

### D4. Chunk-ID citations instead of retrieval-based grounding
Context: the assignment lists "RAG grounding on provided data" as a stretch; outputs must
be checkable against the RFP.
Options: vector retrieval with a lookup tool for the agents; deterministic chunk IDs
carried through every schema; no grounding.
Choice: deterministic chunk IDs (`S3.2` style) assigned by the splitter; every factual
claim cites a chunk ID or requirement ID; inferences are labelled; code validates that
cited IDs exist and that numbers, dates, amounts and proper nouns appear in the source.
Why: the documents fit in one context window, so retrieval buys nothing for coverage,
while citations make "unsupported claim" a countable eval metric and let the UI show
the source paragraph for any claim. Cheap to implement: an ID field in a few schemas
and one rule in three prompts.
Evidence: none yet.

### D5. Exhaustive per-chunk extraction, no RAG in extraction
Context: requirement extraction must not miss requirements.
Options: per-chunk extraction over every chunk; retrieval of "requirement-like" chunks;
single full-document call.
Choice: per-chunk extraction over every chunk, with a single-call full-document
baseline as an eval ablation (all four RFPs fit in one call: 4k to 10k words).
Why: retrieval introduces a recall ceiling the eval cannot easily see. The single-call
baseline is cheap to add and tells us whether chunking is worth its cost.
Evidence: none yet (ablation planned in the eval step).

### D6. Fuzzy dedupe by one LLM grouping pass, not embeddings
Context: per-chunk extraction produces near-duplicate requirements across chunks.
Options: embedding similarity with a threshold; one LLM call returning groups of
duplicate IDs; no fuzzy dedupe.
Choice: exact dedupe in code, then one LLM pass that returns groups; code merges groups,
keeps all quotes and chunk IDs, keeps the stricter strictness, and asserts every ID
lands in exactly one group. Conflicting requirements are flagged, not merged.
Why: at tens of requirements per document, embeddings are overkill and need a tuned
threshold; a grouping call is one request and its output is checkable by assertion.
Evidence: none yet.

### D7. Hierarchical summarisation for the problem statement, no boilerplate removal
Context: the problem statement must capture why the client is buying, not just what.
Options: one full-text call; hierarchical per-chunk summaries then synthesis;
boilerplate stripping before either.
Choice: hierarchical as the production path, full-text as an eval baseline. No
boilerplate removal.
Why: hierarchical scales past the context window and yields per-chunk citations
naturally. Boilerplate detection is untrustworthy: Missouri's "boilerplate" IT
standards section contains hard technical constraints.
Evidence: none yet (compare in the eval step, several runs each, report variance).

### D8. Markdown rendered by code from JSON
Context: the deliverable is a structured summary; the UI and download need markdown.
Options: ask the LLM for markdown; render from JSON in code.
Choice: JSON is the source of truth; code renders markdown and turns citations into
"section title, page" references.
Why: one model-free step less to evaluate, and the rendered citations are guaranteed to
match the JSON.
Evidence: n/a.

### D9. Parsing: library first, heuristics flag, LLM judges flagged pages, VLM is stretch
Context: layout-aware parsing is needed for tables; some pages are images.
Options: VLM-transcribe everything; library only; library plus escalation.
Choice: pymupdf4llm for text and tables; code heuristics flag suspicious pages (low
word count, large image blocks, broken tables); an LLM judges only flagged pages; a
clean hook escalates confirmed-bad pages to a VLM (stretch). Whether code or the LLM
triggered an escalation is logged.
Why: all four test RFPs are text-native and pymupdf4llm renders their tables
correctly. Missouri's only image pages are blank affidavit forms, so a VLM would not
change its output; Federal Way's page-5 image table is real content, which gives the
VLM stretch a measurable eval payoff.
Evidence: structural inspection of the four PDFs (2026-10-30), see ASSUMPTIONS.md.

### D10. Referenced documents are recorded, never fetched
Context: RFPs point at attachments, appendices and web pages outside the PDF.
Options: crawler/fetcher; record and flag; ignore.
Choice: extract every hyperlink and attachment reference with its section into a
`referenced_documents` list; the extractor treats a referenced-but-absent document as
a gap; the risk assessor can surface it. Fetching is a stretch goal.
Why: fetching is open-ended and a security and scope sink; the gap is itself a useful
finding (Colfax's requirements are in Attachments F and G, not provided).
Evidence: n/a.

### D11. Observability: Langfuse cloud plus a local JSON run log
Context: the assignment wants token, latency and cost tracing; Langfuse is named.
Options: Langfuse only; local log only; both.
Choice: both. Langfuse via the LangChain callback handler for per-node traces; a local
JSON run log per run with per-node tokens, latency and cost from a pricing table in
config. The eval harness and the UI read the JSON log.
Why: nothing should depend on the hosted UI being up during the demo or review.
Langfuse cloud free tier avoids a Docker dependency; tracing is a no-op without keys.
Evidence: n/a.

### D12. Repo layout and branch model
Context: several agents may work in parallel; context is cleared between steps.
Choice: living docs under `docs/`, prompts under `prompts/`, `CLAUDE.md` at root; one
long-lived `core` branch, one short-lived branch and PR per roadmap step, stretch goals
on branches off `main`. `docs/ROADMAP.md` is the only memory between sessions.
Why: the roadmap's dependency table lets independent steps run concurrently without
file conflicts; the docs folder keeps the reviewer-facing files in one place.
Evidence: n/a.

---

## Part 2 — Failure modes hit

Observed during development or evaluation. Format:

```
### F<n>. <title>
Where:     node/prompt and the RFP that triggered it
Observed:  what happened (quote the bad output if short)
Cause:     best understanding
Fix:       what changed (link the prompt changelog line or commit)
Before/after: metric, if one exists
```

(None yet. The first pipeline run on `inputs/rfp_brief.pdf` starts this list.)
