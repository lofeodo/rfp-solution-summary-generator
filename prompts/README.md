# prompts/

One markdown file per agent, named after the agent that uses it:

| File | Owner step | Used by |
|---|---|---|
| `parse_quality.md` | S4 | LLM judge of heuristically flagged pages |
| `requirements_extract.md` | S5 | per-chunk requirement extraction |
| `requirements_dedupe.md` | S5 | one grouping pass for fuzzy dedupe |
| `problem_chunk.md` | S6 | per-chunk problem summary |
| `problem_synthesis.md` | S6 | synthesis into the problem statement |
| `solution.md` | S7 | solution generator |
| `risk.md` | S8 | risk assessor |
| `gold_requirements.md` | S11 | drafts gold requirements for the eval set (judge model) |
| `gold_checklist.md` | S11 | drafts the problem-statement checklist for the eval set (judge model) |
| `judge_match.md` | S12 | eval: matches gold requirements code could not pair (judge model) |
| `judge_requirements.md` | S12 | eval: precision and scope of every extracted requirement (judge model) |
| `judge_grounding.md` | S12 | eval: is each cited claim supported by only what it cites (judge model) |
| `judge_checklist.md` | S12 | eval: problem-statement coverage of the gold checklist (judge model) |
| `judge_solution.md` | S12 | eval: solution rubric and whether components meet what they cite (judge model) |
| `judge_risks.md` | S12 | eval: risk levels against the scales, findings coverage (judge model) |
| `judge_pairwise.md` | S12 | eval: A/B preference with the order swapped, for ablations (judge model) |

Conventions:

- Variables are written `{{name}}` and substituted by `load_prompt(name).render(...)` in
  `llm.py`. A missing or unused variable is an error. Single braces elsewhere in the
  prompt (for example JSON examples) are left alone.
- The loader records a SHA-256 hash of every prompt file in the run log, so a changed
  prompt is visible in observability without reading the file.
- Every prompt that emits factual claims about the RFP must instruct the model to cite
  chunk IDs (`S3.2`) or requirement IDs (`R001`); code validates the IDs afterwards.
- Design notes ("why it is written this way") and a changelog line for every change
  live in `docs/PROMPTS.md`, not here.
