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

### D13. Model ids and pricing source
Context: the scaffold fixes the default generator and judge and a pricing table for
cost accounting. DeepSeek's documented API ids changed: `deepseek-chat` is no longer on
the pricing page; the current ids are `deepseek-flash` (V4.1 Flash) and `deepseek-v4-pro`.
Options: deepseek-flash vs deepseek-v4-pro as generator; claude-opus-5-5 vs
claude-sonnet-5-5 as judge; peak vs off-peak DeepSeek rates in the table.
Choice: `deepseek:deepseek-flash` generator, `anthropic:claude-sonnet-5-5` judge (author
decisions, 2026-10-30); DeepSeek peak rates in `PRICING` as the upper bound, Claude
first-party rates (opus 5.5 $4/$20, sonnet 5.5 $2/$10, haiku 5.5 $0.10/$0.50 per 1M).
Why: Flash is the cheapest model with a 1M context, enough for structured extraction over
documents that fit one window; the model is one env var away if evals show it is too
weak. Sonnet halves judge cost against Opus and keeps the judge in a different family
from the generator (D3). Peak pricing never under-reports cost.
Evidence: none yet; S12 reads the run logs.

### D14. Schema conventions
Context: `schemas.py` is the contract between every step and the thing most likely to be
changed live in the follow-up interview.
Choice: every model forbids extra fields; closed sets are `StrEnum`s; IDs are
regex-checked strings (`S3.2`, `R001`, `A01`, `G01`, `C01`, `K01`); `Claim` is the one
citation unit (`text`, `kind` fact|inference, `chunk_ids` at least one); `Requirement`
carries the verbatim quote, `quote_verified`, `merged_from` and `conflicts_with`;
`Coverage` is a separate model so code, not the LLM, fills it; `RunLog.totals()` sums
per-node metrics. Requirement types: 8 values; strictness: mandatory/desired/optional;
risk severity and likelihood: low/medium/high.
Why: `extra="forbid"` makes a hallucinated field a validation error that the
structured-call retry can feed back, instead of silent data loss. Regex IDs make a bad
citation fail at parse time. Three-level scales are easier for a judge to agree with
than numeric ones. Adding a requirement type is a one-line enum change, which is the
planned live-change rehearsal.
Evidence: n/a.

### D15. Install and config mechanics
Context: one env for the author, reviewers and CI; config must be one setting for
provider and model.
Choice: `requirements.txt` pins every direct dependency and ends with `-e .`, so one
`pip install -r requirements.txt` yields an importable `rfp_agent`; `pyproject.toml`
holds no dependency list. Config is pydantic-settings with an `RFP_` prefix for app
settings and the providers' own names for keys; the model spec is `provider:model_id`,
the format LangChain's `init_chat_model` accepts.
Why: a single install command and a single source of pins; no `PYTHONPATH` tricks.
pydantic-settings keeps validation (ranges, types) in the same library as the schemas.
Evidence: CI runs the same install.

### D16. Parsing: layout path with OCR off, flag thresholds as constants
Context: pymupdf4llm 1.28.2 ships a layout model (`pymupdf.layout`) that returns page
boxes (text, section-header, table, picture, page-header, page-footer) and turns OCR on
by default when Tesseract is installed. S4 needs flags on suspicious pages.
Options: OCR on (default); OCR off with flags; flags from layout boxes or from pymupdf
directly.
Choice: `use_ocr=False`; flags from four code rules with thresholds set by inspecting
the four RFPs: fewer than 50 words; an image covering at least 25% of the page; a table
whose rows have different column counts or that collapsed to one column with
`<br>`-merged cells; at least 6 prose lines of at most 2 words making up half the prose.
Image sizes come from `get_image_info()`, not the layout boxes.
Why: with OCR on, output would depend on whether the machine has Tesseract, so CI and a
reviewer's laptop could disagree; image pages are what the S4 judge and the VLM hook
exist for. The thresholds separate the known cases: Missouri's affidavit forms (54% of
the page) and Federal Way's image table (42%) from cover logos (8% to 14%).
Evidence: four-RFP tests; flagged pages listed in the S2 roadmap entry.

### D17. Running headers and footers are stripped only when they repeat
Context: running headers ("City of Federal Way, WA - RFP for ERP Software 5 | Page") and
footers ("Page 6 of 22", bare numbers) pollute chunks and quotes. The layout model
classes most of them, but sometimes calls one ordinary text, merges it with the heading
below, or splits it in two.
Options: keep everything; drop every box the model calls header/footer; drop only
text that repeats.
Choice: a box is a candidate if the model classed it header/footer or it sits in the top
or bottom 12% of the page; a candidate is removed if its text, with digits and markup
removed, recurs as a header/footer on at least 3 pages or is empty (a page number). A
repeated header merged with a heading loses only the header prefix; a header-classed
fragment of a repeated header is removed.
Why: repetition is what makes a line a running header, so a one-off sentence the model
misclassified survives. The author chose stripping over keeping everything.
Evidence: Missouri, NYESD and Colfax word counts unchanged by the prefix and fragment
cases; Federal Way pages 7, 9, 11 each lose exactly the 14-word header (F2).

### D18. A referenced document is present only if its section has a body
Context: RFPs name attachments and exhibits; some are in the PDF, some are cover pages
saying "separate document", some are image-only forms.
Options: present when a matching heading exists; heading plus a minimum body; always
false in S2.
Choice: present when a heading titled with the reference name (e.g. "ATTACHMENT F: ...")
is followed by at least 40 words before the next heading of the same or higher level
(author decision). References are matched by regex: keyword (attachment, appendix,
exhibit, schedule, addendum) plus a single capital letter or number, so "Schedule of"
and "Addendum to" do not match. Each reference keeps its first occurrence outside a
table of contents and that line's section.
Why: Colfax Attachment F holds the software requirements but its page only says the
spreadsheet is provided separately; a heading-only rule would call it present and hide
the most important gap in that RFP.
Evidence: Colfax A-D present, E-G absent; Missouri Exhibits absent; Federal Way Exhibits
present (tests).

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

### F1. Mangled plain-text URLs duplicated real links
Where:     S2 hyperlink extraction, NYESD.
Observed:  39 links where the document has 32; e.g. both
           `.../file-your-vendor-responsibility-questionnaire` (annotation) and
           `.../file-your-vendor-responsibilityquestionnaire` (text layer).
Cause:     the text layer drops hyphens and inserts spaces where long URLs wrap; the
           plain-text URL only differed from an annotation on another page.
Fix:       compare URLs on letters and digits only, against every annotation in the
           document, and drop a plain-text URL that equals or prefixes one.
Before/after: 39 to 32 NYESD links; test asserts no two links share a key.

### F2. Running header survived on three Federal Way pages
Where:     S2 header/footer stripping, Federal Way p7, p9, p11.
Observed:  "City of Federal Way, WA - RFP for ERP Software 7 | P a g e **SECTION 4..."
           left in the page markdown.
Cause:     the layout model merged the header with the heading below into one box (p7,
           p9; on p9 classed as text and extending below the margin band) or split it in
           two header boxes (p11), so the whole-box repeat rule did not match.
Fix:       strip a repeated header as a prefix of a box that starts in the top band, and
           strip header-classed boxes whose text is a fragment of a repeated header.
Before/after: 3 pages with the header to 0; other documents' word counts unchanged.

(The first pipeline run on `inputs/rfp_brief.pdf` continues this list.)
