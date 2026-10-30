"""Debug entry points for the agents: ``python -m rfp_agent.agents <agent> <pdf> ...``.

Each command parses and splits the PDF, runs one agent under a non-writing run recorder,
prints per-node tokens, cost, latency and retries, then the agent's output. Paid: these
call the configured generator.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rfp_agent.observability import RunRecorder

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console(stderr=True)


@app.callback()
def root(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Log every failed attempt and its feedback")
    ] = False,
) -> None:
    """Run one agent on a PDF and print what it produced and what it cost."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("httpx").setLevel(logging.WARNING)


def print_metrics(recorder: RunRecorder) -> None:
    table = Table("node", "calls", "in", "out", "cost $", "latency s", "retries")
    counts: dict[str, int] = {}
    for n in recorder.log.nodes:
        counts[n.node] = counts.get(n.node, 0) + 1
    for node, t in recorder.per_node().items():
        table.add_row(
            node,
            str(counts[node]),
            str(t.input_tokens),
            str(t.output_tokens),
            f"{t.cost_usd:.4f}",
            f"{t.latency_s:.1f}",
            str(t.retries),
        )
    console.print(table)


@app.command()
def problem(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF")],
    full_text: Annotated[
        bool, typer.Option("--full-text", help="One full-text call instead of two stages")
    ] = False,
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
) -> None:
    """Problem statement (S6): per-chunk summaries then synthesis, or one full-text call."""
    from rfp_agent.agents.problem import CLAIM_LISTS, build_problem_statement
    from rfp_agent.parsing import parse_pdf
    from rfp_agent.splitting import split_document

    parsed = parse_pdf(pdf)
    split = split_document(parsed)
    recorder = RunRecorder.from_settings(pdf)
    with recorder.activate(write=False):
        result = build_problem_statement(
            split, title=parsed.title or pdf.name, recorder=recorder, full_text=full_text
        )

    relevant = sum(s.relevant for s in result.chunk_summaries)
    failed = sum(s.error is not None for s in result.chunk_summaries)
    console.print(
        f"[bold]{pdf.name}[/bold] ({result.mode}): {len(split.chunks())} chunks, "
        f"{relevant} relevant, {failed} failed"
    )
    print_metrics(recorder)
    for name in CLAIM_LISTS:
        console.print(f"\n[bold]{name}[/bold]")
        for claim in getattr(result.statement, name):
            mark = "" if claim.kind == "fact" else " [italic](inference)[/italic]"
            console.print(f"- {claim.text} [{', '.join(claim.chunk_ids)}]{mark}")

    if out:
        out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\nwrote {out}")


if __name__ == "__main__":
    app()
