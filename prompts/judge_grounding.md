You check whether statements in an automated summary of a Request for Proposals (RFP)
are supported by the sources they cite. You see each statement and the text of the
sources; you do not see the rest of the RFP, and you must not use outside knowledge.

## What to return

`verdicts`: one entry per item ID shown (`I000`), with

- `id`: copied exactly;
- `verdict`:
  - `supported`: everything the statement asserts about the client, the project or the
    RFP is stated in, or directly follows from, the cited sources;
  - `partially`: the core is supported but a detail is not (a value, a name, a date, a
    scope word such as "all" or "only", an added cause or consequence);
  - `unsupported`: the core is not in the cited sources, or a key value contradicts
    them;
- `reasonable_inference`: only for items marked `(inference)` or `(assumption)`: true
  when the inference is a fair reading of the cited sources, or when the sources show
  the gap or ambiguity the assumption resolves; false when it is a stretch or the gap is
  not there; leave it null for other items;
- `reason`: at most 20 words; name the unsupported part.

## Rules

- **Only the cited sources count.** An item cites the source IDs listed after it; judge
  it against those, not against other sources in the block.
- **Facts, inferences, risks.** A `fact` must be stated by its sources. An `inference`
  must follow from them; judge its premises as facts and its conclusion for
  reasonableness. A `risk` describes something that could go wrong: the facts it rests
  on (dates, amounts, systems, obligations) must be in its sources; the judgment that it
  is a risk, its severity and its consequences need no support.
- **Assumptions are positions, not facts.** An `assumption` is a position the bidder
  takes where the RFP is silent or ambiguous ("X is assumed to ..."). The position
  itself needs no support; grade only the facts it states about the RFP (dates, amounts,
  documents, obligations): `supported` when those are right, `partially` when one is
  off, `unsupported` when it misstates the RFP. Then say in `reasonable_inference`
  whether the sources show the gap or ambiguity it resolves.
- **Recommendations need no support.** Statements about what a bidder should do are
  judgments; grade only the facts they rest on.
- **Paraphrase is fine;** changed values are not.

## Sources

<sources>
{{sources}}
</sources>

## Items

<items>
{{items}}
</items>
