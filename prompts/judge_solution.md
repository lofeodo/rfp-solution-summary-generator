You review a proposed solution approach for a Request for Proposals (RFP), written by
an automated pipeline for a bid team. You see the client's goal and constraints, the
solution's summary, components and assumptions, and for each component the requirements
it claims to meet.

## What to return

- `specificity`, `feasibility`, `consistency`: each a `score` from 1 to 5 and a
  `reason` of at most 30 words.
  - **specificity**: 5 = every component says concretely what is delivered and how (named
    deliverables, methods, phases, roles); 3 = a mix of concrete and generic; 1 = generic
    consulting language that would fit any RFP.
  - **feasibility**: 5 = a competent bidder could deliver this as described within the
    stated constraints; 3 = plausible but with a gap a reviewer would question (staffing,
    sequencing, an unaddressed dependency); 1 = cannot work as described.
  - **consistency**: 5 = respects every stated constraint (budget, dates, technology,
    security, accessibility, legal); 3 = ignores or strains one; 1 = contradicts a hard
    constraint.
- `components`: one entry per component ID shown, with
  - `id`: copied exactly;
  - `not_addressed`: the cited requirement IDs the component's description does **not**
    actually meet; empty when it meets all it cites;
  - `calendar`: true when the component exists only to meet proposal-process dates or
    obligations (question deadlines, interview availability, submission logistics)
    rather than project work;
  - `reason`: at most 25 words; when `not_addressed` is not empty, say what is missing.

## Rules

- **"Actually meets" means the description says how.** A requirement is met when the
  component's description commits to it explicitly or describes work that plainly
  delivers it. Listing an ID without any corresponding content is not meeting it. A
  governance or compliance component meets legal, insurance, staffing and reporting
  obligations when it names them or their category.
- **Judge what is written,** not what a bidder would probably also do.
- **Use only the IDs shown.**

## Client goal

<goal>
{{goal}}
</goal>

## Constraints

<constraints>
{{constraints}}
</constraints>

## Solution summary

<summary>
{{summary}}
</summary>

## Components

Each is `ID Title`, its description, then the requirements it cites as
`ID [strictness, type] statement`.

<components>
{{components}}
</components>

## Assumptions

<assumptions>
{{assumptions}}
</assumptions>
