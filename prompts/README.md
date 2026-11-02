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

## The structure

Every prompt follows one structure (ST12): the same `##` headings in the same order.
`tests/test_prompt_structure.py` enforces it, so a new prompt that breaks the order
fails CI. The order puts everything that is the same on every call first and the
data last, which is what the provider prefix cache needs (S5 measured about three
quarters of input tokens served from cache on the per-chunk extractor).

```
## Role            who the model is: a specific persona and the standard it holds
## Task            what to do, in one or two sentences
## Context         what the model sees and does not see; what code does with the answer
## Output          one bullet per schema field: meaning, allowed values, size, citations
## Rules           bold-named rules, most important first, each with its reason
## Examples        (optional) contrastive pairs: "Not this" / "This"
## Tone            register and voice for every free-text field
## <Input block>   one heading per data block, a one-line legend, the data in XML tags
## ...
## Final checks    three to five things to verify before answering
```

Section by section:

- **Role.** One paragraph. A persona with seniority and practice, and the standard it
  holds. A specific persona sets the register and the default judgment once, at the
  top. Families: generator prompts (`requirements_*`, `problem_*`, `solution`, `risk`)
  are a senior proposal professional at a Big Four advisory practice (analyst,
  proposal manager, solution architect, bid risk manager); gold prompts are a senior
  procurement analyst building an answer key; judge prompts are a senior reviewer in
  an independent quality-assurance function; `parse_quality` is a document-processing
  quality specialist. No real firm is named.
- **Task.** One paragraph: the verb, the object, the reader. Nothing else. Each judge
  prompt's Task carries the phrase the scripted judge in `tests/test_harness.py`
  recognises it by (listed in `tests/test_prompt_structure.py`); keep it.
- **Context.** Where the call sits in the pipeline: what the model sees (one chunk,
  summaries, no RFP text, no page image) and what code does with the answer
  (verifies quotes, assigns IDs, computes coverage, retries with feedback, rejects
  what). A model that knows the boundary of its evidence and the consumer of its
  output invents less and cites more. The `{{unit}}` sentence of the extractor lives
  here.
- **Output.** One bullet per schema field with its meaning, allowed values, size and
  citation requirement; nested fields indented; scales (severity, likelihood, rubric
  anchors) sit under the field they define. The schema enforces the syntax; this
  section carries the semantics. The extractor's `{{mode_rules}}` bullet closes its
  per-requirement field list.
- **Rules.** Bold-named rules ordered by importance; each says what, then why or what
  code does about it. Shared names are reused where they apply so a reader can
  compare prompts: **Scope**, **Cite only IDs that are shown**, **No invented facts**,
  **Verbatim quotes**, **Count**, **Only the cited sources count**, **Judge
  independently**, **Use the full scale**.
- **Examples.** Optional. Contrastive pairs ("Not this: ... This: ...") in one place
  instead of scattered through the rules. Generic or drawn from the public RFPs; never
  a fact the model could reuse as an answer.
- **Tone.** Register for every free-text field. Generators write for a bid team, about
  the RFP and the client as the RFP names it, with concrete values over adjectives, no
  hedging or marketing language, no markdown inside string fields, and no
  meta-references ("the inputs", "the evidence", "the summaries", "the findings", "the
  problem statement"): say "the RFP". Judges are terse: each `reason` names the
  decisive fact and restates its word cap.
- **Input blocks.** One `##` heading per block (`Document`, `Requirements`,
  `Sources`, ...), a one-line legend of the line format, then the data inside an XML
  tag. The first block is `## Document` with `Title: {{title}}` where a title exists.
  Code-built input uses `###` headings inside these blocks, so prompts use `##` only.
- **Final checks.** Three to five checkable items the model verifies before answering:
  every cited ID appears above, counts within range, quotes verbatim, no ID twice,
  empty lists where nothing applies, one entry per ID shown. A self-check next to the
  answer is the cheapest reliability lever; the dedupe prompt's "check that no ID
  appears twice" fixed its double-grouping on the first live run.

Conventions that hold across the structure:

- Variables are written `{{name}}` and substituted by `load_prompt(name).render(...)`
  in `llm.py`. A missing or unused variable is an error. Single braces elsewhere in
  the prompt (for example JSON examples) are left alone. Placeholders live in input
  blocks, except `{{unit}}` and `{{mode_rules}}` (extractor) and `{{what}}`
  (pairwise judge), which code splices into an instruction section.
- ID formats are shown in backticks and match the validators in `schemas.py`: chunk
  `S3.2`, requirement `R012`, ambiguity `A01`, gap `G01`, component `C01`, risk `K01`,
  finding `F1`, grounding item `I000`, claim label `goal[2]`.
- Counts are given as a target range and the code limit is named ("at most twelve;
  code rejects more than fifteen").
- Definitions shared by two prompts are copied word for word and tested: the
  requirement scope (gold, extractor, requirements judge; D31) and the risk scales
  (`risk.md`, `judge_risks.md`).
- Every prompt that emits factual claims about the RFP instructs the model to cite
  chunk IDs or requirement IDs; code validates the IDs afterwards.
- No prompt carries facts about a particular RFP. Everything document-specific comes
  in through variables.
- Files are LF-only (`.gitattributes`). The loader records a SHA-256 hash of every
  prompt file in the run log, so a changed prompt is visible in observability without
  reading the file.
- Design notes ("why it is written this way") and a changelog line for every change
  live in `docs/PROMPTS.md`, not here.
