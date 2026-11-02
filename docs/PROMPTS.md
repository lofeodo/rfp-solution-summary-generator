# PROMPTS.md — prompt assets and change notes

The prompts themselves live in `prompts/`, one file per agent. This file is the
"notes on why they work" deliverable: a design note per prompt plus a changelog line
every time a prompt changes.

## Managing prompts

- One file per agent under `prompts/`, loaded by `load_prompt(name)` in
  `src/rfp_agent/llm.py`; `{{name}}` variables are substituted by code and a missing or
  unused variable is an error, so a prompt cannot silently lose an input.
- Every run log records the SHA-256 of each prompt file the run used
  (`prompt_hashes` in `runs/<id>/run_log.json`), so two runs can be compared knowing
  whether the prompt changed between them without reading the file.
- A prompt change is one commit with one changelog line below (what changed, and the
  observed failure or eval number that motivated it). The before/after figure comes
  from rerunning only the stage the prompt feeds: `python -m rfp_agent.agents <stage>
  <pdf> --requirements/--problem/--solution <json>` reuses the upstream outputs of a
  sample or an earlier run, and `python -m evals.harness score --label <l> --only
  <section>` reruns one judge and merges the result into the existing score file. A
  judge-prompt change is checked against the 40 hand-labelled verdicts
  (`evals/harness agree`) before it is kept.
- Prompts never carry facts about a particular RFP. Everything document-specific comes
  in through variables, and every prompt that states facts about the RFP must cite
  chunk or requirement IDs that code then validates.

## Design notes

Every prompt in `prompts/` has one block below, in this shape:

```
### prompts/<name>.md
Purpose:
Inputs it receives:
Output contract (schema):
Why it is written this way:   (the two or three choices that matter)
Known weaknesses:
```

### prompts/gold_requirements.md
Purpose: draft core gold requirements for one RFP (S11); a human pass corrects them.
Inputs it receives: `{{document}}`, the S2 parsed text with `[page N]` markers.
Output contract (schema): `DraftRequirements` in `evals/gold/label.py` (text, type,
strictness, quote, page, section); IDs and provenance are assigned by code.
Why it is written this way: an explicit include/exclude list carries the core-only scope
(D23), since "requirement" alone pulls in every boilerplate clause; strictness is defined
by modal verb so labels are reproducible; the quote must be the shortest verbatim span
inside one sentence or table cell, because code drops any item whose quote is not found.
Known weaknesses: still over-inclusive on standard certifications and procurement-conduct
rules (13 to 16 removals per RFP); occasionally skips concrete delivery duties stated in
narrative paragraphs or dated milestone tables.

### prompts/gold_checklist.md
Purpose: draft 8 to 12 must-mention facts for a problem statement (S11).
Inputs it receives: `{{document}}`, as above.
Output contract (schema): `DraftChecklist` (fact, quote, page); size 8 to 12 enforced by a
validator so a short list is retried (F4).
Why it is written this way: a coverage list (issuer, need, deliverable, budget, dates,
constraints, absent documents) so the checklist tests understanding, not trivia; facts
must carry the concrete number or name so a grader can tick them unambiguously.
Known weaknesses: tends to spend slots on schedule details and evaluation weights rather
than referenced-but-absent documents (replaced by hand in 3 of 4 RFPs).

### prompts/parse_quality.md
Purpose: judge whether one heuristically flagged page's extracted text is usable and
whether the page holds content the text lacks (S4).
Inputs it receives: `{{title}}`, `{{page_number}}`, `{{page_count}}`, `{{flags}}` (reason
and detail per flag), `{{images}}` (size and caption per image, or "none"),
`{{markdown}}` (the page text, or "(empty)").
Output contract (schema): `PageJudgement` in `schemas.py` (`text_usable`,
`content_missing`, `page_kind`, `confirmed_flags`, `reason`). Code turns it into an
escalation and decides who triggered it (D24).
Why it is written this way: each flag comes with its typical false alarm (contents pages,
covers, "intentionally left blank" dividers, logos, one-column contents tables) because
those are most of the flags on the four RFPs; the two booleans are asked separately so a
page with clean text around an image table is still caught; the model is told it never
sees the image, so it reasons from captions and lead-in sentences ("the following
tables") instead of guessing. No citations: it makes no claims about the RFP's content.
Known weaknesses: cannot see the image, so a decorative large image next to a sentence
that sounds like a lead-in could be escalated; blank fill-in forms (Missouri affidavits)
are escalated although transcribing them adds little. ST2 added one line for the
`garbled_text` flag (encoding failures), which no public RFP triggers.

### prompts/parse_vlm.md
Purpose: transcribe one page the parse-quality pass escalated from its rendered image,
so the transcription can replace the library parser's markdown (ST2).
Inputs it receives: `{{title}}`, `{{page_number}}`, `{{page_count}}`, `{{reason}}` (the
judge's one-sentence verdict, or the flagged-scope note), `{{library_markdown}}` (the
page text the library produced, or "(empty)"). The page image travels in the same
message as an `image_url` block ahead of the text.
Output contract (schema): `VlmTranscription` in `schemas.py` (`markdown`, `notes`). Code
replaces the page's markdown, recounts words, rebuilds that page's tables, clears its
flags and keeps the library text beside the transcription in a `TranscriptionRecord`.
Why it is written this way: the splitter and the extractors read the page as markdown
and quote it verbatim, so the prompt asks for reading order, exact heading wording (the
splitter locates PDF outline entries by their text), pipe tables with one header row and
columns in the image's order, and spanning values repeated rather than merged, which
is what the gold quotes look like ("Quadrant | Cashiering | Replace | ..."). The library
text is passed as a labelled reference because it is usually right about spelling and
numbers in the clean parts of a page; the image wins on any conflict. `[illegible]`
instead of guessing keeps the quote-verification contract honest.
Known weaknesses: a repeated header row inside a printed table comes back as a data row
(Federal Way p5); multi-line bullet lists inside a cell are joined with semicolons, so a
gold quote that spans two cells may not match by containment.

### prompts/problem_chunk.md
Purpose: stage one of the problem statement (S6): what one chunk says about who the
client is, what they need and why, and under what constraints.
Inputs it receives: `{{title}}`, `{{chunk_id}}`, `{{section_path}}` (`A > B`),
`{{pages}}`, `{{text}}` (the chunk, overlap sentence included).
Output contract (schema): `ChunkSummaryDraft` in `schemas.py` (`relevant`, `summary`);
code attaches the chunk ID (D28).
Why it is written this way: the relevance list mirrors the gold checklist categories
(issuer, need, deliverables, dates, money, constraints, evaluation, referenced documents)
so stage one keeps exactly what the synthesis must cite; "keep every number, date, amount,
name and document exactly" because the synthesis can only state values that survive
stage one; the model is told it sees one chunk and must not guess the rest, which keeps
summaries factual; the irrelevant list names the boilerplate seen on the four RFPs
(contents, cover, signature blocks, generic clauses).
Known weaknesses: summaries run long (NYESD: 76k input tokens become 13k of summaries,
little shorter than the 18.5k full text); "two to five sentences" is advisory and not
enforced. Relevance is generous (60 to 63 of 70 NYESD chunks), which is the safe side.

### prompts/problem_synthesis.md
Purpose: stage two of the problem statement (S6), and the full-text baseline: four lists
of cited claims (client situation, goal, success criteria, constraints).
Inputs it receives: `{{title}}`, `{{evidence_kind}}` (one sentence saying whether the
evidence is summaries or full text), `{{evidence}}` (items labelled `[S3.2] section
path (pages n)`).
Output contract (schema): a per-call subclass of `ProblemStatement` that rejects empty
lists and chunk IDs outside the evidence (D28).
Why it is written this way: each list is defined by the questions a bid team asks, with
the checklist categories spread across them so nothing has two homes; "state the concrete
value" with a positive and a negative example, because a claim without the number is not
checkable; `fact` vs `inference` is defined by whether a cited chunk states the claim,
since S12's grounding judge checks exactly that; "three to eight per list" is advisory,
the validator enforces only non-empty; the same prompt serves both modes so the S13
ablation varies the evidence only; the last rule ("write about the RFP, never the
evidence") came from F6.
Known weaknesses: in 2 of 4 NYESD runs the first attempt cited an ID outside the evidence
or left a list empty (F7); the model occasionally spends a constraint slot on a
procedural detail (upload folder layout) rather than a solution constraint.
### prompts/requirements_extract.md
Purpose: extract core requirements, ambiguities and gaps from one chunk (S5); the same
file, with `{{unit}}` and `{{mode_rules}}` swapped, serves the single-call ablation over
every chunk.
Inputs it receives: `{{unit}}` (what the model is given and that other chunks are handled
separately), `{{mode_rules}}` (empty, or the chunk-ID citation rule in document mode),
`{{title}}`, `{{input}}` (one or many `### Chunk S3.2` blocks with section path, pages and
the text in `<chunk>` tags).
Output contract (schema): `ChunkExtraction` or `DocumentExtraction` in `schemas.py`.
Code assigns IDs, cites the chunk, verifies quotes (D29) and dedupes.
Why it is written this way: the include/exclude scope is the gold prompt's, so extractor
and labeller agree on what a requirement is (D31); the exclude list names the boilerplate
clauses the first run kept (assignment, independent contractor, audit, FFATA) and says a
form is one item, not one per field; "many chunks contain no requirement" and "returning
empty lists is correct" stop the model inventing obligations from headings; the quote
rule says code checks it verbatim, which makes the model copy rather than tidy;
ambiguities and gaps both carry a "not this" list, because the first run reported other
sections of the same RFP as missing (F8); the instructions come first and the chunk last
so DeepSeek's prefix cache serves about three quarters of the input tokens.
Known weaknesses: still generous with `submission` items (proposal-content lists split
finely) and with ambiguities (29 to 70 per RFP); the gap definition pulls in every
linked form on a form-heavy RFP (NYESD 38); output varies between runs at temperature 0.

### prompts/requirements_dedupe.md
Purpose: one grouping pass over the exact-deduped list: which IDs state the same
obligation, which contradict (D6, D30).
Inputs it receives: `{{requirements}}`, one line per item: `ID [strictness, type] text —
"quote" (chunk IDs)`.
Output contract (schema): `DedupeOutput` (groups with `representative_id` and
`member_ids`, conflicts with IDs and a reason). Code checks it, feeds violations back
once, sanitises, merges.
Why it is written this way: "same obligation on the same party about the same thing"
with signs for and against, because the failure mode is over-grouping a general duty with
a specific one; the representative is the most specific statement so the merged item
keeps the best text and quote; the one-ID-once rule is stated twice and ends with "check
that no ID appears twice", added after the first run put R030 in three groups on both
turns; alternatives and a standard next to its stricter version are called out as
non-conflicts after Missouri's Oracle/SQL Server and Section 508/WCAG pairs were flagged.
Known weaknesses: the first answer still breaks the contract on most RFPs (the feedback
turn fixes it); alternatives are still sometimes flagged as conflicts.

### prompts/solution.md
Purpose: the proposed approach: a summary, components that cite the requirement IDs
they satisfy, and the assumptions the design rests on (D32).
Inputs it receives: `{{title}}`, `{{problem}}` (the four claim lists, each claim with
its chunk IDs and an `(inference)` mark), `{{requirements}}` (mandatory, desired and
optional blocks, one line per item `ID [strictness, type] text (chunk IDs)`, then the
submission items under "context, do not address"), `{{ambiguities}}`, `{{gaps}}`,
`{{brief}}` (ST12: the pursuit team's guidance as `H1: text` lines, one per paragraph
of the brief written at the checkpoint, or "None provided."). No RFP text and no
quotes.
Output contract (schema): `SolutionDraft`; a per-call subclass rejects empty components,
a component with no requirement IDs, and unknown requirement or chunk IDs; the brief's
`H` IDs are among the known chunk IDs when a brief exists. Code assigns `C01…`,
computes coverage, and feeds the uncovered mandatory IDs back in a revision round
(same conversation) while any remain, up to the round cap.
Why it is written this way: the coverage rule is explicit and says that code computes
it and that misses become risks, so the model has a reason to cite completely rather
than describe elegantly; legal, insurance and reporting obligations are named as things
a governance component cites, because a model left alone writes only the technical
components and the uncovered list fills with contract terms; the submission block is
labelled "do not address" so the model does not build a "proposal writing" component;
claims are discouraged ("most components need no claims") because restating
requirements as claims adds citations without evidence; assumptions must state the
position taken, not the ambiguity, so S8 can read them as design decisions; the F6
rule (write about the RFP, never "the inputs") is carried over; instructions come first
so the provider prefix cache serves repeated rounds. S13 added "name what you cite":
a description must mention each cited obligation and what meets it, because the S12
coverage judge found bulk-cited legal and contractual clauses that no component
described (NYESD judged coverage 78% against 100% cited); the rule lets a compliance
component exceed the five-sentence guide so the two rules do not fight. ST12 added the
"Pursuit team guidance" block and rule: the guidance steers design choices (stack,
phasing, emphasis) and must be cited (`H2`) wherever a component rests on it, so a
reviewer can tell the team's input from the RFP's; it never waives a mandatory
requirement, and a conflict becomes an assumption citing both, because the compliance
matrix outranks the win strategy (D45).
Known weaknesses: proposal-process obligations that S5 typed `timeline` or
`budget_pricing` rather than `submission` are in scope, so the revision round makes the
model add a commercial or submission-flavoured component to cite them (Missouri R007,
R019); the assumption list runs long (Missouri 8) and some assumptions restate facts the
problem statement already carries.

### prompts/risk.md
Purpose: the risks of bidding and delivering: what could go wrong, how badly, how
likely, and what the bidder would do about it (D33).
Inputs it receives: `{{title}}`, `{{findings}}` (five blocks computed by code: mandatory
requirements the solution does not address, conflicting requirement pairs, referenced
documents not in the PDF, pages whose text could not be parsed, the budget-requirement
count), `{{solution}}` (summary, components as `ID Title (requirement IDs)` with their
description and claims, assumptions, the coverage line), `{{problem}}`,
`{{requirements}}` (as S7, but the submission block is headed "how and when the proposal
is delivered", not "do not address"), `{{ambiguities}}`, `{{gaps}}`, `{{brief}}` (ST12,
as in the solution prompt). No RFP text.
Output contract (schema): `RiskAssessmentDraft`; a per-call subclass rejects fewer than
3 or more than 15 risks, unknown requirement or chunk IDs, and a draft in which an
uncovered mandatory requirement is cited by no risk. Code sorts by severity then
likelihood and numbers `K01…`.
Why it is written this way: the findings come first and the "Findings first" rule says
code checks the uncovered IDs, so the model works from facts before it speculates; the
two scales are written out as impact and as "given the RFP and the solution as
written", so a `high` means the same thing on every RFP; `source` is defined by what
creates the risk, not by where the words came from; "one risk, one cause" with a worked
contrast stops requirement restatements; `chunk_ids` may be empty for a flagged page or
a missing document because those have no chunk; mitigation is asked to be an action (a
question before the deadline, a stated assumption, a contingency), not "monitor"; the F6
tone rule is carried over with "the findings" added to the banned phrases; instructions
come first for the prefix cache. ST12 added the "Pursuit team guidance" block and rule:
a risk that rests on something the team set or learned (a constraint, an informal
client statement, a design choice) cites its `H` ID, and a risk the guidance creates has
`source` `solution`, so commercial and team risks are traceable to the brief (D45).
Known weaknesses: the count runs to the top of the range or one over (F12); severity
clusters at high and medium (no `low` severity and one `low` likelihood in 50 risks on
the tuned prompt), so the scales separate less than they could; `source` can flip
between runs for the same risk (NYESD's MWBE goals: `rfp`, then `solution`), which
S12's judge should sample.

### prompts/revise_requirements.md, revise_problem.md, revise_solution.md, revise_risk.md (ST12b)
Purpose: apply one reviewer instruction to one artefact after (or, for requirements and
the problem statement, before) the checkpoint (D46).
Inputs it receives: all four get `{{title}}` and `{{instruction}}` near the top, then the
current artefact, then the context the producing stage's prompt showed:
`revise_requirements` the current list (`ID [strictness, type] text — "quote" (chunks)`)
and `{{chunks}}`, every chunk's own text with its ID, section and pages, so a new quote
can be copied; `revise_problem` the statement, `{{evidence_kind}}` and `{{evidence}}` as
the synthesis saw them (summaries, or the full text) and `{{brief}}`; `revise_solution`
the solution as the risk prompt formats it plus problem, requirements, ambiguities, gaps
and brief; `revise_risk` the current risks (`ID [severity/likelihood, source] title
(requirement IDs; chunk IDs)` with description, justification, mitigation), the findings
recomputed by code, and the risk prompt's other blocks.
Output contract (schema): `RequirementsPatch` (edits by ID with only the changed fields,
additions with quote and chunk ID, removals); `ProblemStatement`; `SolutionDraft` with an
optional `id` per component (`SolutionRevision`); `RiskAssessmentDraft` with an optional
`id` per risk (`RiskAssessmentRevision`). The tool names are the stage's, and the
per-call validators are the stage's own plus ID checks and, for the solution, a refusal
of any coverage regression.
Why it is written this way: "only what the instruction asks; everything else exactly as
it is now" is the first rule of each, because the diff is the audit trail and an
unasked rewording is noise in it; requirements return a patch because the list is too
long to return whole (D46, F16) and the patch explains how to merge and split with
edit, add and remove; the quote rule says code checks every quote, and an empty patch is
named as the right answer when the RFP does not support the instruction, so the model is
not pushed to invent a requirement; the solution prompt states that code refuses a
coverage regression, so the model keeps mandatory IDs instead of learning it from a
retry; the guidance rules are the same as in the drafting prompts (cite `H` IDs, never
waive a mandatory requirement); "never mention the instruction or the reviewer" keeps
the deliverable free of meta-talk.
Known weaknesses: the requirements prompt shows every chunk (about 11k tokens of text on
Missouri), which is the price of letting an addition quote anywhere; whole-artefact
revisions can still reword untouched text slightly, which the diff shows as changes.

### Judge prompts (S12): shared design
The seven `judge_*` prompts are run by the eval harness on the judge model
(`Settings.judge_model`, effort `medium`), never by the pipeline. They follow the agent
prompts' layout: a role line naming what is being graded, `## What to return` with one
bullet per schema field, `## Rules` with bold rule names, data last in tagged blocks.
Every verdict carries a short `reason` with a word cap, so the score files read as an
audit trail and output tokens stay bounded. Every list answer is checked by a per-call
schema that demands exactly one entry per ID shown (D36); the prompts say "use only the
IDs shown" but code enforces it. Design decisions D36 and D37.

### prompts/judge_match.md
Purpose: for gold requirements code could not match, name the extracted items that
state the same obligation (recall, judge tier).
Inputs it receives: `{{gold}}` (up to 15 gold items with strictness, type, page and
quote), `{{candidates}}` (extracted items cited on those pages plus or minus one).
Output contract (schema): `MatchVerdicts{matches[gold_id, requirement_ids, reason]}`;
unknown requirement IDs are dropped by code.
Why it is written this way: "same obligation, any wording" with the bidder test ("a
bidder who met the candidate would meet the gold item's core"), many-to-many explicitly
allowed because the extractor splits and merges, labels shown but not graded so a type
disagreement does not block a match.
Known weaknesses: the first version accepted candidates that omitted the gold item's
key value (F14); S13 added the "missing values do not match either" rule with two
examples from the Missouri disagreements and rescored the baseline match tier. Recall
is still reported next to its code-only lower bound because the judge tier remains a
judgment.

### prompts/judge_requirements.md
Purpose: precision: is each extracted requirement stated by its chunk, a real
obligation, and in the gold scope.
Inputs it receives: `{{sources}}` (the cited chunks with their section path and page),
`{{requirements}}` (up to 25 items: statement, quote, cited chunk IDs).
Output contract (schema): `ItemVerdicts{verdicts[id, supported, is_requirement,
in_scope, reason]}`.
Why it is written this way: the three questions are separate so surplus (out of scope)
is never counted as error (D31); the scope definition is the gold one (D23), with the
boilerplate and procurement-conduct examples written out; strictness and type are
explicitly not graded, because type accuracy is measured against gold.
Known weaknesses: `supported` is near the ceiling because quotes are already verified
by code; the judge reads "can be found here" literally and once rejected a required
form whose obligation sat in the section heading.

### prompts/judge_grounding.md
Purpose: is each cited assertion supported by the text it cites, and only that text.
Inputs it receives: `{{sources}}` (every cited chunk or requirement in the batch),
`{{items}}` (up to ten items, each with its kind and its cited IDs).
Output contract (schema): `ClaimVerdicts{verdicts[id, verdict, reasonable_inference,
reason]}`, verdict one of supported, partially, unsupported (checked in code).
Why it is written this way: "only the cited sources count" makes this a citation test;
four kinds are graded differently: facts must be stated, inferences must follow,
assumptions are positions whose stated facts must be right and whose gap must be real,
risks are judged on the facts they rest on; recommendations need no support.
Known weaknesses: `partially` absorbs added consequences ("which sets the training
cohort size"), which is correct but makes the count sensitive to style; on one sampled
assumption the judge said "none misstated" and still answered `partially`.

### prompts/judge_checklist.md
Purpose: checklist coverage of the problem statement against the 12 gold facts.
Inputs it receives: `{{statement}}` (every claim labelled `list[index]`), `{{facts}}`.
Output contract (schema): `ChecklistVerdicts{facts[gold_id, status, claim, reason]}`;
the claim label must exist when the status is not `missing`.
Why it is written this way: `partial` is defined as "topic without the detail" or
"part of a compound fact", and a wrong value is at best partial, so the number rewards
concrete statements; the "read every claim" rule exists because facts land in
unexpected lists.
Known weaknesses: compound gold facts make `partial` common (an issue date missing from
a list of deadlines); one sampled verdict counted a compound fact as covered with one
part missing.

### prompts/judge_solution.md
Purpose: rubric (specificity, feasibility, consistency with constraints), judged
coverage (does each component actually meet what it cites), calendar components.
Inputs it receives: `{{goal}}`, `{{constraints}}`, `{{summary}}`, `{{components}}`
(each with its description and cited requirements in full), `{{assumptions}}`.
Output contract (schema): `SolutionVerdict` with three `RubricScore`s and
`components[id, not_addressed, calendar, reason]`; `not_addressed` must be a subset of
what the component cites.
Why it is written this way: anchored 1/3/5 descriptions for each rubric axis; "actually
meets means the description says how", with the same allowance S7 gives governance
components (naming the obligation or its category counts); `calendar` answers S7's open
issue directly.
Known weaknesses: the rubric barely moves (specificity 4 on every run, feasibility 3 or
4), so it separates little at this quality level; the category allowance is applied
inconsistently (two of eight sampled pairs disagreed with the hand label, one each way).

### prompts/judge_risks.md
Purpose: rate each risk's severity and likelihood on the S8 scales; say which code
findings the register addresses.
Inputs it receives: `{{risks}}` (title, description, mitigation, cited requirements;
not the pipeline's levels or justification), `{{findings}}` (conflict pairs, absent
documents, flagged pages, uncovered requirements, each `F1…`).
Output contract (schema): `RiskVerdicts{risks[id, severity, likelihood, reason],
findings[id, covered_by]}`.
Why it is written this way: the scales are copied from `prompts/risk.md` so both sides
use one definition; the pipeline's levels are hidden so agreement measures the scales,
not anchoring; "a generic risk does not cover a specific missing document".
Known weaknesses: likelihood agreement is low (50 to 92%) because "turns on facts the
RFP does not settle" and "expected unless someone acts" overlap; with the levels
visible, agreement was 100%, so earlier "agreement" numbers would have meant nothing.

### prompts/judge_pairwise.md
Purpose: A/B preference between two problem statements or two solutions, for S13's
ablations.
Inputs it receives: `{{what}}`, `{{context}}` (the gold checklist or gold requirements,
run-independent), `{{output_a}}`, `{{output_b}}`.
Output contract (schema): `Preference{preferred: A|B|tie, reason}`; the harness asks
twice with the order swapped and counts a win only when both orders agree.
Why it is written this way: the gold reference gives the judge something to check
accuracy against instead of preferring the longer text; "length is not quality" and
"position is irrelevant" are stated, and the swap measures position bias anyway.
Known weaknesses: one live comparison so far (Missouri, hierarchical won both orders);
the two answers' reasons cited different strengths, so ties will be common on close
pairs.

## Changelog

One line per change. Newest first.

| Date | Prompt | What changed | Why (observed failure or eval result) |
|---|---|---|---|
| 2026-11-02 | parse_vlm | Created (ST2) | First version; live Federal Way p5 returned the full ERP environment table (18 rows, every gold row verbatim), Missouri p19/p20 forms at 420 and 453 words with their exhibit headings |
| 2026-11-02 | parse_quality | One line describing the `garbled_text` flag and its false alarm | ST2 added the flag for undecodable fonts; the judge must know what it means |
| 2026-11-02 | revise_requirements, revise_problem, revise_solution, revise_risk | Created (ST12b) | First version; instruction-driven revision of one artefact under the producing stage's validators (D46); first live results in `docs/hitl/ST12b-revise.md` |
| 2026-11-02 | solution, risk | "Pursuit team guidance" input block (`{{brief}}`, `H1: text` lines or "None provided.") and a rule: follow it for design choices, cite `H` IDs for anything that rests on it, never waive a mandatory requirement (solution); cite `H` IDs for risks that rest on it, `source` `solution` for risks it creates (risk) | ST12 checkpoint: the brief written by the pursuit lead must reach the drafter and stay traceable (D45); unattended runs render "None provided." so their output is unchanged |
| 2026-10-30 | solution | Rule "Name what you cite": the description names each cited obligation and what meets it; a compliance component may exceed five sentences | S12 coverage judge: bulk-cited legal clauses no component described, NYESD judged coverage 78% against 100% cited; 94% after (Colfax 96 → 99%, Missouri 97 → 96%, Federal Way 100 → 98%), descriptions 30 to 50% longer |
| 2026-10-30 | judge_match | Rule: a candidate that omits the gold item's key value does not match unless another listed candidate supplies it, with two Missouri examples | Judge-tier matches accepted items missing the gold date or standard (F14); baseline match tier rescored: Missouri combined recall 99 / 100 / 94% → 93 / 93 / 87%, other RFPs within one point |
| 2026-10-30 | judge_grounding, judge_risks | Grounding: an `assumption` kind judged as a position (facts it states, and whether the gap is real); risks: the judge no longer sees the pipeline's levels or justification, "use the full scale" | First Federal Way scoring: assumptions graded as facts (4 unsupported, 11 partially of 22 solution items) and 100% level agreement while the levels were shown; 0 / 7 and 92% / 58% after |
| 2026-10-30 | judge_match, judge_requirements, judge_grounding, judge_checklist, judge_solution, judge_risks, judge_pairwise | Created (S12) | First version; 34 of 40 sampled verdicts agree with hand labels |
| 2026-10-30 | risk | Count rule under Rules: at most twelve, merge or drop, code rejects more than fifteen | All four first runs returned 13 against "six to twelve" (F12); 12, 13, 13, 12 after |
| 2026-10-30 | risk | Created (S8) | First version; 12 to 13 risks per RFP, 0 validator retries, every code finding surfaced as a risk |
| 2026-10-30 | solution | Assumptions: `chunk_ids` are the `S4.2` IDs listed after the ambiguity or gap; `A01`/`G01` are never cited | Colfax and Federal Way first runs cited ambiguity and gap IDs as chunks, caught by the validator (F10); 0 retries on the four-RFP rerun |
| 2026-10-30 | solution | Created (S7) | First version; full mandatory coverage on four RFPs after at most one revision round |
| 2026-10-30 | requirements_extract | Gaps: name the document, never its URL; a document named with its link is one gap | NYESD listed 50 gaps, most forms twice (name and URL) (F9); 38 after |
| 2026-10-30 | requirements_extract | Expanded boilerplate exclusions, one item per form; ambiguities and gaps exclude content defined elsewhere in the same RFP and ordinary lack of detail | Missouri first run: 144 requirements, 105 ambiguities, 39 gaps, most "not in this chunk" (F8); 131 / 53 / 12 after |
| 2026-10-30 | requirements_dedupe | "An ID may appear once across the whole answer; check before answering"; alternatives and a standard next to its stricter version are not conflicts | Missouri first run: R030 in three groups on both turns (fallback used); clean after one turn on all reruns |
| 2026-10-30 | requirements_extract, requirements_dedupe | Created (S5) | First version |
| 2026-10-30 | problem_synthesis | Rule: write about the RFP, never "the evidence" or "the summaries" | F6: 3 of 4 live outputs leaked the prompt's framing into claims; 0 of 2 after |
| 2026-10-30 | problem_chunk, problem_synthesis | Created (S6) | First version; rough checklist coverage 12/12 on four RFPs |
| 2026-10-30 | parse_quality | Created (S4) | First version; 12 of 12 live verdicts matched manual inspection |
| 2026-10-30 | gold_requirements, gold_checklist | Created (S11) | First version |
