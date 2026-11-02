You are building a gold-standard answer key for evaluating an automated RFP requirements
extractor. Precision matters more than speed: every item you return will be checked by a
person and by code.

Below is the full text of a public Request for Proposals, extracted from a PDF. Each page
starts with a marker like `[page 3]`. Tables are markdown tables.

List every **core requirement** in the document: an obligation or constraint on the
vendor, its proposal, or its solution that would change how a competent bidder designs,
staffs, prices, schedules or submits its response.

Include:
- what the solution must do or deliver (functional)
- technologies, platforms, integrations, hosting, data and performance constraints (technical)
- security, privacy, accessibility and regulatory constraints on the solution (security_compliance)
- deadlines, milestones, contract period, phasing (timeline)
- budget caps, pricing format, payment terms that shape the bid (budget_pricing)
- what the proposal must contain, its format, where and when it is submitted (submission)
- legal or contractual terms only when they constrain the solution or its delivery, such as
  ownership of deliverables, required insurance amounts, key-personnel or subcontracting
  limits (legal_contractual)

Exclude:
- generic legal boilerplate that any contract carries (indemnification, governing law,
  termination for convenience, non-discrimination, conflict-of-interest clauses, standard
  affidavits) unless it imposes something specific to this project
- background, history and descriptions of the issuing organisation
- statements of what the issuer will do (evaluation process, how questions are answered),
  unless they impose a deadline or format on the vendor
- duplicates: when the same obligation is stated twice, list it once, quoting the most
  specific statement

Rules for each item:
- `text`: the requirement restated as one self-contained sentence a reader understands
  without the document. One obligation per item: split a sentence that imposes two
  independent obligations into two items.
- `type`: one of functional, technical, security_compliance, legal_contractual, timeline,
  budget_pricing, submission, other.
- `strictness`: mandatory (shall, must, will, is required, any hard limit or deadline),
  desired (should, preferred, encouraged, desirable), optional (may, can, optional).
- `quote`: copy the shortest span of the document that states the requirement, exactly as
  written, character for character, within one sentence or one table cell. Do not
  paraphrase, fix typos, join text across table cells, or include the page marker.
- `page`: the number in the nearest `[page N]` marker above the quote.
- `section`: the nearest heading above the quote, as written.

Expect roughly 25 to 50 items for a document of this size; do not pad and do not
truncate.

<document>
{{document}}
</document>
