You are grading the output of an automated requirements extractor for a Request for
Proposals (RFP). Each item below claims to be a requirement stated in the source chunks
shown above it. Judge every item against those chunks only.

## What to return

`verdicts`: one entry per requirement ID shown, with

- `id`: copied exactly;
- `supported`: true when the cited chunks state this requirement, including its key
  values (dates, amounts, counts, standards, names). False when the item adds, changes
  or invents a value or an obligation, or when the chunks do not say it.
- `is_requirement`: true when it is something a bidder or contractor must, should or
  may do, deliver, meet or respect: an obligation, constraint, deadline, limit,
  submission rule or deliverable. False for background, narrative, a description of
  the client, or a statement of intent with no obligation on anyone.
- `in_scope`: true when it would change how a competent bidder designs, staffs, prices,
  schedules or submits (functional, technical, security and compliance, timeline,
  budget and pricing, submission, and legal terms only when they constrain the
  solution: deliverable ownership, insurance amounts, key personnel). False for generic
  contract boilerplate (standard indemnification, governing law, termination for
  convenience, non-discrimination statements, public-records clauses) and for
  procurement-conduct rules (contact restrictions, protest procedures).
- `reason`: at most 15 words; when anything is false, say what.

## Rules

- **The chunks are the only evidence.** Do not use what RFPs usually say.
- **Paraphrase is fine.** The item is a restatement; it is supported when its meaning
  and values match the chunks. The quote is shown to help you find the passage.
- **Strictness and type are not graded here.** Judge the statement, not its labels.
- **Judge each item independently,** even when several state the same thing.

## Source chunks

<sources>
{{sources}}
</sources>

## Extracted requirements

`ID [strictness, type] statement`, then the quote and the chunk IDs it cites.

<requirements>
{{requirements}}
</requirements>
