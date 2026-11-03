# Assumptions

What the project assumes where the assignment is silent. The reasoning lives in
[DECISIONS.md](DECISIONS.md). Every assumption made along the way, including
operational details, is in the [full log](archive/ASSUMPTIONS-full.md).

## TL;DR

- **No RFP brief was supplied, so four public US government RFPs stand in.** Missouri
  DOT is the primary brief. None of them contain client data.
- **Hosted paid APIs were chosen on purpose** over free or local models: DeepSeek
  generates and Claude judges. Reviewers get a low-balance key.
- **The gold labels are AI-made.** Claude drafted them and the coding agent corrected
  them. A procurement expert would label them in a real project. The judge was checked
  against hand labels and agreed on 34 of 40.
- **Nothing outside the PDF is fetched or OCR'd.** Missing attachments become gaps.
  Image-only pages are flagged, and the vision model that re-renders them is opt-in.
- **This is a local, single-user tool.** It has no authentication, and the reviewer's
  name at sign-off is not verified.

## Inputs and parsing

- The four RFPs are Missouri (20 pages), NYESD (27), Federal Way (16) and Colfax (22).
  All are text-native PDFs, and four was the gold-labelling budget.
- Running headers and footers carry no requirements, so they are removed when they
  repeat on three or more pages.
- An attachment counts as present only if its section has at least 40 words. A page
  saying "provided separately" counts as absent.
- Only pages that a heuristic flags are judged, so damage that no heuristic catches
  goes unnoticed.

## Pipeline

- Chunk size is counted in words, not tokens, so splitting does not depend on the model.
- The solution and risk agents never see the RFP text. They work only from the earlier
  stages' cited output, so a fact those stages missed can enter only as a labelled
  assumption.
- Coverage means cited coverage: a component that cites a requirement is taken to meet
  it. Whether it really does is a question for the judge.
- Submission rules such as format, copies and deadlines are excluded from mandatory
  coverage, because a solution component cannot meet them.
- Extraction follows the gold scope, so contract boilerplate is out. A quote that cannot
  be verified is kept and flagged, not dropped.

## Evaluation

- Grounding is judged only against the cited text. A true claim cited to the wrong chunk
  counts as unsupported.
- Three runs per RFP show which numbers move between runs. They are too few for
  confidence intervals.
- True recall lies between the code-only figure and the combined figure, because the
  judge's matches are slightly lenient.
- Federal Way's image-only table stays in the denominators. "Reachable" columns leave it
  out, so the parsing gap and extraction quality can be read separately.
- Reported cost is an upper bound: DeepSeek is priced at peak rates.

## Human in the loop

- The pursuit brief is trusted input from the bid team. It can be cited, but it never
  waives a mandatory requirement.
- A paused run waits indefinitely and survives restarts. A signed-off run is final.
- The CLI stops at the checkpoint by default, and `--unattended` skips it. The evals and
  the committed samples always run unattended.
