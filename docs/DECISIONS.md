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

### D16. Markdown layout, citation format, strict assembly
Context: S9 turns the JSON into the markdown a reviewer reads, and is the last place a
broken citation can be caught before it ships.
Options: citations as "section, page" only vs with the chunk ID; requirements as one
table vs grouped lists; assembler that annotates vs raises on dangling IDs; snapshot
tests vs assertion-only tests.
Choice: citations render as `(Section title, p. 4 [S3.2])`, grouping IDs that share a
section and page range; requirements grouped by type with the verbatim quote as a
blockquote; risks as a table sorted by severity then likelihood, then per-risk details;
`assemble()` raises `CitationError` listing every dangling ID with its location unless
`strict=False`, while the renderer prints a bare `[S9.9]` for an unknown ID and never
raises; one golden-file test over a fixture that hits every render branch, refreshed
with `pytest --update-golden` (author decisions, 2026-10-30).
Why: the chunk ID keeps the markdown traceable to the JSON and the UI's source reveal,
at the cost of a few characters. Quotes are long and break table rows, so a list keeps
them inline. Raising by default means a citation bug fails the run loudly instead of
shipping an unverifiable claim; the non-strict path exists so the eval harness can still
score a run with a bad citation and count it. A golden file makes any render change
show up as a reviewable diff.
Evidence: `tests/fixtures/summary_sample.md`.

### D17. Structured output: provider-native mode inside a code-owned retry loop
Context: every agent emits a Pydantic schema; providers differ in how they enforce one.
DeepSeek silently turns JSON-schema mode into tool calling, returns `parsed=None` with no
error when the model makes no tool call, and in thinking mode (its default) rejects forced
tool choice. Current Claude models reject forced tool choice but support native JSON-schema
output.
Options: provider-native `with_structured_output` per provider; one code-side path (schema
in the prompt, parse JSON text in code) for every provider.
Choice: provider-native (author decision), method picked per model by
`structured_method`: Anthropic `json_schema`; DeepSeek forced tool calling with thinking
off (default), JSON mode with the schema in the prompt when thinking is on. Around it,
code owns the loop: on a validation error or missing output the model's reply and the
error go back into the conversation (as tool results when the reply made tool calls),
bounded by `RFP_MAX_STRUCTURED_RETRIES`; a reply truncated by the output cap is not
retried; exhaustion raises with every attempt.
Why: native modes give the strongest guarantee each provider offers (forced tool calling
and Claude's JSON-schema output rarely fail validation), while the loop gives one uniform
failure contract for every agent. `extra="forbid"` on the schemas means hallucinated
fields reach the loop as errors instead of being dropped.
Evidence: live smoke tests on DeepSeek Flash pass with thinking off (389 in / 80 out
tokens, 0.9 s) and on (251 in / 115 out, 1.4 s), no retries; unit tests cover every retry
path. Thinking on vs off quality is open for S13.

### D18. Observability recording: explicit recorder in a context variable
Context: per-node tokens, latency and cost must land in a local JSON run log without
threading a logger through every agent and graph state.
Options: a LangChain callback that aggregates usage by `langgraph_node`; an explicit
recorder that `structured_call` writes to.
Choice: `RunRecorder` holds the `RunLog`; `RunRecorder.activate()` puts it in a context
variable for the duration of a run, and `structured_call` and `load_prompt` record into
whichever recorder is active. One `NodeMetrics` per logical call (retries summed into it,
recorded on failure too), aggregated per node in code. Langfuse rides alongside as a
LangChain callback, built only when both keys are set.
Why: explicit recording is testable without a graph, keeps retries and validation
failures attached to the call that caused them, and does not depend on callback
propagation details. Per-call entries keep the latency distribution visible for the eval
tables and the UI. Langfuse is lazy-imported and its trace-URL lookup is guarded because
without keys it raises.
Evidence: unit tests write and re-read the run log; live smoke test writes one.

### D19. Sampling and cost settings per provider
Context: one temperature setting for every provider; Claude Sonnet 5.5 rejects a
non-default temperature (LangChain raises before sending), DeepSeek accepts one.
Choice: the factory sends `RFP_TEMPERATURE` to every provider except Anthropic, which runs
at its default with adaptive thinking left at the model default. Cost is an upper bound:
DeepSeek peak rates, cache reads at the cached rate, cache writes at the input rate,
unknown models cost 0 with one warning (author decision).
Why: a judge must run with whatever sampling its model allows; determinism for the
generator comes from temperature 0 on DeepSeek. A clock-dependent DeepSeek price would make
the same run cost different amounts depending on when it ran, which muddies eval tables.
Evidence: factory unit tests; live smoke test cost matches the table.

### D20. Parsing: layout path with OCR off, flag thresholds as constants
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

### D21. Running headers and footers are stripped only when they repeat
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
cases; Federal Way pages 7, 9, 11 each lose exactly the 14-word header (F3).

### D22. A referenced document is present only if its section has a body
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

### D23. Gold labels: core-only scope, Claude drafts, agent corrects, diff is the record
Context: S12 needs reference requirements and problem-statement facts for four RFPs.
Hand-labelling ~250 requirements from scratch would take most of a day; an unchecked model
draft would grade the pipeline against another model's opinion.
Options: exhaustive gold (every shall-sentence, boilerplate tagged); core-only gold;
judge-only evaluation with no gold.
Choice: core-only gold (author decision): requirements that change how a bidder designs,
staffs, prices, schedules or submits; generic contract boilerplate, standard state
certifications and post-award compliance reporting are out. Claude Sonnet 5.5 drafts
from S2's parsed text (pages marked `[page N]`), items whose quote is not in the text are
dropped by code, the coding agent corrects every item against the full text, the author
spot-checks the diff in the PR. The untouched draft is committed next to the final file.
Gold has its own IDs (`GR`, `GC`) and no chunk IDs, so it survives re-chunking.
Why: recall against a core set measures what matters for the solution; precision against
a core set would punish correct extraction of boilerplate, so S12 judges precision per
item instead. Keeping the draft makes the human contribution measurable rather than
asserted.
Evidence: 19 to 26% of drafted requirements corrected per RFP, almost all removals for
scope; 5 type or strictness edits in 265 drafted items; 0 drafted quotes failed
verification (evals/gold/README.md).

### D24. Section boundaries: the outline located in the text, then markdown, then promotion
Context: citations print "section title, page", so sections must follow the RFP's own
structure. pymupdf4llm renders only about half of Missouri's 64 outline entries as `#`
headings; the rest are bold labels that open a paragraph (`**(A) Services:** The Offeror
shall ...`). Documents without an outline have headings the renderer missed (Federal Way
"SECTION 4", NYESD "A." and "iii.").
Options: markdown headings only; outline entries anchored at the top of their page; the
outline located in the text; an LLM pass to find headings.
Choice: (1) with an outline, each entry is searched by normalised title on its page, then
the next, after the previous match, never in a table row or on a contents page; it may
match a `#` heading, a leading bold run (the line stays in the body, since the rest of it
is content) or a title split over two lines; entries not found are dropped. Markdown
headings missing from the outline nest one level under the entry in effect. (2) `#`
lines over 20 words, ending in a period, or not starting like a title are paragraphs; a
short label heading followed by a same-level heading is one split title ("SECTION (1):"
+ "GENERAL DESCRIPTION ..."); a colon-ended heading with no numbering ("Name of
Respondent:") is a form label. (3) Without an outline only, a whole-bold line whose
numbering scheme (SECTION n, (A), 4.2, IV., iv., A., Task/Tab/Exhibit n) is used by a
detected heading is promoted at that heading's level (author decision). Every heading is
a section; levels come from the path, which never skips; a contents heading never parents
what follows. Text before the first heading is a "Front matter" section.
Why: the outline is the author's own structure and is free; locating it in the text
keeps cut points exact without an LLM. Promotion is limited to documents without an
outline because in outlined ones the bold numbered lines are sub-items the outline chose
not to list.
Evidence: Missouri 63/64 outline entries located (the miss, "Expenses", is a table cell);
Colfax 29/29; Federal Way SECTION 1 to 7 at one level; NYESD X. has i to xiv (tests).

### D25. Chunks: 300-word cap, cut at paragraphs, tables atomic, one sentence of overlap
Context: chunks are the unit every claim cites and the unit S5 extracts from. The LLM can
read the whole document at once, so chunk size is about citation precision and
per-chunk extraction cost, not context limits.
Options: one chunk per section; fixed-size windows with overlap; paragraph packing up to
a cap.
Choice: blocks are paragraphs and whole tables; blocks are packed greedily up to 300
words (`count_words`); a paragraph over the cap is cut at sentence ends; a table is never
cut; a last piece under 50 words joins the previous chunk; each chunk after the first
repeats the previous chunk's last sentence (author decision; not after a table, not if
over 60 words). IDs: `S<n>` numbers sections in document order and `S<n>.<k>` chunks
within a section, so the same PDF always yields the same IDs. Section kind is a separate
cheap tag (D26).
Why: paragraph cuts keep a requirement's sentence whole; the one-sentence overlap lets a
requirement that straddles a cut be quoted verbatim from one chunk, which S5's quote
check needs. Atomic tables keep schedules and pricing grids readable. Words stand in for
tokens (about 1.3 tokens per word), which avoids a tokenizer dependency.
Evidence: chunks per RFP 67 / 70 / 40 / 21 (Missouri, NYESD, Colfax, Federal Way), mean
82 to 178 words; every word of every page lands in exactly one chunk or heading line
once the overlap is removed; only two chunks exceed 300 words of their own text, both a
single table (Missouri contents, 330; Federal Way proposal format, 353) (tests).

### D26. Section kind: any obligation cue makes a section requirement-bearing
Context: the roadmap asks for a narrative vs requirement-bearing tag by cheap heuristics.
Options: cue density per hundred words with a threshold; any obligation cue; an LLM label.
Choice: requirement-bearing when the section's own text contains "shall", "must",
"required", "mandatory", "no later than" (and similar) or a line opening with an
instruction ("Describe", "Include", "Provide", ...); "will" and "should" do not count.
Why: a density threshold (tried first, at 1.5 cues per 100 words) tagged long legal
clauses that say "shall" once as narrative (17 of Missouri's 25 agreement clauses
requirement-bearing) and was an arbitrary number to defend. The tag is a hint: S5 still
extracts from every chunk, so a false positive costs nothing and a false negative hides
nothing. Imperative lines catch proposal-content lists ("- Describe how your
organization ...") that use no modal verb.
Evidence: Missouri agreement clauses 21/25 requirement-bearing (the four left say "may"
or "encouraged"); Colfax 1.1 and Federal Way Section 2 background narrative; NYESD
"C. Project Plan" requirement-bearing (tests).

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

### F1. DeepSeek thinking mode rejects forced tool choice
Where: `structured_call` on `deepseek:deepseek-flash`, S1 live smoke test.
Observed: `400 - Thinking mode does not support this tool_choice`.
Cause: thinking mode is on by default for DeepSeek's current models, and LangChain's
tool-calling `with_structured_output` forces the tool.
Fix: `RFP_DEEPSEEK_THINKING` (default off) sets `extra_body.thinking`; with thinking off
the forced tool call works, with thinking on `structured_call` switches DeepSeek to JSON
mode with the schema in the prompt (D17).
Before/after: live smoke test failed, then passed in both modes.

### F2. Mangled plain-text URLs duplicated real links
Where:     S2 hyperlink extraction, NYESD.
Observed:  39 links where the document has 32; e.g. both
           `.../file-your-vendor-responsibility-questionnaire` (annotation) and
           `.../file-your-vendor-responsibilityquestionnaire` (text layer).
Cause:     the text layer drops hyphens and inserts spaces where long URLs wrap; the
           plain-text URL only differed from an annotation on another page.
Fix:       compare URLs on letters and digits only, against every annotation in the
           document, and drop a plain-text URL that equals or prefixes one.
Before/after: 39 to 32 NYESD links; test asserts no two links share a key.

### F3. Running header survived on three Federal Way pages
Where:     S2 header/footer stripping, Federal Way p7, p9, p11.
Observed:  "City of Federal Way, WA - RFP for ERP Software 7 | P a g e **SECTION 4..."
           left in the page markdown.
Cause:     the layout model merged the header with the heading below into one box (p7,
           p9; on p9 classed as text and extending below the margin band) or split it in
           two header boxes (p11), so the whole-box repeat rule did not match.
Fix:       strip a repeated header as a prefix of a box that starts in the top band, and
           strip header-classed boxes whose text is a fragment of a repeated header.
Before/after: 3 pages with the header to 0; other documents' word counts unchanged.

### F4. Judge returned 3 checklist facts instead of 8 to 12
Where:     S11 `gold_checklist` prompt, Missouri and NYESD (first draft run).
Observed:  3 facts each (who, need, goal) although the prompt asks for 8 to 12; Colfax
           and Federal Way returned 12.
Cause:     the count was only an instruction; nothing in the schema or code enforced it, so
           structured_call accepted the short list.
Fix:       a field validator on the draft model (not minItems in the JSON schema, which
           provider structured output supports unevenly) rejects a list outside 8 to 12;
           structured_call feeds the error back and retries. Test added.
Before/after: 3 to 12 facts for Missouri and NYESD on redraft.

### F5. NYESD requirements draft truncated at 16,000 output tokens
Where:     S11 `gold_requirements` on NYESD (redraft), Claude Sonnet 5.5.
Observed:  `StructuredOutputError: output truncated by the token cap; not retrying`.
Cause:     the longest RFP (10k words) plus adaptive thinking, which counts toward
           max_tokens, exceeded 16,000.
Fix:       drafting cap raised to 32,000 with a 600 s timeout (drafting only; pipeline
           settings unchanged).
Before/after: failed to 61 requirements drafted.

