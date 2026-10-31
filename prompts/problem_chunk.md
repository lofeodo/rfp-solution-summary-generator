You are reading one chunk of a Request for Proposals (RFP) so that a later step can
write the problem statement: who the client is, what they are asking for, why, and under
what constraints. The whole document is processed chunk by chunk; you see only this chunk
and must not guess what the rest of the document says.

## Document

Title: {{title}}
Chunk: {{chunk_id}}
Section: {{section_path}}
Pages: {{pages}}

## Chunk text

<chunk>
{{text}}
</chunk>

## What to return

- `relevant`: true if the chunk says anything about
  - who the client is (the issuing body, its size, what it does today, its current
    systems or process);
  - what they need or want to buy, and why (the problem, the business driver);
  - what must be delivered (tasks, deliverables, milestones, scope boundaries);
  - when (deadlines for questions and proposals, contract period, milestone dates,
    go-live dates);
  - money (budget, not-to-exceed amounts, pricing rules, cost caps);
  - constraints the solution must respect (technical standards, security, privacy,
    accessibility, hosting, staffing, licensing, data ownership);
  - how proposals are evaluated (criteria and weights);
  - documents the RFP refers to that are provided separately or not included
    (attachments, appendices, exhibits, linked pages).

  Set it to false for a table of contents, a cover page, a signature block, a blank
  form, contact boilerplate, or a generic legal clause that would read the same in any
  contract and imposes no project-specific constraint (indemnification, governing law,
  severability, and the like).

- `summary`: when relevant, a compact factual summary of the chunk in two to five
  sentences, written as a list of facts rather than prose. Keep every number, date,
  amount, percentage, name of an organisation, system, standard or document, exactly as
  the chunk gives them. Do not add anything the chunk does not say and do not interpret.
  When not relevant, return an empty string.
