"""Top-level CLI: ``python -m rfp_agent run <pdf> [flags]`` runs the whole pipeline.

Prints one line per stage as it starts and finishes (wall time, LLM calls, cost), then
the per-node metrics table, the run totals and where the outputs went. Paid: this calls
the configured generator. Per-agent debug commands live in ``rfp_agent.agents``.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rfp_agent.observability import per_node_totals
from rfp_agent.schemas import RunLog, StageStatus

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console(stderr=True)
_print_lock = threading.Lock()


@app.callback()
def root(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Log every failed attempt and its feedback")
    ] = False,
) -> None:
    """RFP solution-summary generator."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("httpx").setLevel(logging.WARNING)


def print_metrics(log: RunLog) -> None:
    """Per-node table: calls, tokens, cost, summed call latency and retries."""
    table = Table("node", "calls", "in", "out", "cached", "cost $", "latency s", "retries")
    counts: dict[str, int] = {}
    for n in log.nodes:
        counts[n.node] = counts.get(n.node, 0) + 1
    for node, t in per_node_totals(log).items():
        table.add_row(
            node,
            str(counts[node]),
            str(t.input_tokens),
            str(t.output_tokens),
            str(t.cached_input_tokens),
            f"{t.cost_usd:.4f}",
            f"{t.latency_s:.1f}",
            str(t.retries),
        )
    console.print(table)


def print_stages(log: RunLog) -> None:
    """Per-stage table: outcome, wall time, LLM calls and cost."""
    from rfp_agent.graph import stage_totals

    table = Table("stage", "status", "wall s", "calls", "cost $")
    for s in log.stages:
        calls, totals = stage_totals(log, s.stage)
        status = s.status.value
        if s.status == StageStatus.FAILED:
            status = f"[red]{status}[/red]"
        table.add_row(s.stage, status, f"{s.latency_s:.1f}", str(calls), f"{totals.cost_usd:.4f}")
    console.print(table)


def print_totals(log: RunLog) -> None:
    t = log.totals()
    wall = (log.finished_at - log.started_at).total_seconds() if log.finished_at else 0.0
    console.print(
        f"[bold]total[/bold]: {len(log.nodes)} calls, {t.input_tokens} in / {t.output_tokens} "
        f"out tokens ({t.cached_input_tokens} cached), ${t.cost_usd:.4f}, {t.retries} "
        f"retries, {wall:.0f} s wall"
    )


@app.command()
def run(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF")],
    full_text_problem: Annotated[
        bool,
        typer.Option(
            "--full-text-problem",
            help="Ablation: problem statement from one full-text call instead of per-chunk "
            "summaries and a synthesis",
        ),
    ] = False,
    single_call_extraction: Annotated[
        bool,
        typer.Option(
            "--single-call-extraction",
            help="Ablation: extract requirements in one call over the whole document "
            "instead of one call per chunk plus a dedupe pass",
        ),
    ] = False,
    max_iterations: Annotated[
        int | None,
        typer.Option(
            "--max-iterations", min=1, help="Solution rounds (RFP_SOLUTION_MAX_ITERATIONS)"
        ),
    ] = None,
    model: Annotated[
        str | None, typer.Option("--model", help="Generator, <provider>:<model_id> (RFP_MODEL)")
    ] = None,
    runs_dir: Annotated[
        Path | None, typer.Option("--runs-dir", help="Parent of the run directory (default runs/)")
    ] = None,
    run_id: Annotated[
        str | None, typer.Option("--run-id", help="Run directory name (default: timestamp + hex)")
    ] = None,
) -> None:
    """Run the pipeline on one PDF: parse, judge flagged pages, split, extract
    requirements and build the problem statement in parallel, generate the solution,
    assess risks, assemble and render. Writes runs/<run_id>/{summary.json, summary.md,
    run_log.json} plus every intermediate."""
    from rfp_agent.graph import PipelineError, StageEvent, run_pipeline
    from rfp_agent.llm import MissingApiKeyError

    def on_event(e: StageEvent) -> None:
        with _print_lock:
            if e.status == StageStatus.STARTED:
                console.print(f"[dim]{e.stage}: started[/dim]")
            elif e.status == StageStatus.FINISHED:
                calls = f", {e.calls} calls, ${e.totals.cost_usd:.4f}" if e.calls else ""
                console.print(f"[green]{e.stage}[/green]: finished in {e.latency_s:.1f} s{calls}")
            else:
                console.print(f"[red]{e.stage}[/red]: failed after {e.latency_s:.1f} s: {e.error}")

    try:
        result = run_pipeline(
            pdf,
            runs_dir=runs_dir,
            run_id=run_id,
            model_spec=model,
            full_text_problem=full_text_problem or None,
            single_call_extraction=single_call_extraction or None,
            max_iterations=max_iterations,
            on_event=on_event,
        )
    except MissingApiKeyError as exc:
        console.print(f"[red]error[/red]: {exc}")
        raise typer.Exit(2) from exc
    except PipelineError as exc:
        print_stages(exc.run_log)
        print_metrics(exc.run_log)
        print_totals(exc.run_log)
        console.print(
            f"[red]run {exc.run_log.run_id} failed[/red] in stage {exc.stage}: {exc.cause}"
        )
        console.print(f"run log and intermediates kept in {exc.run_dir}", soft_wrap=True)
        raise typer.Exit(1) from exc

    log = result.run_log
    print_stages(log)
    print_metrics(log)
    print_totals(log)
    summary = result.summary
    console.print(
        f"[bold]{pdf.name}[/bold]: {len(summary.requirements.requirements)} requirements, "
        f"{len(summary.solution.components)} components, {len(summary.risks.risks)} risks; "
        f"coverage {summary.solution.coverage.mandatory_covered}/"
        f"{summary.solution.coverage.mandatory_total} mandatory"
    )
    # soft_wrap: never break a path across lines, whatever the terminal width.
    for name in ("summary.json", "summary.md"):
        console.print(f"  {result.output_paths[name]}", soft_wrap=True)
    console.print(f"  {result.run_dir / 'run_log.json'}", soft_wrap=True)
    if log.langfuse_trace_url:
        console.print(f"  trace: {log.langfuse_trace_url}", soft_wrap=True)
