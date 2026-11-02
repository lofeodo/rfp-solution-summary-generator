"""Top-level CLI.

``python -m rfp_agent run <pdf> [flags]`` reads the RFP and stops at the checkpoint
(ST12); ``python -m rfp_agent checkpoint <run_id> --reviewer NAME [...]`` confirms the
requirements, records the pursuit brief and drafts the rest; ``run --unattended`` does
everything in one go, as before ST12.

Prints one line per stage as it starts and finishes (wall time, LLM calls, cost), then
the per-node metrics table, the run totals and where the outputs went. Paid: this calls
the configured generator. Per-agent debug commands live in ``rfp_agent.agents``.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
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
    # A paused run has no finished_at: its wall time so far is "until now".
    end = log.finished_at or datetime.now(UTC)
    wall = (end - log.started_at).total_seconds()
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
    unattended: Annotated[
        bool,
        typer.Option(
            "--unattended",
            help="Do not stop at the checkpoint: draft the solution and the risks right "
            "after the requirements, with no human confirmation and no pursuit brief",
        ),
    ] = False,
) -> None:
    """Read one RFP and stop at the checkpoint: parse, judge flagged pages, split,
    extract requirements and build the problem statement in parallel, then wait for
    `checkpoint`. With --unattended, go on to generate the solution, assess risks,
    assemble and render. Writes runs/<run_id>/ with every intermediate, and with
    summary.json, summary.md and run_log.json once drafted."""
    from rfp_agent.graph import PipelineError, run_pipeline
    from rfp_agent.llm import MissingApiKeyError

    try:
        result = run_pipeline(
            pdf,
            runs_dir=runs_dir,
            run_id=run_id,
            model_spec=model,
            full_text_problem=full_text_problem or None,
            single_call_extraction=single_call_extraction or None,
            max_iterations=max_iterations,
            on_event=_print_event,
            pause_at_checkpoint=not unattended,
        )
    except MissingApiKeyError as exc:
        console.print(f"[red]error[/red]: {exc}")
        raise typer.Exit(2) from exc
    except PipelineError as exc:
        _report_failure(exc)
        raise typer.Exit(1) from exc
    _report(result, pdf.name)


@app.command()
def checkpoint(
    run_id: Annotated[
        str, typer.Argument(help="Run directory name of a run waiting at the checkpoint")
    ],
    reviewer: Annotated[
        str, typer.Option("--reviewer", help="Who confirms the requirements (recorded)")
    ],
    brief: Annotated[
        Path | None,
        typer.Option(
            "--brief",
            exists=True,
            dir_okay=False,
            help="Pursuit brief (text or markdown): win themes, capabilities, constraints, "
            "client context, things to avoid. Each paragraph becomes a citable chunk H1, H2...",
        ),
    ] = None,
    reject: Annotated[
        list[str] | None,
        typer.Option("--reject", help="Requirement ID to drop; repeatable"),
    ] = None,
    strictness: Annotated[
        list[str] | None,
        typer.Option(
            "--strictness", help="ID=mandatory|desired|optional to change a strictness; repeatable"
        ),
    ] = None,
    type_: Annotated[
        list[str] | None,
        typer.Option("--type", help="ID=<requirement type> to change a type; repeatable"),
    ] = None,
    note: Annotated[
        str | None, typer.Option("--note", help="Free-text note for the record")
    ] = None,
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
) -> None:
    """Confirm the checkpoint of a paused run and draft the rest: apply the decisions
    (reject, change strictness or type), record the reviewer and the pursuit brief,
    then generate the solution, assess risks, assemble and render on the same run."""
    from rfp_agent.brief import parse_brief
    from rfp_agent.checkpoint import CheckpointError
    from rfp_agent.config import RUNS_DIR
    from rfp_agent.graph import PipelineError, PipelineStateError, resume_pipeline
    from rfp_agent.llm import MissingApiKeyError
    from rfp_agent.schemas import (
        CheckpointRecord,
        DecisionAction,
        RequirementDecision,
        RequirementType,
        Strictness,
    )

    decisions: dict[str, RequirementDecision] = {}

    def decision(rid: str) -> RequirementDecision:
        return decisions.setdefault(rid, RequirementDecision(requirement_id=rid))

    def parse_assignment(item: str, flag: str) -> tuple[str, str]:
        rid, sep, value = item.partition("=")
        if not sep or not rid.strip() or not value.strip():
            raise typer.BadParameter(f"{flag} takes ID=value, got {item!r}")
        return rid.strip(), value.strip().lower()

    try:
        for rid in reject or []:
            decisions[rid] = RequirementDecision(requirement_id=rid, action=DecisionAction.REJECT)
        for item in strictness or []:
            rid, value = parse_assignment(item, "--strictness")
            try:
                level = Strictness(value)
            except ValueError as exc:
                allowed = ", ".join(s.value for s in Strictness)
                raise typer.BadParameter(
                    f"--strictness {rid}: {value!r} is not one of {allowed}"
                ) from exc
            decisions[rid] = decision(rid).model_copy(update={"strictness": level})
        for item in type_ or []:
            rid, value = parse_assignment(item, "--type")
            try:
                kind = RequirementType(value)
            except ValueError as exc:
                allowed = ", ".join(t.value for t in RequirementType)
                raise typer.BadParameter(
                    f"--type {rid}: {value!r} is not one of {allowed}"
                ) from exc
            decisions[rid] = decision(rid).model_copy(update={"type": kind})
        record = CheckpointRecord(
            reviewer=reviewer,
            confirmed_at=datetime.now(UTC),
            decisions=list(decisions.values()),
            brief=parse_brief(brief.read_text(encoding="utf-8")) if brief is not None else None,
            note=note,
        )
    except ValueError as exc:  # pydantic: a malformed ID or an empty reviewer
        raise typer.BadParameter(str(exc)) from exc

    run_dir = (runs_dir or RUNS_DIR) / run_id
    try:
        result = resume_pipeline(
            run_dir,
            record,
            model_spec=model,
            max_iterations=max_iterations,
            on_event=_print_event,
        )
    except (MissingApiKeyError, PipelineStateError, CheckpointError) as exc:
        console.print(f"[red]error[/red]: {exc}")
        raise typer.Exit(2) from exc
    except PipelineError as exc:
        _report_failure(exc)
        raise typer.Exit(1) from exc
    _report(result, Path(result.run_log.source_path).name)


# --------------------------------------------------------------------------------------
# Refinement (ST12b): revise, regenerate, sign off, history
# --------------------------------------------------------------------------------------

RunsDirOption = Annotated[
    Path | None, typer.Option("--runs-dir", help="Parent of the run directory (default runs/)")
]
ReviewerOption = Annotated[str, typer.Option("--reviewer", help="Who asks for it (recorded)")]
ModelOption = Annotated[
    str | None, typer.Option("--model", help="Generator, <provider>:<model_id> (RFP_MODEL)")
]


def _run_dir(runs_dir: Path | None, run_id: str) -> Path:
    from rfp_agent.config import RUNS_DIR

    return (runs_dir or RUNS_DIR) / run_id


def _print_diff(diff, limit: int = 40) -> None:
    """``+`` added, ``-`` removed, ``~`` changed paths of a revision's diff."""
    if diff is None:
        return
    if diff.empty:
        console.print("no change")
        return
    lines = [f"[green]+ {p}[/green]" for p in diff.added]
    lines += [f"[red]- {p}[/red]" for p in diff.removed]
    lines += [f"[yellow]~ {c.path}[/yellow]" for c in diff.changed]
    for line in lines[:limit]:
        console.print(line, soft_wrap=True, markup=True, highlight=False)
    if len(lines) > limit:
        console.print(f"... and {len(lines) - limit} more (see revisions.json)")


def _report_refine(result) -> None:
    """The diff, the version change, what went stale, cost, then the summary paths."""
    r = result.record
    _print_diff(r.diff)
    if r.artefact is not None and r.to_version is not None:
        console.print(f"{r.artefact.value} v{r.from_version} -> v{r.to_version}")
    stale = [(a.value, v.stale_because) for a, v in result.versions.artefacts.items() if v.stale]
    if stale:
        console.print(
            "[yellow]stale[/yellow]: " + "; ".join(f"{a} ({why})" for a, why in stale),
            soft_wrap=True,
        )
    console.print(f"{r.id}: {r.calls} calls, ${r.cost_usd:.4f}, {r.latency_s:.1f} s")
    print_totals(result.run_log)
    if result.summary is not None and result.output_paths:
        for name in ("summary.json", "summary.md"):
            if name in result.output_paths:
                console.print(f"  {result.output_paths[name]}", soft_wrap=True)
    elif result.summary is None:
        console.print("the run is still waiting at the checkpoint; nothing was re-assembled")


@app.command()
def revise(
    run_id: Annotated[str, typer.Argument(help="Run directory name")],
    artefact: Annotated[
        str, typer.Argument(help="What to revise: requirements, problem, solution or risks")
    ],
    reviewer: ReviewerOption,
    instruction: Annotated[
        str | None, typer.Option("--instruction", help="What to change, in plain words")
    ] = None,
    instruction_file: Annotated[
        Path | None,
        typer.Option(
            "--instruction-file", exists=True, dir_okay=False, help="The instruction from a file"
        ),
    ] = None,
    model: ModelOption = None,
    runs_dir: RunsDirOption = None,
) -> None:
    """Apply one instruction to one artefact: the model revises it, code re-validates it
    with the producing stage's checks, the change is versioned with a diff, what depends
    on it is marked stale, and the summary is re-assembled. Requirements and the problem
    statement can be revised while the run waits at the checkpoint."""
    from rfp_agent.graph import PipelineStateError
    from rfp_agent.llm import MissingApiKeyError
    from rfp_agent.refine import RefineError, RevisionFailed
    from rfp_agent.refine import revise as do_revise
    from rfp_agent.schemas import Artefact

    try:
        kind = Artefact(artefact.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(a.value for a in Artefact)
        raise typer.BadParameter(f"artefact must be one of {allowed}, not {artefact!r}") from exc
    if (instruction is None) == (instruction_file is None):
        raise typer.BadParameter("give exactly one of --instruction or --instruction-file")
    text = instruction if instruction is not None else instruction_file.read_text(encoding="utf-8")
    try:
        result = do_revise(
            _run_dir(runs_dir, run_id),
            kind,
            reviewer=reviewer,
            instruction=text,
            model_spec=model,
            on_event=_print_event,
        )
    except (MissingApiKeyError, PipelineStateError, RefineError) as exc:
        console.print(f"[red]error[/red]: {exc}")
        raise typer.Exit(2) from exc
    except RevisionFailed as exc:
        print_totals(exc.run_log)
        console.print(f"[red]{exc.record.id} failed[/red]: {exc.record.error}", soft_wrap=True)
        console.print(f"{kind.value} unchanged; the failure is in revisions.json")
        raise typer.Exit(1) from exc
    _report_refine(result)


@app.command()
def regenerate(
    run_id: Annotated[str, typer.Argument(help="Run directory name")],
    stage: Annotated[str, typer.Argument(help="The stage to re-run: solution or risk")],
    reviewer: ReviewerOption,
    max_iterations: Annotated[
        int | None,
        typer.Option(
            "--max-iterations", min=1, help="Solution rounds (RFP_SOLUTION_MAX_ITERATIONS)"
        ),
    ] = None,
    model: ModelOption = None,
    runs_dir: RunsDirOption = None,
) -> None:
    """Re-run the solution or the risk stage alone on the current inputs (after an
    upstream change made it stale) and make its output the next version. Never cascades:
    regenerating the solution leaves the risks stale until you regenerate or revise them."""
    from rfp_agent.graph import PipelineError, PipelineStateError
    from rfp_agent.llm import MissingApiKeyError
    from rfp_agent.refine import RefineError
    from rfp_agent.refine import regenerate as do_regenerate

    try:
        result = do_regenerate(
            _run_dir(runs_dir, run_id),
            stage.strip().lower(),
            reviewer=reviewer,
            model_spec=model,
            max_iterations=max_iterations,
            on_event=_print_event,
        )
    except (MissingApiKeyError, PipelineStateError, RefineError) as exc:
        console.print(f"[red]error[/red]: {exc}")
        raise typer.Exit(2) from exc
    except PipelineError as exc:
        _report_failure(exc)
        raise typer.Exit(1) from exc
    _report_refine(result)


@app.command("sign-off")
def sign_off(
    run_id: Annotated[str, typer.Argument(help="Run directory name")],
    reviewer: ReviewerOption,
    note: Annotated[str | None, typer.Option("--note", help="Free-text note")] = None,
    runs_dir: RunsDirOption = None,
) -> None:
    """Freeze the run at its current versions and render the sign-off. Refused while an
    artefact is stale; nothing can be revised or regenerated afterwards."""
    from rfp_agent.graph import PipelineStateError
    from rfp_agent.refine import RefineError
    from rfp_agent.refine import sign_off as do_sign_off

    try:
        result = do_sign_off(
            _run_dir(runs_dir, run_id), reviewer=reviewer, note=note, on_event=_print_event
        )
    except (PipelineStateError, RefineError) as exc:
        console.print(f"[red]error[/red]: {exc}", soft_wrap=True)
        raise typer.Exit(2) from exc
    so = result.versions.signed_off
    versions = ", ".join(f"{a.value} v{v}" for a, v in so.versions.items())
    console.print(f"[green]signed off[/green] by {so.reviewer}: {versions}")
    for name in ("summary.json", "summary.md"):
        if result.output_paths and name in result.output_paths:
            console.print(f"  {result.output_paths[name]}", soft_wrap=True)


@app.command()
def history(
    run_id: Annotated[str, typer.Argument(help="Run directory name")],
    runs_dir: RunsDirOption = None,
) -> None:
    """The review history of a run: the checkpoint, every revision, regeneration and
    sign-off with its cost, and where each artefact stands now."""
    from rfp_agent import versions

    run_dir = _run_dir(runs_dir, run_id)
    if not (run_dir / "run_log.json").is_file():
        console.print(f"[red]error[/red]: {run_dir} has no run log", soft_wrap=True)
        raise typer.Exit(2)
    review = versions.review_history(run_dir)
    state = versions.load_version_state(run_dir)
    cp = review.checkpoint if review is not None else None
    if cp is not None:
        console.print(
            f"checkpoint: confirmed by {cp.reviewer} on {cp.confirmed_at:%Y-%m-%d %H:%M} UTC, "
            f"{len(cp.rejected_ids())} rejected, {len(cp.edited_ids())} edited, "
            f"brief {'with ' + str(len(cp.brief.chunks)) + ' chunks' if cp.brief else 'none'}"
        )
    else:
        console.print("checkpoint: none (unattended run, or still waiting)")
    revisions = review.revisions if review is not None else []
    table = Table("id", "kind", "artefact", "reviewer", "versions", "calls", "cost $", "status")
    for r in revisions:
        span = f"v{r.from_version}->v{r.to_version}" if r.to_version is not None else ""
        table.add_row(
            r.id,
            r.kind.value,
            r.artefact.value if r.artefact else "",
            r.reviewer,
            span,
            str(r.calls),
            f"{r.cost_usd:.4f}",
            r.status.value,
        )
    console.print(table)
    for r in revisions:
        if r.instruction:
            console.print(f"  {r.id}: {r.instruction.strip()}", soft_wrap=True)
    now = Table("artefact", "version", "stale")
    for a, v in state.artefacts.items():
        now.add_row(a.value, f"v{v.version}", (v.stale_because or "yes") if v.stale else "")
    console.print(now)
    if state.signed_off is not None:
        so = state.signed_off
        console.print(f"signed off by {so.reviewer} on {so.signed_at:%Y-%m-%d %H:%M} UTC")


def _print_event(e) -> None:
    with _print_lock:
        if e.status == StageStatus.STARTED:
            console.print(f"[dim]{e.stage}: started[/dim]")
        elif e.status == StageStatus.FINISHED:
            calls = f", {e.calls} calls, ${e.totals.cost_usd:.4f}" if e.calls else ""
            console.print(f"[green]{e.stage}[/green]: finished in {e.latency_s:.1f} s{calls}")
        elif e.status == StageStatus.WAITING:
            console.print(f"[yellow]{e.stage}[/yellow]: waiting for a reviewer")
        else:
            console.print(f"[red]{e.stage}[/red]: failed after {e.latency_s:.1f} s: {e.error}")


def _report_failure(exc) -> None:
    print_stages(exc.run_log)
    print_metrics(exc.run_log)
    print_totals(exc.run_log)
    console.print(f"[red]run {exc.run_log.run_id} failed[/red] in stage {exc.stage}: {exc.cause}")
    console.print(f"run log and intermediates kept in {exc.run_dir}", soft_wrap=True)


def _report(result, source_name: str) -> None:
    """Tables, totals and either the drafted summary's headline and paths, or, for a run
    paused at the checkpoint, what was read and the command that continues it."""
    log = result.run_log
    print_stages(log)
    print_metrics(log)
    print_totals(log)
    # soft_wrap: never break a path across lines, whatever the terminal width.
    if result.paused:
        reqs = result.state["requirements"]
        console.print(
            f"[bold]{source_name}[/bold]: paused at the checkpoint with "
            f"{len(reqs.requirements)} requirements, {len(reqs.ambiguities)} ambiguities, "
            f"{len(reqs.gaps)} gaps"
        )
        console.print(f"  {result.run_dir}", soft_wrap=True)
        console.print(
            "next: review requirements.json, then\n"
            f'  python -m rfp_agent checkpoint {log.run_id} --reviewer "<name>" '
            "[--brief brief.md] [--reject R003] [--strictness R005=desired] "
            "[--type R007=technical]",
            soft_wrap=True,
        )
        return
    summary = result.summary
    console.print(
        f"[bold]{source_name}[/bold]: {len(summary.requirements.requirements)} requirements, "
        f"{len(summary.solution.components)} components, {len(summary.risks.risks)} risks; "
        f"coverage {summary.solution.coverage.mandatory_covered}/"
        f"{summary.solution.coverage.mandatory_total} mandatory"
    )
    for name in ("summary.json", "summary.md"):
        console.print(f"  {result.output_paths[name]}", soft_wrap=True)
    console.print(f"  {result.run_dir / 'run_log.json'}", soft_wrap=True)
    if log.langfuse_trace_url:
        console.print(f"  trace: {log.langfuse_trace_url}", soft_wrap=True)
