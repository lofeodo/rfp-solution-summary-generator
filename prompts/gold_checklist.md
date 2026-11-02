You are building a gold-standard checklist for evaluating an automated summary of a
Request for Proposals. The checklist lists the facts that any correct one-page problem
statement for this RFP must mention. A grader will later tick each fact as present or
absent in a generated summary, so each fact must be specific and checkable.

Below is the full text of the RFP, extracted from a PDF. Each page starts with a marker
like `[page 3]`.

Return 8 to 12 facts, covering as many of these as the document states:
- who is issuing the RFP and who the end users or beneficiaries are
- the problem or need that prompted it, and why now
- what is being procured (the core deliverable or service), and its scope boundaries
- the budget or price ceiling
- the contract period, key milestones, and the proposal due date
- hard constraints the solution must respect (technology, security, accessibility,
  legal, data)
- important documents that are referenced but not included in this PDF

Rules:
- `fact`: one sentence, with the concrete detail (name, number, date, amount). "The
  budget is capped at $175,000", not "The RFP mentions a budget".
- Only facts the document states. No inferences, no recommendations.
- `quote`: the shortest span of the document that states the fact, copied exactly,
  character for character, within one sentence or table cell, without the page marker.
- `page`: the number in the nearest `[page N]` marker above the quote.
- Prefer the facts a reader would most regret missing. Skip boilerplate.

<document>
{{document}}
</document>
