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

## Changelog

One line per change. Newest first.

| Date | Prompt | What changed | Why (observed failure or eval result) |
|---|---|---|---|
| 2026-10-30 | problem_synthesis | Rule: write about the RFP, never "the evidence" or "the summaries" | F6: 3 of 4 live outputs leaked the prompt's framing into claims; 0 of 2 after |
| 2026-10-30 | problem_chunk, problem_synthesis | Created (S6) | First version; rough checklist coverage 12/12 on four RFPs |
| 2026-10-30 | parse_quality | Created (S4) | First version; 12 of 12 live verdicts matched manual inspection |
| 2026-10-30 | gold_requirements, gold_checklist | Created (S11) | First version |
