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

### D24. Parse quality: two-boolean verdict, attribution by match, flags replaced
Context: S2's heuristics flag 12 pages across the four RFPs; most are covers, contents
pages and short attachment dividers. Downstream steps (S8 risks, S9 parse-flags table)
should see only real damage, and the roadmap asks that every escalation records whether
code or the model triggered it.
Options: a single `usable` boolean; ok/degraded/unusable scale; two booleans. Keep S2's
flags and add a report beside them; or replace them with judged flags. Judge with the
generator or with Claude.
Choice (author decisions): one generator-model call per flagged page (all flags on the
page in one call) returning `PageJudgement`: `text_usable` (the text represents the page),
`content_missing` (the page holds content the text lacks, typically in an image),
`page_kind`, `confirmed_flags`, one-sentence `reason`. Code decides: not bad clears the
page (`code`, `confirmed_bad=False`); bad with at least one confirmed heuristic flag keeps
those flags and calls the VLM hook (`code`); bad with no confirmed flag replaces the
page's flags with an `other` flag carrying the reason (`model`). `confirmed_flags` is
intersected with the page's real flags, so an invented flag name cannot survive. The pass
returns a copy of the `ParsedDocument` holding only surviving flags plus a
`ParseQualityReport`; every escalation also goes on the run log. A judge call that fails
after retries keeps the page's flags. The VLM hook is a `(page, judgement) -> action`
callable; core records "would escalate to VLM", ST2 swaps in transcription.
Why: a single boolean conflates "the text is garbled" with "the text is fine but a table
is in an image" (Federal Way p5), which the two booleans separate; the decision rule lives
in code so the attribution is auditable and testable without a model. Replacing flags
keeps later steps simple; the report and run log keep the full audit. Failing safe means
a flaky judge can hide nothing. The generator judges because it is a pipeline node; the
Claude judge stays reserved for evaluation (D3).
Evidence: live on DeepSeek Flash, 12 pages judged, 0 retries, $0.0047 and 4 to 8 s per
document; 9 false alarms cleared (Colfax p1, p2, p3, p20, p21, p22; Federal Way p2, p14;
Missouri p12) and 3 escalated (Missouri p19, p20; Federal Way p5), matching the manual
inspection in S2 exactly. The `model` path is exercised only by unit tests so far.

### D25. Section boundaries: the outline located in the text, then markdown, then promotion
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

### D26. Chunks: 300-word cap, cut at paragraphs, tables atomic, one sentence of overlap
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
cheap tag (D27).
Why: paragraph cuts keep a requirement's sentence whole; the one-sentence overlap lets a
requirement that straddles a cut be quoted verbatim from one chunk, which S5's quote
check needs. Atomic tables keep schedules and pricing grids readable. Words stand in for
tokens (about 1.3 tokens per word), which avoids a tokenizer dependency.
Evidence: chunks per RFP 67 / 70 / 40 / 21 (Missouri, NYESD, Colfax, Federal Way), mean
82 to 178 words; every word of every page lands in exactly one chunk or heading line
once the overlap is removed; only two chunks exceed 300 words of their own text, both a
single table (Missouri contents, 330; Federal Way proposal format, 353) (tests).

### D27. Section kind: any obligation cue makes a section requirement-bearing
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

### D28. Problem statement: code-owned chunk IDs in stage one, schema-validated citations in stage two
Context: the problem statement is the output where unsupported claims are most tempting
(the model is asked to say why the client is buying), and the traceability rule says every
fact cites a chunk ID that exists.
Options: let the model echo chunk IDs in both stages and check them afterwards; group
several chunks per stage-one call; check citations in code after the call and drop bad
ones; check citations inside the structured-output retry loop and fail on exhaustion.
Choice: stage one is one call per chunk with the chunk ID attached by code, so there is
nothing to validate; synthesis sees only the relevant summaries, labelled with their IDs,
and its output schema is a per-call subclass of `ProblemStatement` whose validator rejects
an empty list or an ID outside the evidence. `structured_call` feeds the message back and
retries; after the budget the node raises. Stage one runs in a thread pool
(`RFP_LLM_CONCURRENCY`, default 4). The full-text baseline is the same synthesis prompt
over the own text of every chunk with the same labels.
Why: an ID the model never writes cannot be wrong, and one call per chunk keeps that
property at the cost of about seventy cheap calls per RFP ($0.01 to $0.04 on DeepSeek
Flash, 30 to 60 s with four workers). Putting the citation check in the schema reuses the
one retry mechanism the pipeline has (the F4 pattern) and gives the model a precise
correction ("constraints cites chunk IDs that are not in the evidence: ['S45.3']") rather
than a silent drop that evals would never see. Failing on exhaustion is deliberate: a
problem statement with an unverifiable claim is worse than no problem statement, and the
run log records the spend. Keeping the baseline's prompt identical makes the S13 comparison
about hierarchy alone.
Evidence: four RFPs, both modes: every citation resolves, no stage-one failure, the
validator retried once in 2 of 4 NYESD runs and succeeded; rough checklist coverage 12/12
hierarchical, 11 to 12/12 full text (ROADMAP S6 table). Quality comparison is S13's.
### D29. Quote verification: one feedback turn, then keep the item as unverified
Context: every requirement carries a verbatim quote that code must be able to find in
the cited chunk (traceability rule); models paraphrase, fix typos and join table cells.
Options: drop items whose quote is not found; keep them silently; retry with the failing
quotes named, then drop; retry, then keep flagged.
Choice: after the schema-valid reply, code checks each quote with `find_quote` (the S11
normaliser, now in `rfp_agent.textmatch`). If any fails, the model gets one more turn
with the failing quotes listed; the retry is kept only if it has no more problems than
the first reply. Items still unverified stay in the output with `quote_verified=False`.
Why: a sloppy quote does not make the obligation disappear, and dropping it would hide
a real requirement from the solution step; flagging it keeps the evidence honest and
lets the renderer and the eval treat it differently. The "no worse" rule stops a second
turn from regressing a mostly-good first reply. One turn is enough in practice (below)
and bounds the cost at two calls per chunk.
Evidence: on the four RFPs (198 chunks) one feedback turn fired and fixed its quote;
zero unverified items shipped. The check also catches table-cell joins
(`"Submission of Proposals(date and time)|October 1,2025<br>by2:00 PM ET"` verifies
because the normaliser strips pipes and tags).

### D30. Grouping contract checked by code, violations fed back once, then sanitised
Context: D6 chose one LLM grouping pass for fuzzy dedupe and demanded that every ID land
in exactly one group. Models put an ID in two groups, invent IDs, or list the
representative among its members.
Options: trust the grouping; assert and abort; retry until clean; retry once, then make
the answer valid in code.
Choice: `check_groups` lists violations in plain sentences; the model gets one feedback
turn; whatever comes back goes through `sanitise_groups` (unknown IDs dropped, first
membership wins, a conflicting member leaves the group, empty groups vanish) so the
merge step only ever sees a valid grouping. The report records the violations and
whether the fallback was used. Conflicts are never merged: the pair is marked on both
items and surfaced as an ambiguity.
Why: the invariant must hold for S7's coverage arithmetic, and it is cheaper to hold it
by construction than by looping. "First membership wins" loses at most a merge, never a
requirement. The feedback turn is worth its one extra call: on three of four RFPs the
first grouping violated the contract and the second was clean.
Evidence: first Missouri run: `R030 appears in group 6 and group 9`, `... group 10`,
`R031 ...`, `R127 ...` on both turns, fallback used, output still valid (the 60-round
random-grouping test asserts the invariant). After the dedupe prompt gained "an ID may
appear once across the whole answer", all four reruns were clean after at most one turn.

### D31. Extraction scope mirrors the gold scope; everything else is left to S12
Context: the gold labels are core-only (D23). An extractor that lists every clause of
Missouri's 24-clause agreement section would bury S7 in boilerplate, and an extractor
that is stricter than gold loses recall S12 cannot see.
Options: extract everything and filter later; extract core-only with the gold prompt's
include/exclude rule; two passes (all, then classify).
Choice: the extraction prompt carries the gold prompt's include/exclude list verbatim,
with the boilerplate examples expanded after the first live run (assignment,
independent-contractor status, audit rights, transparency reporting, one item per form
rather than per field). Every chunk is still sent (D5); only the prompt's notion of
"requirement" narrows.
Why: recall against gold becomes like for like, and S7 reads a list a bidder would
recognise. Precision is judged per item in S12, so a kept boilerplate clause costs
nothing in the score; the surplus (90 to 216 items against 46 to 71 gold) is a quality
question for S13, not a correctness one.
Evidence: Missouri 144 → 131 requirements after the expanded exclusions (legal 33 → 20),
crude recall 89% → 86% (within run-to-run noise: the "lost" items are the same
requirements with different spans). Four-RFP table in the roadmap, S5.

### D32. Solution coverage computed by code, revised in a capped LangGraph loop
Context: the solution generator is where a model most easily writes a confident
approach that silently skips half the obligations. The roadmap demands that coverage of
mandatory requirements be computable by code, and the assignment grades agentic depth.
Options: one call and report whatever coverage results; ask the model to self-report
coverage; a code-checked feedback turn (the S5 `verified_call` pattern); a LangGraph
loop that revises while uncovered requirements remain, with a round cap.
Choice: the model sees the problem statement, the requirements (one line each, no
quote), the ambiguities and the gaps, never the RFP text, and returns a `SolutionDraft`
whose components cite requirement IDs. A per-call schema subclass rejects an empty
component list, a component citing nothing, and any requirement or chunk ID outside the
inputs inside the `structured_call` retry (D28). `compute_coverage` counts the mandatory
requirements cited by at least one component, with type `submission` excluded (the
author's call: proposal format and copies are context, not scope). A three-node
LangGraph (`generate` → `check` → `revise` → `generate`) feeds the uncovered IDs with
their text back in the same conversation while any remain and the round cap
(`RFP_SOLUTION_MAX_ITERATIONS`, default 3) is not reached; the draft with the fewest
uncovered requirements is kept, and what is still uncovered is listed for the risk
assessor. Component IDs are assigned by code.
Why: coverage is the one solution metric code can own, so it drives the only loop. The
loop is LangGraph rather than a hand-written `for` so S10 nests it as a subgraph and the
Langfuse trace shows each round as a node; the cap keeps cost bounded and the
best-draft rule makes a bad revision harmless. Sending no chunk text keeps the solution
honest about its sources: everything it can say about the client is already a cited
claim or requirement, so a fact it needs and does not have must become a labelled
assumption. Quotes were left out because the normalised text is already verified and
the block would double in size for no design signal.
Evidence: Missouri, DeepSeek Flash: round one covered 74 of 76 in-scope mandatory
requirements, the revision covered 76 of 76; two calls, $0.017, 44 s summed latency, no
validator retry. The two IDs the revision added (R007, R019) are proposal-process
obligations typed `timeline` by S5, so the model wrapped them in a commercial
component; see S7 open issues. Four-RFP table in the roadmap, S7.

### D33. Risks: findings computed by code, must-address checked in the schema, one call
Context: the risk assessor is the last agent and the one most tempted to write generic
project risks. The roadmap lists what it must cover (timelines, vague or conflicting
requirements, missing budget, referenced-but-absent documents, flagged pages, risks the
solution creates), asks that code validate IDs, and leaves the scales to this step.
Options: send the RFP text again; let the model find everything; a code-detected
findings block the model must address; a generate → check → revise loop as in S7.
Choice: no RFP text (the S7 rule). Code computes a findings block before the call: the
mandatory requirements S7 left uncovered, the conflict pairs S5 flagged, the referenced
documents the parser marked absent (hyperlinks excluded), the parse flags that survived
the S4 judge, and the count of budget requirements. The model sees it first, then the
solution (components with their requirement IDs and claims, assumptions, coverage), the
problem statement, all requirements (submission items under a plain heading, since
deadlines are risks), ambiguities and gaps. A per-call `RiskAssessmentDraft` subclass
rejects fewer than 3 or more than 15 risks, unknown requirement or chunk IDs, and a
draft in which an uncovered mandatory requirement is cited by no risk (the author's
call: only the finding with a citable ID is enforced; conflicts, documents and pages are
advice). One call, no loop; the retry is the feedback loop. Scales: severity is impact
(`high`: the project fails, a contractual date is missed or the budget overruns by more
than a quarter; `medium`: rework or cost contingency absorbs; `low`: normal delivery);
likelihood is judged given the RFP and the solution as written (`high`: expected unless
someone acts; `medium`: turns on facts the RFP does not settle; `low`: an unusual
event). Code sorts by severity then likelihood and numbers `K01…`, so the JSON order is
the rendered table order.
Why: the findings block turns the step from "think of risks" into "explain these facts
and add what they imply", which is where a 20k-token context earns its keep; the model
still brings judgment code cannot (Missouri's IS-approval gate on the proof of concept,
NYESD's 250-versus-400 participant floor). Enforcing only the uncovered IDs keeps the
validator honest: it can check an ID, it cannot check that a page was "considered". No
loop was built because nothing in a risk list is computable the way coverage is; the
count band and the must-cite rule are the whole contract, and one call costs a cent.
Three-level scales with written definitions give S12's judge something to agree with
(D14).
Evidence: four RFPs, DeepSeek Flash, one call each, 0 validator retries, $0.007 to
$0.011 and 19 to 22 s; 12 to 13 risks per RFP; every code finding surfaced as a risk
(table in the roadmap, S8). No uncovered mandatory requirement reached S8 because S7's
loop closed them all, so the must-cite rule is exercised by the unit tests only.

### D34. One LangGraph graph of thin stage wrappers; runtime objects in closures, outputs on disk per stage
Context: S2 to S9 each ship a function that takes `settings`, `recorder` and a LangChain
`config`; the S8 debug CLI already chains them by hand. S10 must make that one graph
with the S5/S6 fan-out, per-stage observability and a progress surface for the UI, and
produce the first end-to-end outputs.
Options: (a) a `StateGraph` whose nodes are the existing functions, called directly;
(b) nest S7's compiled loop as a subgraph and move every agent's internals into graph
nodes; (c) no graph, a plain function calling the stages in order with a thread for the
fan-out. For progress: LangGraph stream modes (`updates`, `debug`) versus a callback
from the node wrappers. For where intermediates live: in memory only, or written as
each stage finishes.
Choice: (a). Eight nodes (`parse`, `parse_quality`, `split`, `requirements`, `problem`,
`solution`, `risk`, `assemble`); `split` fans out to `requirements` and `problem`, which
join at `solution`. Every node is the same wrapper around a stage function: it emits a
`StageEvent` (started / finished / failed, wall time, the stage's LLM calls and cost) to
an optional callback, records a `StageRecord` on the run recorder (`RunLog.stages`, an
additive change to the S1 schema), and writes the stage's output JSON into the run
directory before returning. Settings, the one shared chat model, the recorder and the
callback are bound in closures by `build_pipeline`; the state carries only documents
and results. S7's revision loop stays a function call, since `build_solution` already
runs its compiled graph with the same `config`, so tracing nests it. A stage's LLM
calls are found by node-name prefix (`requirements_`, `problem_`, ...), so per-stage
cost needs no second accounting. The CLI maps a failure to exit 1 with the stage named,
and `activate()` writes the run log on the way out either way.
Why: the agents' internals are already tested at their own level, so wrapping them
keeps the graph small enough to explain in a minute and keeps S14's job to
"subscribe to the callback and serve the files". A callback works from the executor
threads the fan-out runs on, and it costs nothing when absent; parsing LangGraph's
stream formats in the UI would couple S14 to LangGraph's event shapes. Writing
intermediates per stage makes a failed run diagnosable (the log says which stage and
why, the earlier outputs are on disk) and gives the UI and the evals one place to read
from. Reading the recorder from the contextvar inside nodes would also have worked
(LangGraph copies the context into its executor threads) but explicit binding does not
depend on that.
Evidence: first end-to-end runs on the four RFPs, one each, DeepSeek Flash: every
stage finished, $0.048 to $0.101 and 79 to 110 s wall per RFP ($0.28 and 6.3 minutes in
all), 0 to 1 structured-output retry per run, all mandatory requirements in scope
covered, every citation resolving under strict assembly. The requirements and
problem-statement branches took 21 to 48 s each and overlapped, so the middle of the
run costs one branch's time. A stubbed-stage test holds both branches at a barrier to
prove they run concurrently, and a forced failure in the solution stage leaves the
log with the stage marked failed, the error text, and the requirements and problem
JSON on disk. Table in the roadmap, S10; samples under `runs/samples/`.

### D35. UI backend: a thin FastAPI layer over `run_pipeline`, one worker, events through a condition variable
Context: S15 needs to start a run, watch it live with per-stage metrics, and read every
intermediate output, the summary and the cited chunks. S10 already writes each stage's
JSON as it finishes and calls back with `StageEvent`s from LangGraph's executor threads.
Options: for execution, one worker thread, a thread per run, or refusing uploads while
busy (409). For streaming, per-subscriber `asyncio.Queue`s fed by
`loop.call_soon_threadsafe`, or one event list under a `threading.Condition` read with a
cursor from `asyncio.to_thread`. For SSE, `sse-starlette` or a hand-written
`StreamingResponse`. For run status, track it in memory only, or read it from
`run_log.json` once the run ends.
Choice: `ui/backend/` is a FastAPI app built by `create_app`. A
`ThreadPoolExecutor(max_workers=1)` runs one pipeline at a time, and later uploads wait
as `queued`. Each run's registry entry holds the events in a list under a `Condition`.
The pipeline callback appends and notifies. An SSE reader calls `wait(cursor, 15 s)`
on a worker thread and yields what came after its cursor, a keepalive comment when
nothing came, and `done` at the end. The SSE is about 20 lines over
`StreamingResponse`. The chat model is built when the upload is accepted, so a missing
key is a 503 before anything is written. Once a run ends, its status comes from
`run_log.json`, the same path that serves the committed samples and runs from earlier
processes. Artifacts are served from disk with `FileResponse`. Only `split.json` is
parsed, and it is cached, for chunk lookup. The four samples resolve as runs, so the
UI and the demo work with no key. `rfp_agent` gains no web dependency.
Why: one worker keeps rate limits and spend predictable, since a run already makes up
to eight concurrent LLM calls. Queueing is friendlier than a 409 and costs one line.
The single cursor-indexed list makes replay and live delivery one code path. A client
that connects mid-run gets every earlier event and no duplicates. The worker thread
needs no event-loop reference, which is exactly what S10's thread-safe-callback
contract asks for. The cost is one blocked thread per open stream for at most 15 s,
which does not matter for a single-user tool. Reading status from the log means a
finished live run, a sample and a run from yesterday look the same to the frontend.
Hand-written SSE and plain `uvicorn` avoid two dependencies for about 20 lines of code.
Not done: cancel and delete, because LangGraph threads cannot be stopped cleanly; auth,
because this is a local tool; and resuming runs across restarts.
Evidence: 27 tests with the LLM stages stubbed. A run held at a gate proves queueing
and a mid-run subscription that receives the replayed and live events and closes on
`done`. A forced failure keeps the earlier outputs. One live Federal Way run through
the API cost $0.050 over 82 s. `curl -N` printed every stage as it happened, with
keepalives during the 32 s solution stage and the two branches starting together.
Details in the roadmap, S14.

### D36. UI frontend: views built from per-stage artifacts, source reveal in a slide-over, the browser's PDF viewer
Context: S15 must show a run live, every intermediate output, and the source of any
cited claim, on top of the S14 API. The author chose a React view built from JSON over
rendering `summary.md`, and the browser's PDF viewer over pdf.js.
Options: for data, read `summary.json` once the run ends, or each stage's artifact as it
appears. For source reveal, navigate to a source page, use a modal, or use a
slide-over that keeps the reading position. For highlighting, mark the quote on the PDF
(pdf.js text layer), or in the chunk text beside the PDF. For state, use a store
library, or hooks and one context.
Choice: each tab reads the artifact of the stage that writes it, fetched as soon as it
appears in `status.artifacts`. A run index (chunks from `split.json`, requirements,
components, risks, ambiguities, gaps) is rebuilt from whatever exists. Every ID renders
as a chip that opens a right-hand slide-over with a history stack. The panel shows the
item, its cited chunks and the quote highlighted in the chunk text, and the PDF in an
iframe at `#page=N`. Quote matching folds case, curly quotes, dashes, whitespace and
`*` and maps back to the original indices. Live progress is one `EventSource` feeding
a latest-event-per-stage reducer, which is idempotent, so reconnects and disk replays
need no special case. There is no store library: two hooks and a `SourceContext`.
Why: per-stage artifacts make the live run useful before it ends. Requirements are
readable 30 s in, while the solution is still being written. They also let the
backend's chunk text come from one 90 kB file instead of one request per click. The
slide-over keeps the user's place in a long table, which matters for 120 to 223
requirements. Highlighting in text works the same in every browser and is testable on
real data. Highlighting on the PDF would need pdf.js and coordinate matching for a
small gain. A latest-event reducer matches the API's replay-then-live contract exactly.
Not done: pdf.js highlighting, cancel and delete (the API has none), an SSE stream for
the run list (polling while busy), and visual polish beyond four Playwright passes
(ST1).
Evidence: 11 Vitest tests, including quote highlighting for at least 95% of Missouri's
verified quotes in a cited chunk, and the index built from the committed sample.
Playwright MCP passes at 1440 px and 390 px fixed 13 issues, among them a 456 px
overflow on phones and a blank page from F13. One live Colfax upload through the UI
cost $0.0556 over 83 s, and the timeline and every tab filled in without a reload.
Details in the roadmap, S15.

---

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

### F6. Synthesis claims spoke of "the evidence" instead of the RFP
Where:     S6 `problem_synthesis` prompt, first live run on the four RFPs.
Observed:  three of four hierarchical statements contained a constraint such as "The RFP
           refers to documents not included in the evidence that bidders must obtain" and
           Federal Way's client situation said the systems were "not reproduced in the
           summarized text".
Cause:     the prompt names its input "evidence" and told the model to cite only evidence
           IDs; the model carried the framing into the claims, which a bid team cannot
           use.
Fix:       one rule added to the prompt: write about "the RFP", never "the evidence", "the
           summaries" or "the chunks", and do not speculate about what the RFP may say
           elsewhere.
Before/after: 3 of 4 outputs affected to 0 of 2 re-runs (NYESD, Federal Way).

### F7. Citation validator retry with no recorded cause
Where:     S6 `problem_synthesis` on NYESD, 2 of 4 live runs.
Observed:  `retries = 1` in the node metrics; the INFO line read "attempt 1 failed: 1
           validation error for ProblemStatement" and was cut at 200 characters before
           the list name and the offending IDs; the two later runs did not retry.
Cause:     `structured_call` logs the error truncated and `NodeMetrics` stores the retry
           count only; DeepSeek Flash is not deterministic at temperature 0, so the
           retry could not be reproduced on demand (60 to 63 relevant chunks across runs).
Fix:       not fixed in S6 (the schema is S1's). Open issue for S12/S13: record the last
           validation error on `NodeMetrics` so a retry is diagnosable from the run log.
Before/after: n/a.

### F8. Extractor reported other sections of the same RFP as ambiguities and gaps
Where:     S5 `requirements_extract` prompt, Missouri (first live run).
Observed:  105 ambiguities and 39 gaps for 144 requirements. Typical: "The specific
           data items required are in paragraph (B), which is not included in this
           chunk"; gap "Section (3), paragraph I ... is referenced but not included in
           this chunk"; blank affidavit forms that are in the PDF listed as gaps.
Cause:     the chunk-local prompt said "work only from the text you are given", and the
           model took "not in this chunk" as "missing from the RFP". The gap definition
           ("a document referred to but not included here") invited it.
Fix:       ambiguities and gaps each got a "not this" list: content defined in another
           part of the same RFP (other chunks are handled separately) and ordinary lack
           of detail are neither; gaps are documents outside the RFP only; "most chunks
           have none". Boilerplate exclusions expanded at the same time (D31).
Before/after: Missouri 144 / 105 / 39 (requirements / ambiguities / gaps) to
           131 / 53 / 12; crude recall 89% to 86% (same items, different spans).

### F9. NYESD gaps listed every form twice, by name and by URL
Where:     S5 `requirements_extract` prompt, NYESD (63 hyperlinks, most to forms).
Observed:  50 gaps; "Executive Order 16 Certification" (G12) and
           "https://esd.ny.gov/sites/default/files/EO16-certification.pdf" (G29) are
           the same document; code dedupes by normalised name, so neither folded.
Cause:     `referenced_document` was described as "the name as written (or the link
           text)", and link text in NYESD is the URL.
Fix:       prompt: "the document's name as written, never its URL; a document named
           once with its link is one gap". Code: gaps whose names are prefixes of each
           other at a word boundary fold ("Attachment F" with
           "ATTACHMENT F: SOFTWARE ABILITIES AND REQUIREMENTS", a Colfax pair).
Before/after: NYESD 50 to 38 gaps (the rest are distinct forms the RFP really links).

### F10. Solution assumptions cited ambiguity and gap IDs as chunk IDs
Where:     S7 `solution` prompt, `solution_generate`, Colfax and Federal Way (not
           Missouri or NYESD).
Observed:  `assumptions cites chunk IDs that are not shown in the inputs: ['A02', 'A03',
           ..., 'G06', 'G07', ...]` on attempt one; attempt two, with the validator's
           message fed back, cited the chunk IDs and passed.
Cause:     the prompt said "`chunk_ids` copied from the ambiguity or gap it resolves",
           and the nearest ID on that line is the ambiguity's own `A02`.
Fix:       prompt: `chunk_ids` holds the chunk IDs `(S4.2)` listed in parentheses after
           the ambiguity or gap; ambiguity and gap IDs are never cited (changelog
           2026-10-30). The validator already made the output safe; the fix saves the
           retry.
Before/after: 2 of 4 first runs needed the retry; four-RFP rerun on the tuned prompt in
           the roadmap, S7.

### F11. DeepSeek returned no tool call on a revision turn
Where:     S7 `solution_revise`, Federal Way, the revision round (history: prompt, the
           model's own 6k-token answer, the coverage feedback).
Observed:  `attempt 1 failed: No structured output was returned. Reply with exactly one
           output that matches the required schema.`; attempt two returned the tool
           call and passed.
Cause:     not known; a plain-text reply instead of the forced tool call on a long
           multi-turn history. Seen once in eight solution calls.
Fix:       none needed: `structured_call` already treats a missing tool call as a
           retryable attempt and feeds the instruction back. Noted so S12's retry
           counts have a known cause.
Before/after: one retry, $0.01.

---

### F12. Risk count ran over the asked range on every RFP
Where:     S8 `risk_assess`, all four RFPs, first prompt.
Observed:  13 risks on each of the four RFPs against "six to twelve risks" in the
           "What to return" line; inside the validator band (3 to 15), so no retry.
Cause:     the count sat in a field description while the Rules section said each
           finding "deserves a risk"; with 7 to 10 code findings plus the model's own,
           the rules outweighed the range.
Fix:       a **Count** rule under Rules ("at most twelve; merge or drop; code rejects
           more than fifteen"). Partial: Missouri and Federal Way returned 12, NYESD and
           Colfax still 13. The band in the schema stays the contract; the range is
           advice. S13 can tighten the band if the judge finds the tail risks weak.
Before/after: 13, 13, 13, 13 → 12, 13, 13, 12; cost and latency unchanged ($0.04 for
           the rerun).


### F13. Vite's dev transform dropped an exported function named `displayName`
Where:     S15 frontend, `RunList.tsx`, in the dev server only (`npm run build` was fine).
Observed:  a blank home page; console `ReferenceError: displayName is not defined`.
           The served module called `displayName(...)` but no longer defined it.
Cause:     React Fast Refresh treats `displayName` as a component property, and the
           dev transform did not keep a module-level function with that name.
Fix:       renamed to `prettySource` in `lib/format.ts`, with a unit test, and added
           error boundaries so a render error shows a message instead of a blank page.
Before/after: blank page, then the run list rendered.
