You are grading an automated requirements extractor against a gold standard for a
Request for Proposals (RFP). Each gold requirement below was written by a human
reviewer. The candidates are requirements the extractor produced from pages near the
gold item. Decide, for each gold requirement, which candidates state the same
obligation.

## What to return

`matches`: one entry per gold ID shown, with

- `gold_id`: copied exactly;
- `requirement_ids`: every candidate ID that states the same requirement, best first;
  empty when none does;
- `reason`: at most 15 words.

## Rules

- **Same obligation, any wording.** A candidate matches when a bidder who met the
  candidate would thereby meet the gold requirement's core: same subject, same
  obligation, same key value (date, amount, count, standard). Wording, sentence
  structure and level of detail may differ.
- **Partial splits count.** When the extractor split one gold requirement into several
  candidates, list every candidate that states a material part of it. When one candidate
  merges the gold requirement with others, it still matches.
- **Different values do not match.** A candidate with a different date, amount, count or
  standard than the gold item is not a match, even on the same topic.
- **Topic is not enough.** "Proposals must be emailed" does not match "Proposals must
  include a cost form".
- Type and strictness labels are shown for context; do not reject a match because they
  differ.
- Use only the IDs shown. Never invent an ID.

## Gold requirements

One per item: `ID [strictness, type, page] statement`, then the gold quote.

<gold>
{{gold}}
</gold>

## Candidates

One per line: `ID [strictness, type] statement`.

<candidates>
{{candidates}}
</candidates>
