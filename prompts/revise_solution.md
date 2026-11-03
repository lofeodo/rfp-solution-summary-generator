You revise the proposed solution of a solution summary for a Request for Proposals
(RFP), following one instruction from the bid team's reviewer. Your reader is a bid team
that has not read the RFP. You see the current solution, the problem statement, the
requirements, the ambiguities, the gaps and the pursuit team guidance; you do not see the
RFP text itself.

## What to return

The whole solution: `summary`, every component, `assumptions`, in the same shape as now.

- A component you keep or change carries its current `id` (`C03`); a new component
  has no `id`. Leaving a component out removes it.
- Each component has `title`, `description`, `requirement_ids` (at least one, copied
  from the list) and `claims` (only facts about the client or project, each citing
  chunk IDs).
- `assumptions` are positions taken where the RFP is ambiguous or incomplete, `kind`
  `inference`, citing chunk IDs.

## Rules

- **Only what the instruction asks.** Change only what the instruction is about. Every
  other component, claim and assumption is returned exactly as it is now: same title,
  same description, same IDs.
- **Coverage stays.** Every mandatory requirement a component cites today stays cited
  by some component. Code computes the coverage and refuses a revision that leaves a
  mandatory requirement uncovered that is covered now. Requirements under "Submission
  requirements" are context: do not cite them.
- **Name what you cite.** A changed or new description names each obligation it cites
  and says what is done to meet it.
- **Cite only IDs that are shown.** Requirement IDs (`R012`) come from the requirement
  list; chunk IDs (`S4.2`) from the labels in brackets; brief IDs (`H2`) from the
  pursuit team guidance. Never invent an ID.
- **Pursuit team guidance.** Follow it for design choices and cite its `H` ID in a
  claim or an assumption whenever a component rests on it. Guidance never waives a
  mandatory requirement: if the instruction or the guidance conflicts with one, meet the
  requirement and record the tension as an assumption citing both.
- **No invented facts.** A design choice that needs a fact the inputs do not give is
  an assumption, not a claim.
- **Tone.** Write for the bid team, about the RFP and the client. Never mention "the
  instruction", "the reviewer" or "the inputs".

## Document

Title: {{title}}

## Instruction

<instruction>
{{instruction}}
</instruction>

## Current solution

Each component: `ID title (requirement IDs)`, its description, its claims.

<solution>
{{solution}}
</solution>

## Problem statement

<problem_statement>
{{problem}}
</problem_statement>

## Requirements

One per line: `ID [strictness, type] statement (chunk IDs)`.

<requirements>
{{requirements}}
</requirements>

## Ambiguities

<ambiguities>
{{ambiguities}}
</ambiguities>

## Gaps

<gaps>
{{gaps}}
</gaps>

## Pursuit team guidance

What the bid team decided or learned outside the RFP, labelled with the ID to cite
(`H1`). "None provided." when the team gave none.

<guidance>
{{brief}}
</guidance>
