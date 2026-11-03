# Decisions

The trade-offs a reviewer is most likely to ask about. Each ID links to its full entry
(context, options, reasoning, evidence) in the [full log](archive/DECISIONS-full.md).

## TL;DR

- **Every claim cites an ID that code checks.** No scored run has had a dangling ID.
- **Code owns the rules, LLMs fill schemas.** Code checks coverage, quotes and
  citations inside bounded retries.
- **One revision loop, with a target code computes.** There is no critic agent.
- **Evals use code first, then a judge.** Recall is 80 to 100% and precision 95 to 99%.
  The judge agrees with 34 of 40 hand labels.
- **Ablations are reported plainly.** Cheaper paths match quality. The defaults are kept
  for scale.
- **About $0.05 to $0.10 and under 2.5 minutes per RFP.** Judging costs about six times
  as much as generation.
- **A human gates the draft.** They confirm a checkpoint, add a citable brief, revise by
  instruction and sign off.

## Key decisions

- **[D4](archive/DECISIONS-full.md#d4-chunk-id-citations-instead-of-retrieval-based-grounding)
  Chunk-ID citations, not RAG.** Each RFP fits in one context window. Citations make
  unsupported claims countable and let the UI show the source of any claim.
- **[D17](archive/DECISIONS-full.md#d17-structured-output-provider-native-mode-inside-a-code-owned-retry-loop)
  Retries owned by code.** Each provider uses its native schema mode. Validation errors
  go back to the model in a bounded loop.
- **[D32](archive/DECISIONS-full.md#d32-solution-coverage-computed-by-code-revised-in-a-capped-langgraph-loop)
  Coverage loop.** The solution is revised until code finds no uncovered mandatory
  requirement, at most three times. It reached 100% on 12 of 12 runs.
- **[D40](archive/DECISIONS-full.md#d40-no-critic-or-free-revision-loop-the-evals-show-prompt-shaped-faults-and-the-one-revision-loop-with-a-code-computed-target-already-exists)
  No critic.** Every fault the evals found was fixed by a prompt rule. A critic would
  be a second opinion with no ground truth.
- **[D39](archive/DECISIONS-full.md#d39-ablations-hierarchy-and-chunking-are-kept-for-scale-and-traceability-not-for-quality-the-evals-can-see)
  Ablations.** A single call gets within 2 pp of per-chunk recall at 30 to 45% less
  cost, but it truncates on long documents.
- **[D36](archive/DECISIONS-full.md#d36-evals-code-first-judge-second-recall-against-gold-precision-judged-per-item)
  Code-first evals.** Code settles 61 to 94% of gold matches at no cost, and a judge
  handles the rest.
- **[D37](archive/DECISIONS-full.md#d37-grounding-code-heuristics-plus-a-judge-that-sees-only-what-is-cited)
  The grounding judge sees only the cited text.** This tests the citation itself. When
  the pipeline's risk levels were hidden from the judge, its agreement fell from 100% to
  92% on severity and 58% on likelihood.
- **[D23](archive/DECISIONS-full.md#d23-gold-labels-core-only-scope-claude-drafts-agent-corrects-diff-is-the-record)
  AI-drafted gold labels.** Claude drafted them and the coding agent corrected 19 to
  26% of each draft. The draft is committed next to the final labels.
- **[D3](archive/DECISIONS-full.md#d3-deepseek-generates-claude-judges-single-family-per-role)
  DeepSeek generates, Claude judges.** A separate model family keeps the judge
  independent of the generator.
- **[D42](archive/DECISIONS-full.md#d42-vision-model-transcription-replaces-the-page-gated-by-the-judge-off-by-default-st2)
  Optional VLM.** It re-renders pages that the judge confirms are damaged. It is off by
  default.
- **[D44](archive/DECISIONS-full.md#d44-pause-and-resume-through-the-run-directory-not-a-langgraph-checkpointer-d1-extended)
  Pause through the run directory, not a LangGraph checkpointer.** A review can last
  days and must survive restarts.
- **[D46](archive/DECISIONS-full.md#d46-revision-by-instruction-a-patch-for-requirements-the-whole-artefact-for-the-rest-the-producing-stages-validators-either-way)
  Revision by instruction.** Requirements are revised by patch, so long lists never
  truncate. Code refuses any revision that loses coverage.

## Changes the author drove

1. **Tables were lost in parsing.** The author asked for a vision model that re-renders
   badly converted content, not just images. That became D42, which raised Federal Way
   recall from 81% to 95%.
2. **Human in the loop, redesigned.** The author rejected the first designs. The
   replacement is the single mode a pursuit lead would use (D43): a checkpoint before
   drafting and a sign-off after.
3. **One prompt structure for every prompt (D51).** The measured effect was neutral to
   slightly positive.
4. **Models cut from three families to two (D3)** to fit the time budget.
5. **Fixes from using the app.** The README now leads with the UI after its run
   command failed. The author also asked for run removal (D52) and for the README to
   disclose that the gold set is AI-made.

<details>
<summary>Index of every decision and failure mode</summary>

**Orchestration and contracts:** [D1](archive/DECISIONS-full.md#d1-langgraph-as-the-orchestration-framework) LangGraph · [D34](archive/DECISIONS-full.md#d34-one-langgraph-graph-of-thin-stage-wrappers-runtime-objects-in-closures-outputs-on-disk-per-stage) one graph of thin stage wrappers · [D17](archive/DECISIONS-full.md#d17-structured-output-provider-native-mode-inside-a-code-owned-retry-loop) structured output in a code-owned retry · [D14](archive/DECISIONS-full.md#d14-schema-conventions) schema conventions · [D8](archive/DECISIONS-full.md#d8-markdown-rendered-by-code-from-json) markdown rendered from JSON · [D16](archive/DECISIONS-full.md#d16-markdown-layout-citation-format-strict-assembly) strict assembly, citation format · [D18](archive/DECISIONS-full.md#d18-observability-recording-explicit-recorder-in-a-context-variable) run recorder · [D15](archive/DECISIONS-full.md#d15-install-and-config-mechanics) install and config · [D12](archive/DECISIONS-full.md#d12-repo-layout-and-branch-model) repo layout and branches

**Models and cost:** [D2](archive/DECISIONS-full.md#d2-hosted-paid-apis-instead-of-local-models) hosted APIs · [D3](archive/DECISIONS-full.md#d3-deepseek-generates-claude-judges-single-family-per-role) DeepSeek generates, Claude judges · [D13](archive/DECISIONS-full.md#d13-model-ids-and-pricing-source) model IDs and pricing · [D19](archive/DECISIONS-full.md#d19-sampling-and-cost-settings-per-provider) sampling and cost settings

**Parsing:** [D9](archive/DECISIONS-full.md#d9-parsing-library-first-heuristics-flag-llm-judges-flagged-pages-vlm-is-stretch) parsing ladder · [D20](archive/DECISIONS-full.md#d20-parsing-layout-path-with-ocr-off-flag-thresholds-as-constants) OCR off, flag thresholds · [D21](archive/DECISIONS-full.md#d21-running-headers-and-footers-are-stripped-only-when-they-repeat) repeating headers stripped · [D10](archive/DECISIONS-full.md#d10-referenced-documents-are-recorded-never-fetched) references never fetched · [D22](archive/DECISIONS-full.md#d22-a-referenced-document-is-present-only-if-its-section-has-a-body) a reference is present only with a body · [D24](archive/DECISIONS-full.md#d24-parse-quality-two-boolean-verdict-attribution-by-match-flags-replaced) parse-quality verdict · [D42](archive/DECISIONS-full.md#d42-vision-model-transcription-replaces-the-page-gated-by-the-judge-off-by-default-st2) VLM transcription

**Splitting and extraction:** [D25](archive/DECISIONS-full.md#d25-section-boundaries-the-outline-located-in-the-text-then-markdown-then-promotion) section boundaries · [D26](archive/DECISIONS-full.md#d26-chunks-300-word-cap-cut-at-paragraphs-tables-atomic-one-sentence-of-overlap) 300-word chunks · [D27](archive/DECISIONS-full.md#d27-section-kind-any-obligation-cue-makes-a-section-requirement-bearing) obligation cues · [D5](archive/DECISIONS-full.md#d5-exhaustive-per-chunk-extraction-no-rag-in-extraction) per-chunk extraction · [D29](archive/DECISIONS-full.md#d29-quote-verification-one-feedback-turn-then-keep-the-item-as-unverified) quote verification · [D6](archive/DECISIONS-full.md#d6-fuzzy-dedupe-by-one-llm-grouping-pass-not-embeddings) LLM grouping dedupe · [D30](archive/DECISIONS-full.md#d30-grouping-contract-checked-by-code-violations-fed-back-once-then-sanitised) grouping contract · [D31](archive/DECISIONS-full.md#d31-extraction-scope-mirrors-the-gold-scope-everything-else-is-left-to-s12) extraction scope mirrors gold

**Drafting:** [D4](archive/DECISIONS-full.md#d4-chunk-id-citations-instead-of-retrieval-based-grounding) chunk-ID citations · [D7](archive/DECISIONS-full.md#d7-hierarchical-summarisation-for-the-problem-statement-no-boilerplate-removal) hierarchical problem statement · [D28](archive/DECISIONS-full.md#d28-problem-statement-code-owned-chunk-ids-in-stage-one-schema-validated-citations-in-stage-two) problem-statement citations · [D32](archive/DECISIONS-full.md#d32-solution-coverage-computed-by-code-revised-in-a-capped-langgraph-loop) coverage loop · [D33](archive/DECISIONS-full.md#d33-risks-findings-computed-by-code-must-address-checked-in-the-schema-one-call) risks from code findings · [D40](archive/DECISIONS-full.md#d40-no-critic-or-free-revision-loop-the-evals-show-prompt-shaped-faults-and-the-one-revision-loop-with-a-code-computed-target-already-exists) no critic

**Evaluation and observability:** [D11](archive/DECISIONS-full.md#d11-observability-langfuse-cloud-plus-a-local-json-run-log) Langfuse plus JSON run log · [D23](archive/DECISIONS-full.md#d23-gold-labels-core-only-scope-claude-drafts-agent-corrects-diff-is-the-record) gold labels · [D36](archive/DECISIONS-full.md#d36-evals-code-first-judge-second-recall-against-gold-precision-judged-per-item) code-first matching · [D37](archive/DECISIONS-full.md#d37-grounding-code-heuristics-plus-a-judge-that-sees-only-what-is-cited) cited-text grounding judge · [D39](archive/DECISIONS-full.md#d39-ablations-hierarchy-and-chunking-are-kept-for-scale-and-traceability-not-for-quality-the-evals-can-see) ablations

**Human in the loop:** [D43](archive/DECISIONS-full.md#d43-human-in-the-loop-as-a-pursuit-lead-would-use-it-one-checkpoint-before-drafting-one-sign-off-after-instruction-driven-refinement-between) checkpoint and sign-off · [D44](archive/DECISIONS-full.md#d44-pause-and-resume-through-the-run-directory-not-a-langgraph-checkpointer-d1-extended) pause via the run directory · [D45](archive/DECISIONS-full.md#d45-the-pursuit-brief-is-citable-evidence-row-actions-are-deterministic-the-reviewer-is-a-name) brief as evidence · [D46](archive/DECISIONS-full.md#d46-revision-by-instruction-a-patch-for-requirements-the-whole-artefact-for-the-rest-the-producing-stages-validators-either-way) revision by instruction · [D47](archive/DECISIONS-full.md#d47-versions-stale-flags-and-sign-off-live-in-the-run-directory-assembly-always-re-runs-llm-stages-never-do-on-their-own) versions and stale flags · [D48](archive/DECISIONS-full.md#d48-the-backend-runs-every-human-loop-step-as-a-job-on-the-one-worker-state-is-read-from-the-run-directory) jobs on one worker · [D49](archive/DECISIONS-full.md#d49-the-checkpoint-is-a-tab-on-the-run-page-the-draft-lives-in-the-browser-until-confirmed-the-brief-is-previewed-as-the-server-will-split-it) checkpoint tab · [D50](archive/DECISIONS-full.md#d50-refine-controls-sit-on-each-artefact-tab-the-review-tab-holds-sign-off-and-history-diffs-are-the-stored-ones-old-versions-are-read-only) refine controls

**UI, prompts, delivery:** [D35](archive/DECISIONS-full.md#d35-ui-backend-a-thin-fastapi-layer-over-run_pipeline-one-worker-events-through-a-condition-variable) FastAPI backend · [D38](archive/DECISIONS-full.md#d38-ui-frontend-views-built-from-per-stage-artifacts-source-reveal-in-a-slide-over-the-browsers-pdf-viewer) frontend · [D41](archive/DECISIONS-full.md#d41-one-docker-image-for-the-ui-and-the-cli-keys-from-the-hosts-env) Docker image · [D51](archive/DECISIONS-full.md#d51-one-prompt-structure-for-every-prompt-st13) one prompt structure · [D52](archive/DECISIONS-full.md#d52-removing-a-run-deletes-its-directory-samples-and-busy-runs-are-refused) removing runs

**Failure modes hit:** [F1](archive/DECISIONS-full.md#f1-deepseek-thinking-mode-rejects-forced-tool-choice) thinking rejects forced tool choice · [F2](archive/DECISIONS-full.md#f2-mangled-plain-text-urls-duplicated-real-links) mangled URLs · [F3](archive/DECISIONS-full.md#f3-running-header-survived-on-three-federal-way-pages) surviving running header · [F4](archive/DECISIONS-full.md#f4-judge-returned-3-checklist-facts-instead-of-8-to-12) judge fact count · [F5](archive/DECISIONS-full.md#f5-nyesd-requirements-draft-truncated-at-16000-output-tokens) gold draft truncated · [F6](archive/DECISIONS-full.md#f6-synthesis-claims-spoke-of-the-evidence-instead-of-the-rfp) "the evidence" in claims · [F7](archive/DECISIONS-full.md#f7-citation-validator-retry-with-no-recorded-cause) retry with no cause · [F8](archive/DECISIONS-full.md#f8-extractor-reported-other-sections-of-the-same-rfp-as-ambiguities-and-gaps) other chunks reported as gaps · [F9](archive/DECISIONS-full.md#f9-nyesd-gaps-listed-every-form-twice-by-name-and-by-url) forms listed twice · [F10](archive/DECISIONS-full.md#f10-solution-assumptions-cited-ambiguity-and-gap-ids-as-chunk-ids) assumptions cited wrong IDs · [F11](archive/DECISIONS-full.md#f11-deepseek-returned-no-tool-call-on-a-revision-turn) no tool call on revision · [F12](archive/DECISIONS-full.md#f12-risk-count-ran-over-the-asked-range-on-every-rfp) risk count over range · [F13](archive/DECISIONS-full.md#f13-judge-output-truncated-by-the-token-cap) judge truncated · [F14](archive/DECISIONS-full.md#f14-judge-tier-gold-matches-accept-a-missing-key-value) lenient judge matches · [F15](archive/DECISIONS-full.md#f15-vites-dev-transform-dropped-an-exported-function-named-displayname) Vite dropped a function · [F16](archive/DECISIONS-full.md#f16-single-call-extraction-truncated-at-the-providers-default-output-cap) single call truncated · [F17](archive/DECISIONS-full.md#f17-grounding-judge-runs-away-inside-a-reason-string) judge runaway (open)
</details>
