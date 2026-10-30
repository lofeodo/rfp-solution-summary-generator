# ASSUMPTIONS.md

Living file. Add an entry whenever a step relies on something the assignment does not
state. Keep entries short; put reasoning in `DECISIONS.md`.

## Inputs

- **No `/inputs` RFP brief was provided** with the assignment; only the assignment PDF
  was. The project uses public US government RFPs as stand-ins. None contain real
  client data.
- **Primary brief**: Missouri DOT TR202504 "Using AI/ML to Write Legal Land
  Descriptions" (`data/rfps/missouri.pdf`, 20 pages). The scaffold step copies it to
  `inputs/rfp_brief.pdf` so the default invocation matches the assignment wording.
- **Eval set**: the primary brief plus three more public RFPs in `data/rfps/`:
  NY Empire State Development "AI Prep" (`NYESD.pdf`, 27 pages), City of Federal Way
  ERP RFP (`federal_way.pdf`, 16 pages), City of Colfax accounting software RFP
  (`colfax.pdf`, 22 pages). Four is the budget for gold labelling.
- The RFPs are text-native PDFs. Missouri's only image pages are two blank affidavit
  forms (Exhibits A and B); Federal Way page 5 holds a requirements table as an image.
  The core pipeline flags image pages and low-text pages but does not transcribe them.
- RFPs reference external documents (attachments, appendices, linked web pages). The
  pipeline records these references and treats absent ones as gaps; it does not fetch
  them.

## Parsing

- Running headers and footers carry no requirement content; they are stripped when they
  repeat on at least three pages (D21).
- `mailto:` links are contact addresses, not documents; only http(s) links are recorded
  as referenced documents. The addresses stay in the page text.
- A referenced attachment or exhibit counts as present only when its section in the PDF
  has at least 40 words; a cover page saying "provided separately" is absent (D22).
- OCR is off: image-only pages are flagged for S4, not transcribed (D20).

## Models and keys

- Hosted paid APIs are used instead of local models: small local models cannot do
  reliable long-context structured output, and reviewers cannot be assumed to have
  GPUs. The assignment allows "any free tier" and encourages free/open tooling; this
  is a deliberate deviation, defended in `DECISIONS.md`.
- Default generator for the whole pipeline: DeepSeek. Eval judge: Claude. A single
  model family per role, for time reasons; comparing families (Claude vs DeepSeek on
  cost, latency, quality) and using a third family for label drafting are stretch
  goals.
- Gold labels are drafted by the judge family (Claude) and hand-corrected. The
  fraction corrected is recorded with the labels.
- Keys live only in `.env`. The repo ships `.env.example`. The author hands reviewers a
  low-balance key out of band; no fallback provider is documented.
- Provider and model are one config setting, so any LangChain-supported chat model can
  be swapped in.
- Default generator `deepseek-flash` (DeepSeek V4.1 Flash) and judge
  `claude-sonnet-5-5`. The pricing table uses DeepSeek's peak-hour rates as an upper
  bound; off-peak is half, so reported DeepSeek cost may overstate actual spend.
- Cache-write tokens are costed at the normal input rate. Anthropic bills them at
  1.25x, so Claude cost is slightly under-counted on calls that write the cache;
  DeepSeek has no cache-write surcharge.
- DeepSeek runs with thinking mode off by default (`RFP_DEEPSEEK_THINKING`); its API
  default is on. Whether thinking improves output quality is measured in S13.

## Scope

- Five pipeline outputs are the deliverable: parsed document, requirements (with
  ambiguities), problem statement, solution approach, risks. JSON is the source of
  truth; markdown is rendered from it by code.
- Observability: Langfuse cloud free tier via the LangChain callback, plus a local JSON
  run log per run. The eval harness and UI read the JSON log, so nothing depends on
  Langfuse being reachable; tracing is a no-op when keys are absent.
- Local run plus a Dockerfile is the target; no cloud deployment in core.
- The demo recording is produced by the author; the README includes the demo script.
