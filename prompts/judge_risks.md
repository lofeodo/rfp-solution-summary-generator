You review the risk register an automated pipeline wrote for a bid on a Request for
Proposals (RFP). You see each risk's description and mitigation (not the levels the
pipeline gave it), and a list of findings that code detected for certain and that the
register was asked to address.

## What to return

- `risks`: one entry per risk ID shown, with a `severity` and a `likelihood` (`low`,
  `medium` or `high`) on the scales below, judged from the risk as written, and a
  `reason` of at most 20 words naming what drives the levels.
- `findings`: one entry per finding ID shown (`F1`), with `covered_by`: the risk IDs
  that address that finding, alone or grouped with others; empty when no risk does.

## Scales

Severity is the impact if the risk happens:

- `high`: the project fails, misses a contractual date, or overruns the budget by more
  than a quarter;
- `medium`: material rework, a slip or a cost that contingency can absorb;
- `low`: handled in normal delivery.

Likelihood is the chance it happens given the RFP and the solution as written:

- `high`: expected unless someone acts;
- `medium`: plausible; it turns on facts the RFP does not settle;
- `low`: needs an unusual event.

## Rules

- **Use the full scale.** Apply the definitions literally; a risk handled in normal
  delivery is `low` even if it sounds important.
- **Covering a finding** means the risk is about that conflict, that missing document,
  that unreadable page or that unaddressed requirement, by name or unambiguous
  reference. A generic risk ("requirements may be incomplete") does not cover a specific
  missing document.
- Use only the IDs shown.

## Risks

<risks>
{{risks}}
</risks>

## Findings

<findings>
{{findings}}
</findings>
