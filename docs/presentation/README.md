# Presentation pages

Support material for walking an interviewer through the three harnesses. Each page opens with its one-line message and key numbers, then one section per talking point. Detail sits in collapsed blocks at the bottom for questions.

| Order | Page | One line |
|---|---|---|
| 1 | [Traceability](TRACEABILITY.md) | Every claim points at a numbered paragraph of the RFP; code guarantees the pointer exists |
| 2 | [Evaluation](EVALUATION-HARNESS.md) | Code scores first, a judge from another model family scores the rest, and the judge is checked |
| 3 | [Observability](OBSERVABILITY.md) | Every LLM call is recorded with cost, latency and the cause of any retry, in a JSON file the UI and evals read |

Traceability comes first because the other two rest on it: the evals count unsupported claims *because* claims carry IDs, and the observability log records the retries the citation validators trigger.

**Colour key in the diagrams:** black boxes are code (deterministic, free), orange boxes are a language model.

Written for Obsidian. Detail sections are folded callouts (`> [!note]- Title`; click to open). Diagrams are Mermaid, which Obsidian renders natively. Dollar signs are escaped (`\$`) so Obsidian does not read them as maths. On GitHub the diagrams and tables also render, but the folded callouts show as plain quote blocks with a visible `[!note]-` marker.
