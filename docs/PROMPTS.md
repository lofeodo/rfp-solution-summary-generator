# PROMPTS.md — prompt assets and change notes

The prompts themselves live in `prompts/`, one file per agent. This file is the
"notes on why they work" deliverable: a design note per prompt plus a changelog line
every time a prompt changes.

## Design notes

Fill in one block per prompt when the owning step lands:

```
### prompts/<name>.md
Purpose:
Inputs it receives:
Output contract (schema):
Why it is written this way:   (the two or three choices that matter)
Known weaknesses:
```

### prompts/gold_requirements.md
Purpose: draft core gold requirements for one RFP (S11); a human pass corrects them.
Inputs it receives: `{{document}}`, the S2 parsed text with `[page N]` markers.
Output contract (schema): `DraftRequirements` in `evals/gold/label.py` (text, type,
strictness, quote, page, section); IDs and provenance are assigned by code.
Why it is written this way: an explicit include/exclude list carries the core-only scope
(D23), since "requirement" alone pulls in every boilerplate clause; strictness is defined
by modal verb so labels are reproducible; the quote must be the shortest verbatim span
inside one sentence or table cell, because code drops any item whose quote is not found.
Known weaknesses: still over-inclusive on standard certifications and procurement-conduct
rules (13 to 16 removals per RFP); occasionally skips concrete delivery duties stated in
narrative paragraphs or dated milestone tables.

### prompts/gold_checklist.md
Purpose: draft 8 to 12 must-mention facts for a problem statement (S11).
Inputs it receives: `{{document}}`, as above.
Output contract (schema): `DraftChecklist` (fact, quote, page); size 8 to 12 enforced by a
validator so a short list is retried (F4).
Why it is written this way: a coverage list (issuer, need, deliverable, budget, dates,
constraints, absent documents) so the checklist tests understanding, not trivia; facts
must carry the concrete number or name so a grader can tick them unambiguously.
Known weaknesses: tends to spend slots on schedule details and evaluation weights rather
than referenced-but-absent documents (replaced by hand in 3 of 4 RFPs).

### prompts/parse_quality.md
Purpose: judge whether one heuristically flagged page's extracted text is usable and
whether the page holds content the text lacks (S4).
Inputs it receives: `{{title}}`, `{{page_number}}`, `{{page_count}}`, `{{flags}}` (reason
and detail per flag), `{{images}}` (size and caption per image, or "none"),
`{{markdown}}` (the page text, or "(empty)").
Output contract (schema): `PageJudgement` in `schemas.py` (`text_usable`,
`content_missing`, `page_kind`, `confirmed_flags`, `reason`). Code turns it into an
escalation and decides who triggered it (D24).
Why it is written this way: each flag comes with its typical false alarm (contents pages,
covers, "intentionally left blank" dividers, logos, one-column contents tables) because
those are most of the flags on the four RFPs; the two booleans are asked separately so a
page with clean text around an image table is still caught; the model is told it never
sees the image, so it reasons from captions and lead-in sentences ("the following
tables") instead of guessing. No citations: it makes no claims about the RFP's content.
Known weaknesses: cannot see the image, so a decorative large image next to a sentence
that sounds like a lead-in could be escalated; blank fill-in forms (Missouri affidavits)
are escalated although transcribing them adds little.

### prompts/requirements_extract.md
Purpose: extract core requirements, ambiguities and gaps from one chunk (S5); the same
file, with `{{unit}}` and `{{mode_rules}}` swapped, serves the single-call ablation over
every chunk.
Inputs it receives: `{{unit}}` (what the model is given and that other chunks are handled
separately), `{{mode_rules}}` (empty, or the chunk-ID citation rule in document mode),
`{{title}}`, `{{input}}` (one or many `### Chunk S3.2` blocks with section path, pages and
the text in `<chunk>` tags).
Output contract (schema): `ChunkExtraction` or `DocumentExtraction` in `schemas.py`.
Code assigns IDs, cites the chunk, verifies quotes (D28) and dedupes.
Why it is written this way: the include/exclude scope is the gold prompt's, so extractor
and labeller agree on what a requirement is (D30); the exclude list names the boilerplate
clauses the first run kept (assignment, independent contractor, audit, FFATA) and says a
form is one item, not one per field; "many chunks contain no requirement" and "returning
empty lists is correct" stop the model inventing obligations from headings; the quote
rule says code checks it verbatim, which makes the model copy rather than tidy;
ambiguities and gaps both carry a "not this" list, because the first run reported other
sections of the same RFP as missing (F6); the instructions come first and the chunk last
so DeepSeek's prefix cache serves about three quarters of the input tokens.
Known weaknesses: still generous with `submission` items (proposal-content lists split
finely) and with ambiguities (29 to 70 per RFP); the gap definition pulls in every
linked form on a form-heavy RFP (NYESD 38); output varies between runs at temperature 0.

### prompts/requirements_dedupe.md
Purpose: one grouping pass over the exact-deduped list: which IDs state the same
obligation, which contradict (D6, D29).
Inputs it receives: `{{requirements}}`, one line per item: `ID [strictness, type] text —
"quote" (chunk IDs)`.
Output contract (schema): `DedupeOutput` (groups with `representative_id` and
`member_ids`, conflicts with IDs and a reason). Code checks it, feeds violations back
once, sanitises, merges.
Why it is written this way: "same obligation on the same party about the same thing"
with signs for and against, because the failure mode is over-grouping a general duty with
a specific one; the representative is the most specific statement so the merged item
keeps the best text and quote; the one-ID-once rule is stated twice and ends with "check
that no ID appears twice", added after the first run put R030 in three groups on both
turns; alternatives and a standard next to its stricter version are called out as
non-conflicts after Missouri's Oracle/SQL Server and Section 508/WCAG pairs were flagged.
Known weaknesses: the first answer still breaks the contract on most RFPs (the feedback
turn fixes it); alternatives are still sometimes flagged as conflicts.

## Changelog

One line per change. Newest first.

| Date | Prompt | What changed | Why (observed failure or eval result) |
|---|---|---|---|
| 2026-10-30 | requirements_extract | Gaps: name the document, never its URL; a document named with its link is one gap | NYESD listed 50 gaps, most forms twice (name and URL) (F7); 38 after |
| 2026-10-30 | requirements_extract | Expanded boilerplate exclusions, one item per form; ambiguities and gaps exclude content defined elsewhere in the same RFP and ordinary lack of detail | Missouri first run: 144 requirements, 105 ambiguities, 39 gaps, most "not in this chunk" (F6); 131 / 53 / 12 after |
| 2026-10-30 | requirements_dedupe | "An ID may appear once across the whole answer; check before answering"; alternatives and a standard next to its stricter version are not conflicts | Missouri first run: R030 in three groups on both turns (fallback used); clean after one turn on all reruns |
| 2026-10-30 | requirements_extract, requirements_dedupe | Created (S5) | First version |
| 2026-10-30 | parse_quality | Created (S4) | First version; 12 of 12 live verdicts matched manual inspection |
| 2026-10-30 | gold_requirements, gold_checklist | Created (S11) | First version |
