# Gold labels

Reference answers S12 scores the pipeline against, for the four public RFPs in
`data/rfps/`. One final file per RFP (`<rfp>.json`), plus the untouched model draft it
started from (`<rfp>.draft.json`) and, where needed, hand-only labels (`<rfp>.hand.json`).

## What is labelled

- **Requirements (core only).** Obligations or constraints that would change how a
  competent bidder designs, staffs, prices, schedules or submits: functional, technical,
  security and compliance, timeline, budget and pricing, submission, and legal terms
  only when they constrain the solution (deliverable ownership, insurance amounts,
  key personnel). Generic contract boilerplate is left out on purpose. See
  `docs/DECISIONS.md` D23.
- **Problem-statement checklist.** 8 to 12 concrete facts any correct problem statement
  must mention (issuer, need, deliverable, budget, dates, hard constraints, missing
  documents).

Consequence for S12: **recall** is measured against gold. **Precision** is judged per
extracted item, because a correctly extracted boilerplate clause is not in gold but is
not a false positive either.

## Format (`schema.py`)

| Field | Requirements (`GR001`) | Checklist (`GC01`) |
|---|---|---|
| statement | `text`: one self-contained sentence | `fact`: one sentence with the concrete detail |
| class | `type`, `strictness` (the pipeline's enums) | |
| evidence | `quote` verbatim from the parsed text, `page`, `section` | `quote`, `page` |
| provenance | `source`: `draft`, `corrected` or `hand`; `quote_verifiable`; `note` | same |

Gold IDs use their own prefixes so they never collide with pipeline IDs (`R001`). Gold
has no chunk IDs, so it survives any change to chunking. Quotes are matched with
`textmatch.normalise` on both sides (case, quote and dash style, markdown markers, table
pipes, `<br>`, whitespace), so S12 matches the same way.

## Workflow

```
python -m evals.gold.label draft --all   # Claude drafts <rfp>.draft.json (needs ANTHROPIC_API_KEY)
python -m evals.gold.label init --all    # copies to <rfp>.json, appends <rfp>.hand.json
#   correct <rfp>.json by hand against the full text; set source=corrected on edited items
python -m evals.gold.label diff --all    # correction table below
python -m evals.gold.label check --all   # every verifiable quote is in the parsed text
```

The draft step drops any item whose quote is not found in the parsed text and prints it,
so every draft label is checkable. Draft files are never edited afterwards; the diff
against them is the record of the human pass. `tests/test_gold.py` re-runs the `check`
on every committed final file.

## Federal Way page 5

The ERP Environment table on page 5 is an embedded image, so the parser cannot see it.
Its rows are labelled by hand from the page render in `federal_way.hand.json`, with
`quote_verifiable=false`. A pipeline that misses them shows the known parsing gap as lost
recall rather than hiding it.

## Fraction corrected

"Corrected" = drafted items the human pass edited (text, type, strictness or quote) or
removed, over drafted items. Items the draft missed are counted separately as added.

CORRECTION_TABLE
