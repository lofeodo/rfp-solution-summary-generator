# Solution summary: TR202504 Using AI/ML to Write Legal Land Descriptions

- **Source:** inputs/rfp_brief.pdf
- **Run:** run-fixture-0001
- **Generated:** 2026-10-30T12:00:00+00:00
- **Model:** deepseek:deepseek-flash

## Problem statement

### Client situation

- MoDOT writes legal land descriptions by hand. (Background, p. 2 [S2.1])

### Goal

- Automate drafting of legal land descriptions. (Scope of Work, p. 4 [S3.1, S3.2])

### Success criteria

None.

### Constraints

- Budget capped at $175,000. (Schedule | Milestones, pp. 6-7 [S4.1])
- The budget is tight for a research-grade ML project. *(inference)* (Schedule | Milestones, pp. 6-7 [S4.1]; Scope of Work, p. 4 [S3.1])

## Requirements

5 requirements: 3 mandatory, 1 desired, 1 optional.

### Functional (1)

- **R001** (mandatory) The system must draft legal land descriptions from survey data. _(merged from R004, R009)_
  > "The contractor shall develop a tool that drafts legal land descriptions" (Scope of Work, p. 4 [S3.1, S3.2])

### Technical (2)

- **R002** (mandatory) Python use needs approval from the IS review team.
  > "Use of Python requires IS review-team approval" (IT Standards, pp. 13-18 [S7.1, S7.3])
- **R005** (optional) Reports may be delivered as plain PDF. _(conflicts with R003)_
  > "may be provided as PDF" (Scope of Work, p. 5 [S3.3]; [S9.9])

### Security and compliance (1)

- **R003** (desired) Outputs should meet WCAG 2.1 AA. _(conflicts with R005)_
  > "should conform to WCAG 2.1 AA" (IT Standards, pp. 13-18 [S7.1]) *(quote not verified)*

### Budget and pricing (1)

- **R006** (mandatory) Total cost must not exceed $175,000.
  > "not to exceed $175,000" (Schedule | Milestones, pp. 6-7 [S4.1])

### Ambiguities

- **A01** The output format for land descriptions is not specified. _(affects R001, R005)_ (Scope of Work, p. 4 [S3.2])
- **A02** Accuracy target is never quantified. (Scope of Work, p. 5 [S3.3])

### Gaps

- **G01** Sample deeds referenced for training are not attached. _(referenced document: Attachment B)_ (Scope of Work, p. 5 [S3.3])
- **G02** No data retention policy is given.

## Proposed solution

An extraction pipeline turns survey data into draft descriptions that a
surveyor reviews before filing.

### Coverage

Covers 1 of 3 mandatory requirements. Uncovered: R002, R006.

### Components

#### C01. Survey-data extractor

Parses plats and field notes into a structured parcel record.

Addresses: R001.

- Plats arrive as scanned PDFs. *(inference)* (Scope of Work, p. 5 [S3.3])

#### C02. Review workbench

A web UI where surveyors accept or edit each draft.

Addresses: R001, R003.

### Assumptions

- MoDOT can provide a few hundred historical deeds. *(inference)* (Background, p. 2 [S2.1])

## Risks

| ID | Risk | Severity | Likelihood | Source |
|---|---|---|---|---|
| K03 | Reviewer over-trust | high | high | Solution |
| K02 | Budget \| scope mismatch | high | medium | RFP |
| K01 | Python approval delay | medium | high | RFP |

### K03. Reviewer over-trust

Surveyors may accept drafts without checking them.

**Why:** Automation bias in review tools.

**Mitigation:** Highlight low-confidence calls in the workbench.

**Related requirements:** R001.

### K02. Budget | scope mismatch

ML research and a production tool for $175,000.

**Why:** The cap is fixed and the scope is open-ended. (Schedule | Milestones, pp. 6-7 [S4.1])

### K01. Python approval delay

IS review of Python could stall development.

**Why:** Approval is mandatory and has no stated turnaround. (IT Standards, pp. 13-18 [S7.1, S7.3])

**Mitigation:** Request approval in week one.

**Related requirements:** R002.

## Referenced documents

| Name | Kind | Page | Section | In PDF | URL |
|---|---|---|---|---|---|
| Attachment B | attachment | 5 | Scope of Work | no |  |
| MoDOT IT standards | hyperlink | 13 |  | yes | https://www.modot.org/it-standards |

## Parse flags

- Page 19: low word count (blank affidavit form)
- Page 20: large image block
