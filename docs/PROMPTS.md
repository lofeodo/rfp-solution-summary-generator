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

## Changelog

One line per change. Newest first.

| Date | Prompt | What changed | Why (observed failure or eval result) |
|---|---|---|---|
| 2026-10-30 | parse_quality | Created (S4) | First version; 12 of 12 live verdicts matched manual inspection |
| 2026-10-30 | gold_requirements, gold_checklist | Created (S11) | First version |
