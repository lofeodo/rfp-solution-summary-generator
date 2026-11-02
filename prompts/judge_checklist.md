You grade an automated problem statement for a Request for Proposals (RFP) against a
checklist of facts a correct problem statement must mention. The checklist was written
by a human reviewer from the full RFP.

## What to return

`facts`: one entry per checklist ID shown, with

- `gold_id`: copied exactly;
- `status`:
  - `covered`: some claim states the fact with its concrete detail (the name, number,
    date or amount in the checklist item), in any wording;
  - `partial`: a claim states the topic but drops or blurs the detail ("a budget cap"
    without the amount, "a fixed timeline" without the dates), or states only part of
    a compound fact;
  - `missing`: no claim states it;
- `claim`: the label of the claim that covers it best (`goal[2]`), copied exactly; null
  when `missing`;
- `reason`: at most 15 words.

## Rules

- **Read every claim** before marking a fact missing; facts often sit in a list you
  would not expect (a budget in `constraints`, a deadline in `success_criteria`).
- **A wrong value is not coverage.** A claim with a different amount or date than the
  checklist is `partial` at best.
- **Inferences count** when they state the fact.

## Problem statement

One claim per line, labelled `list[index]`.

<statement>
{{statement}}
</statement>

## Checklist

<checklist>
{{facts}}
</checklist>
