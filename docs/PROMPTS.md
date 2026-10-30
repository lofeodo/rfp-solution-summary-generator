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

### prompts/problem_chunk.md
Purpose: stage one of the problem statement (S6): what one chunk says about who the
client is, what they need and why, and under what constraints.
Inputs it receives: `{{title}}`, `{{chunk_id}}`, `{{section_path}}` (`A > B`),
`{{pages}}`, `{{text}}` (the chunk, overlap sentence included).
Output contract (schema): `ChunkSummaryDraft` in `schemas.py` (`relevant`, `summary`);
code attaches the chunk ID (D28).
Why it is written this way: the relevance list mirrors the gold checklist categories
(issuer, need, deliverables, dates, money, constraints, evaluation, referenced documents)
so stage one keeps exactly what the synthesis must cite; "keep every number, date, amount,
name and document exactly" because the synthesis can only state values that survive
stage one; the model is told it sees one chunk and must not guess the rest, which keeps
summaries factual; the irrelevant list names the boilerplate seen on the four RFPs
(contents, cover, signature blocks, generic clauses).
Known weaknesses: summaries run long (NYESD: 76k input tokens become 13k of summaries,
little shorter than the 18.5k full text); "two to five sentences" is advisory and not
enforced. Relevance is generous (60 to 63 of 70 NYESD chunks), which is the safe side.

### prompts/problem_synthesis.md
Purpose: stage two of the problem statement (S6), and the full-text baseline: four lists
of cited claims (client situation, goal, success criteria, constraints).
Inputs it receives: `{{title}}`, `{{evidence_kind}}` (one sentence saying whether the
evidence is summaries or full text), `{{evidence}}` (items labelled `[S3.2] section
path (pages n)`).
Output contract (schema): a per-call subclass of `ProblemStatement` that rejects empty
lists and chunk IDs outside the evidence (D28).
Why it is written this way: each list is defined by the questions a bid team asks, with
the checklist categories spread across them so nothing has two homes; "state the concrete
value" with a positive and a negative example, because a claim without the number is not
checkable; `fact` vs `inference` is defined by whether a cited chunk states the claim,
since S12's grounding judge checks exactly that; "three to eight per list" is advisory,
the validator enforces only non-empty; the same prompt serves both modes so the S13
ablation varies the evidence only; the last rule ("write about the RFP, never the
evidence") came from F6.
Known weaknesses: in 2 of 4 NYESD runs the first attempt cited an ID outside the evidence
or left a list empty (F7); the model occasionally spends a constraint slot on a
procedural detail (upload folder layout) rather than a solution constraint.
### prompts/requirements_extract.md
Purpose: extract core requirements, ambiguities and gaps from one chunk (S5); the same
file, with `{{unit}}` and `{{mode_rules}}` swapped, serves the single-call ablation over
every chunk.
Inputs it receives: `{{unit}}` (what the model is given and that other chunks are handled
separately), `{{mode_rules}}` (empty, or the chunk-ID citation rule in document mode),
`{{title}}`, `{{input}}` (one or many `### Chunk S3.2` blocks with section path, pages and
the text in `<chunk>` tags).
Output contract (schema): `ChunkExtraction` or `DocumentExtraction` in `schemas.py`.
Code assigns IDs, cites the chunk, verifies quotes (D29) and dedupes.
Why it is written this way: the include/exclude scope is the gold prompt's, so extractor
and labeller agree on what a requirement is (D31); the exclude list names the boilerplate
clauses the first run kept (assignment, independent contractor, audit, FFATA) and says a
form is one item, not one per field; "many chunks contain no requirement" and "returning
empty lists is correct" stop the model inventing obligations from headings; the quote
rule says code checks it verbatim, which makes the model copy rather than tidy;
ambiguities and gaps both carry a "not this" list, because the first run reported other
sections of the same RFP as missing (F8); the instructions come first and the chunk last
so DeepSeek's prefix cache serves about three quarters of the input tokens.
Known weaknesses: still generous with `submission` items (proposal-content lists split
finely) and with ambiguities (29 to 70 per RFP); the gap definition pulls in every
linked form on a form-heavy RFP (NYESD 38); output varies between runs at temperature 0.

### prompts/requirements_dedupe.md
Purpose: one grouping pass over the exact-deduped list: which IDs state the same
obligation, which contradict (D6, D30).
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

### prompts/solution.md
Purpose: the proposed approach: a summary, components that cite the requirement IDs
they satisfy, and the assumptions the design rests on (D32).
Inputs it receives: `{{title}}`, `{{problem}}` (the four claim lists, each claim with
its chunk IDs and an `(inference)` mark), `{{requirements}}` (mandatory, desired and
optional blocks, one line per item `ID [strictness, type] text (chunk IDs)`, then the
submission items under "context, do not address"), `{{ambiguities}}`, `{{gaps}}`. No
RFP text and no quotes.
Output contract (schema): `SolutionDraft`; a per-call subclass rejects empty components,
a component with no requirement IDs, and unknown requirement or chunk IDs. Code assigns
`C01…`, computes coverage, and feeds the uncovered mandatory IDs back in a revision
round (same conversation) while any remain, up to the round cap.
Why it is written this way: the coverage rule is explicit and says that code computes
it and that misses become risks, so the model has a reason to cite completely rather
than describe elegantly; legal, insurance and reporting obligations are named as things
a governance component cites, because a model left alone writes only the technical
components and the uncovered list fills with contract terms; the submission block is
labelled "do not address" so the model does not build a "proposal writing" component;
claims are discouraged ("most components need no claims") because restating
requirements as claims adds citations without evidence; assumptions must state the
position taken, not the ambiguity, so S8 can read them as design decisions; the F6
rule (write about the RFP, never "the inputs") is carried over; instructions come first
so the provider prefix cache serves repeated rounds.
Known weaknesses: proposal-process obligations that S5 typed `timeline` or
`budget_pricing` rather than `submission` are in scope, so the revision round makes the
model add a commercial or submission-flavoured component to cite them (Missouri R007,
R019); the assumption list runs long (Missouri 8) and some assumptions restate facts the
problem statement already carries.

### prompts/risk.md
Purpose: the risks of bidding and delivering: what could go wrong, how badly, how
likely, and what the bidder would do about it (D33).
Inputs it receives: `{{title}}`, `{{findings}}` (five blocks computed by code: mandatory
requirements the solution does not address, conflicting requirement pairs, referenced
documents not in the PDF, pages whose text could not be parsed, the budget-requirement
count), `{{solution}}` (summary, components as `ID Title (requirement IDs)` with their
description and claims, assumptions, the coverage line), `{{problem}}`,
`{{requirements}}` (as S7, but the submission block is headed "how and when the proposal
is delivered", not "do not address"), `{{ambiguities}}`, `{{gaps}}`. No RFP text.
Output contract (schema): `RiskAssessmentDraft`; a per-call subclass rejects fewer than
3 or more than 15 risks, unknown requirement or chunk IDs, and a draft in which an
uncovered mandatory requirement is cited by no risk. Code sorts by severity then
likelihood and numbers `K01…`.
Why it is written this way: the findings come first and the "Findings first" rule says
code checks the uncovered IDs, so the model works from facts before it speculates; the
two scales are written out as impact and as "given the RFP and the solution as
written", so a `high` means the same thing on every RFP; `source` is defined by what
creates the risk, not by where the words came from; "one risk, one cause" with a worked
contrast stops requirement restatements; `chunk_ids` may be empty for a flagged page or
a missing document because those have no chunk; mitigation is asked to be an action (a
question before the deadline, a stated assumption, a contingency), not "monitor"; the F6
tone rule is carried over with "the findings" added to the banned phrases; instructions
come first for the prefix cache.
Known weaknesses: the count runs to the top of the range or one over (F12); severity
clusters at high and medium (no `low` severity and one `low` likelihood in 50 risks on
the tuned prompt), so the scales separate less than they could; `source` can flip
between runs for the same risk (NYESD's MWBE goals: `rfp`, then `solution`), which
S12's judge should sample.

## Changelog

One line per change. Newest first.

| Date | Prompt | What changed | Why (observed failure or eval result) |
|---|---|---|---|
| 2026-10-30 | risk | Count rule under Rules: at most twelve, merge or drop, code rejects more than fifteen | All four first runs returned 13 against "six to twelve" (F12); 12, 13, 13, 12 after |
| 2026-10-30 | risk | Created (S8) | First version; 12 to 13 risks per RFP, 0 validator retries, every code finding surfaced as a risk |
| 2026-10-30 | solution | Assumptions: `chunk_ids` are the `S4.2` IDs listed after the ambiguity or gap; `A01`/`G01` are never cited | Colfax and Federal Way first runs cited ambiguity and gap IDs as chunks, caught by the validator (F10); 0 retries on the four-RFP rerun |
| 2026-10-30 | solution | Created (S7) | First version; full mandatory coverage on four RFPs after at most one revision round |
| 2026-10-30 | requirements_extract | Gaps: name the document, never its URL; a document named with its link is one gap | NYESD listed 50 gaps, most forms twice (name and URL) (F9); 38 after |
| 2026-10-30 | requirements_extract | Expanded boilerplate exclusions, one item per form; ambiguities and gaps exclude content defined elsewhere in the same RFP and ordinary lack of detail | Missouri first run: 144 requirements, 105 ambiguities, 39 gaps, most "not in this chunk" (F8); 131 / 53 / 12 after |
| 2026-10-30 | requirements_dedupe | "An ID may appear once across the whole answer; check before answering"; alternatives and a standard next to its stricter version are not conflicts | Missouri first run: R030 in three groups on both turns (fallback used); clean after one turn on all reruns |
| 2026-10-30 | requirements_extract, requirements_dedupe | Created (S5) | First version |
| 2026-10-30 | problem_synthesis | Rule: write about the RFP, never "the evidence" or "the summaries" | F6: 3 of 4 live outputs leaked the prompt's framing into claims; 0 of 2 after |
| 2026-10-30 | problem_chunk, problem_synthesis | Created (S6) | First version; rough checklist coverage 12/12 on four RFPs |
| 2026-10-30 | parse_quality | Created (S4) | First version; 12 of 12 live verdicts matched manual inspection |
| 2026-10-30 | gold_requirements, gold_checklist | Created (S11) | First version |
