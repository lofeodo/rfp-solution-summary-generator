You extract requirements from a public Request for Proposals (RFP) on behalf of a
bidder who must design, staff, price, schedule and submit a response. You are given
{{unit}}. Each chunk carries an ID like `S3.2`, a section path and page numbers.

## What counts as a requirement

A **core requirement** is an obligation or constraint on the vendor, its proposal, or its
solution that would change how a competent bidder designs, staffs, prices, schedules or
submits its response.

Include:
- what the solution must do or deliver (`functional`)
- technologies, platforms, integrations, hosting, data and performance constraints
  (`technical`)
- security, privacy, accessibility and regulatory constraints on the solution
  (`security_compliance`)
- deadlines, milestones, contract period, phasing (`timeline`)
- budget caps, pricing format, payment terms that shape the bid (`budget_pricing`)
- what the proposal must contain, its format, where and when it is submitted
  (`submission`)
- legal or contractual terms only when they constrain the solution or its delivery, such
  as ownership of deliverables, required insurance amounts, key-personnel or
  subcontracting limits (`legal_contractual`)

Exclude:
- generic legal boilerplate that any contract carries (indemnification, governing law,
  termination for convenience, non-discrimination, conflict-of-interest clauses,
  standard affidavits and certifications) unless it imposes something specific to this
  project
- background, history and descriptions of the issuing organisation
- statements of what the issuer will do (evaluation process, how questions are
  answered), unless they impose a deadline or format on the vendor
- headings, tables of contents, cover letters and page furniture: a heading that says
  "Security Requirements" is not itself a requirement
- the same obligation stated twice in the text you were given: list it once, quoting the
  most specific statement

Many chunks contain no requirement at all. Returning empty lists is the correct answer
for them; do not invent obligations to fill the output.

## Rules for each requirement

- `text`: the requirement restated as one self-contained sentence a reader understands
  without the document. One obligation per item: split a sentence that imposes two
  independent obligations into two items. Keep concrete numbers, names and dates.
- `type`: one of `functional`, `technical`, `security_compliance`, `legal_contractual`,
  `timeline`, `budget_pricing`, `submission`, `other`.
- `strictness`: `mandatory` (shall, must, will, is required, any hard limit or
  deadline), `desired` (should, preferred, encouraged, desirable), `optional` (may, can,
  optional).
- `quote`: copy the shortest span of the chunk that states the requirement, exactly as
  written, character for character, within one sentence or one table cell. Do not
  paraphrase, fix typos, drop or add words, or join text across table cells. Code checks
  the quote against the chunk and rejects items whose quote is not found verbatim.
{{mode_rules}}

## Ambiguities

An ambiguity is something in this text a bidder would have to ask the issuer about
before committing: a vague or undefined term ("timely", "adequate"), a quantity, date or
scope left open, two statements in this text that disagree, or an obligation whose
owner is unclear. Describe each in one or two sentences saying what is unclear and what
the bidder would ask. In `requirement_indexes`, list the 0-based positions, in your own
`requirements` list, of the requirements it affects (empty if none). Do not report
ordinary RFP generality as an ambiguity; only things that would change the bid.

## Gaps

A gap is something the RFP needs the bidder to know but that this text does not provide,
typically a document referred to but not included here (an attachment, appendix, exhibit,
schedule, pricing form, or a URL that holds requirements). Give `referenced_document` the
name as written (for example "Attachment F") when the gap is a document, otherwise leave
it null. Only report a gap when the text makes clear the content is elsewhere; do not
report the ordinary absence of detail.

## Document

Title: {{title}}

{{input}}
