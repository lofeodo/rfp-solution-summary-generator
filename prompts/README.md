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
