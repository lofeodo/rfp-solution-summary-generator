# REPOSITORY.md — where things live

```
src/rfp_agent/   the pipeline: parsing, splitting, agents, render, graph, CLI
prompts/         one markdown prompt per agent (structure in prompts/README.md)
ui/              FastAPI backend and React frontend
evals/gold/      reference labels for the four RFPs, with the drafts they came from
evals/harness/   the scoring harness (see EVALUATION.md)
evals/results/   committed eval reports, one folder per run label
data/rfps/       the four public RFPs
runs/samples/    four complete sample runs (no key needed to browse)
tests/           pytest suite; nothing in it calls a paid API by default
docs/            design, usage, evaluation and build history
Dockerfile       one image for the UI and the CLI
```
