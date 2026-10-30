"""``python -m evals.harness``: generate eval runs, score them, report, check the judge.

    python -m evals.harness run --label baseline --all --runs 2 --reuse-samples   # paid
    python -m evals.harness score --label baseline                                # judge, paid
    python -m evals.harness score --label baseline --no-judge                     # free
    python -m evals.harness report --label baseline
    python -m evals.harness sample --label baseline     # hand-labelling sample
    python -m evals.harness agree --label baseline      # judge vs hand labels
    python -m evals.harness compare RUN_A RUN_B --what problem --rfp missouri     # paid
    python -m evals.harness run --label ablation_full_text --all --full-text-problem
    python -m evals.harness score --label baseline --only match        # one judge, merged
    python -m evals.harness diff baseline ablation_full_text --what problem        # free

Eval runs live under ``runs/evals/<label>/<rfp>/<k>/`` (gitignored); scores, summaries,
judge logs and the agreement files under ``evals/results/<label>/`` (committed).
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from evals.gold.label import RFPS, final_path, load_gold
from evals.harness import agreement as agreement_mod
from evals.harness.load import EvalRun
from evals.harness.report import DIFF_COLUMNS, LabelSummary, render_diff, render_markdown, summarise
from evals.harness.report import diff as do_diff
from evals.harness.score import JUDGE_NODES, SECTIONS, load_scores, parse_sections, score_run

ROOT = Path(__file__).resolve().parents[2]
EVAL_RUNS = ROOT / "runs" / "evals"
SAMPLES = ROOT / "runs" / "samples"
RESULTS = ROOT / "evals" / "results"
SAMPLE_FILE = "agreement_sample.json"
LABELS_FILE = "agreement_labels.json"

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console(stderr=True)

LabelOpt = Annotated[str, typer.Option("--label", "-l", help="Results set name, e.g. baseline")]
RfpOpt = Annotated[str | None, typer.Option("--rfp", help=f"One of {', '.join(RFPS)}")]
AllOpt = Annotated[bool, typer.Option("--all", help="All four RFPs")]


@app.callback()
def root(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    """Evaluation harness (S12)."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("httpx").setLevel(logging.WARNING)


def _gold_name(rfp: str) -> str:
    """The RFP name as the gold files and eval run directories spell it, matched
    case-insensitively (Linux CI is case-sensitive, Windows is not)."""
    for name in RFPS:
        if name.lower() == rfp.lower():
            return name
    raise typer.BadParameter(f"--rfp must be one of {RFPS}")


def _rfps(rfp: str | None, all_: bool) -> list[str]:
    if all_ or rfp is None:
        return RFPS
    return [_gold_name(rfp)]


def _rel(path: Path) -> Path:
    """Relative to the working directory when possible, so run logs carry
    ``data/rfps/<rfp>.pdf`` like the committed samples."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return path


def _results(label: str) -> Path:
    return RESULTS / label


def _run_dirs(label: str, rfps: list[str]) -> list[tuple[str, Path]]:
    """``(key, dir)`` for every finished run under the label, key ``<rfp>-<k>``."""
    out = []
    for rfp in rfps:
        base = EVAL_RUNS / label / rfp
        if not base.exists():
            continue
        for d in sorted(base.iterdir(), key=lambda p: p.name):
            if (d / "summary.json").exists():
                out.append((f"{rfp}-{d.name}", d))
    return out


def _judge():
    from evals.harness.judge import Judge, build_judge_model
    from rfp_agent.llm import MissingApiKeyError

    try:
        return Judge(build_judge_model())
    except MissingApiKeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc


@app.command()
def run(
    label: LabelOpt,
    rfp: RfpOpt = None,
    all_: AllOpt = False,
    runs: Annotated[int, typer.Option("--runs", help="Fresh runs per RFP")] = 2,
    reuse_samples: Annotated[
        bool, typer.Option("--reuse-samples", help="Copy runs/samples/<rfp> in as run 1")
    ] = False,
    full_text_problem: Annotated[
        bool | None,
        typer.Option(
            "--full-text-problem/--no-full-text-problem",
            help="Problem statement from one full-text call (ablation); default: Settings",
        ),
    ] = None,
    single_call_extraction: Annotated[
        bool | None,
        typer.Option(
            "--single-call-extraction/--no-single-call-extraction",
            help="Requirements from one whole-document call (ablation); default: Settings",
        ),
    ] = None,
) -> None:
    """Run the pipeline (paid) into runs/evals/<label>/<rfp>/<k>/."""
    from rfp_agent.config import DATA_DIR
    from rfp_agent.graph import PipelineError, run_pipeline
    from rfp_agent.llm import MissingApiKeyError

    for name in _rfps(rfp, all_):
        base = EVAL_RUNS / label / name
        base.mkdir(parents=True, exist_ok=True)
        start = 1
        if reuse_samples:
            src = SAMPLES / name.lower()
            dst = base / "1"
            if not dst.exists():
                shutil.copytree(src, dst)
                console.print(f"{name}: copied {src.relative_to(ROOT).as_posix()} as run 1")
            start = 2
        existing = {d.name for d in base.iterdir() if (d / "summary.json").exists()}
        k = start
        made = 0
        while made < runs:
            if str(k) in existing:
                k += 1
                continue
            pdf = _rel(DATA_DIR / "rfps" / f"{name}.pdf")
            try:
                result = run_pipeline(
                    pdf,
                    runs_dir=base,
                    run_id=str(k),
                    full_text_problem=full_text_problem,
                    single_call_extraction=single_call_extraction,
                )
            except MissingApiKeyError as exc:
                console.print(f"[red]{exc}[/red]")
                raise typer.Exit(2) from exc
            except PipelineError as exc:
                console.print(f"[red]{name} run {k} failed in {exc.stage}: {exc}[/red]")
                raise typer.Exit(1) from exc
            t = result.run_log.totals()
            console.print(
                f"{name} run {k}: {len(result.summary.requirements.requirements)} reqs, "
                f"{len(result.summary.solution.components)} components, "
                f"{len(result.summary.risks.risks)} risks, ${t.cost_usd:.3f}"
            )
            k += 1
            made += 1


@app.command()
def score(
    label: LabelOpt,
    run_dirs: Annotated[
        list[Path] | None, typer.Argument(help="Score these run dirs instead of the label's")
    ] = None,
    rfp: RfpOpt = None,
    run_key: Annotated[str | None, typer.Option("--run", help="Only this run key, e.g. 1")] = None,
    only: Annotated[
        list[str] | None,
        typer.Option(
            "--only",
            help="Rescore only these sections (comma list or repeated): "
            + ", ".join(SECTIONS)
            + ". Merged into the existing score file and judge log.",
        ),
    ] = None,
    no_judge: Annotated[bool, typer.Option("--no-judge", help="Code metrics only (free)")] = False,
    force: Annotated[bool, typer.Option("--force", help="Rescore existing score files")] = False,
) -> None:
    """Score runs into evals/results/<label>/scores/<rfp>-<k>.json."""
    from evals.harness.judge import judge_cost_from_log, merge_judge_logs
    from rfp_agent.schemas import RunLog

    try:
        sections = parse_sections(only)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if run_dirs:
        targets = []
        for d in run_dirs:
            run_ = EvalRun.load(d)
            targets.append((f"{run_.rfp}-{d.name}", d))
    else:
        targets = _run_dirs(label, _rfps(rfp, False))
    if run_key:
        targets = [(k, d) for k, d in targets if k.rsplit("-", 1)[1] == run_key]
    if not targets:
        console.print(f"[red]no run directories found for label {label!r}[/red]")
        raise typer.Exit(1)
    out_dir = _results(label) / "scores"
    log_dir = _results(label) / "judge_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    for key, d in targets:
        out = out_dir / f"{key}.json"
        log_path = log_dir / f"{key}.json"
        previous = None
        if out.exists():
            if sections is None and not force:
                console.print(f"{key}: scored already, skipping (use --force)")
                continue
            if sections is not None and not force:
                previous = load_scores(out)
            elif sections is not None:
                console.print(
                    f"[yellow]{key}: --only with --force resets the other sections to "
                    "code-only values and replaces the judge log[/yellow]"
                )
        judge = None if no_judge else _judge()
        run_ = EvalRun.load(d)
        try:
            scores = score_run(
                run_, judge, key=key.rsplit("-", 1)[1], only=sections, previous=previous
            )
        except ValueError as exc:
            console.print(f"[red]{key}: {exc}[/red]")
            raise typer.Exit(1) from exc
        if judge is not None:
            judge.recorder.finish()
            if previous is not None and previous.judge is not None and log_path.exists():
                # One log per run holding exactly the calls behind the verdicts in the
                # score file: the kept sections' old calls plus this pass's new ones.
                old = RunLog.model_validate_json(log_path.read_text(encoding="utf-8"))
                replaced = {JUDGE_NODES[s] for s in (sections or ()) if s in JUDGE_NODES}
                merged = merge_judge_logs(old, judge.recorder.log, replaced)
                scores = scores.model_copy(
                    update={
                        "judge": judge_cost_from_log(
                            judge.spec, merged, previous.judge.failures + judge.failures
                        )
                    }
                )
                log_path.write_text(merged.model_dump_json(indent=2) + "\n", encoding="utf-8")
            else:
                judge.recorder.write(log_path)
        out.write_text(scores.model_dump_json(indent=2) + "\n", encoding="utf-8")
        r = scores.requirements
        jc = f", judge ${scores.judge.totals.cost_usd:.3f}" if scores.judge else ""
        part = f" only={','.join(sorted(sections))}" if sections else ""
        console.print(
            f"{key}: recall {r.recall:.0%} (reachable {r.recall_reachable:.0%}), "
            f"precision {'–' if r.precision is None else f'{r.precision:.0%}'}{jc}{part}"
        )


def _scores(label: str) -> list:
    d = _results(label) / "scores"
    return [load_scores(p) for p in sorted(d.glob("*.json"))] if d.exists() else []


@app.command()
def report(label: LabelOpt) -> None:
    """Write evals/results/<label>/summary.json and summary.md from the score files."""
    scores = _scores(label)
    if not scores:
        console.print(f"[red]no score files for label {label!r}[/red]")
        raise typer.Exit(1)
    labels_path = _results(label) / LABELS_FILE
    agreed = None
    if labels_path.exists():
        agreed = agreement_mod.agree(agreement_mod.read_sample(labels_path), scores)
    summary = summarise(label, scores, agreed)
    (_results(label) / "summary.json").write_text(
        summary.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    md = render_markdown(summary)
    (_results(label) / "summary.md").write_text(md, encoding="utf-8")
    typer.echo(md)


@app.command()
def sample(
    label: LabelOpt,
    run_key: Annotated[str, typer.Option("--run", help="Which run of each RFP")] = "1",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Write the hand-labelling sample (judge answers hidden)."""
    path = _results(label) / SAMPLE_FILE
    if path.exists() and not force:
        console.print(f"{path.name} exists (use --force)")
        raise typer.Exit(1)
    scores = [s for s in _scores(label) if s.run == run_key and s.judged]
    items = agreement_mod.sample(scores)
    agreement_mod.write_sample(items, path)
    console.print(
        f"wrote {len(items)} items to {path.relative_to(ROOT).as_posix()}", soft_wrap=True
    )


@app.command()
def agree(label: LabelOpt) -> None:
    """Judge vs hand labels (reads agreement_labels.json)."""
    path = _results(label) / LABELS_FILE
    if not path.exists():
        console.print(f"[red]{path.name} not found: copy {SAMPLE_FILE} and fill `human`[/red]")
        raise typer.Exit(1)
    result = agreement_mod.agree(agreement_mod.read_sample(path), _scores(label))
    typer.echo(json.dumps(result, indent=2))


@app.command()
def compare(
    a: Annotated[Path, typer.Argument(help="Run dir or problem/solution/summary JSON")],
    b: Annotated[Path, typer.Argument(help="Run dir or problem/solution/summary JSON")],
    what: Annotated[str, typer.Option("--what", help="problem or solution")] = "problem",
    rfp: Annotated[str, typer.Option("--rfp", help="Gold set for the context")] = "missouri",
    out: Annotated[Path | None, typer.Option("--out", "-o")] = None,
) -> None:
    """Pairwise judge with the order swapped (paid, two calls)."""
    from evals.harness.pairwise import compare as do_compare
    from evals.harness.pairwise import load_output

    if what not in ("problem", "solution"):
        raise typer.BadParameter("--what must be problem or solution")
    judge = _judge()
    result = do_compare(
        load_output(a, what),  # type: ignore[arg-type]
        load_output(b, what),  # type: ignore[arg-type]
        what=what,  # type: ignore[arg-type]
        gold=load_gold(final_path(_gold_name(rfp))),
        judge=judge,
        a_name=a.as_posix(),
        b_name=b.as_posix(),
    )
    text = result.model_dump_json(indent=2)
    typer.echo(text)
    console.print(f"judge cost ${judge.cost().totals.cost_usd:.4f}")
    if out:
        out.write_text(text + "\n", encoding="utf-8")


@app.command()
def diff(
    a: Annotated[str, typer.Argument(help="Baseline label")],
    b: Annotated[str, typer.Argument(help="Candidate label")],
    what: Annotated[
        str | None,
        typer.Option("--what", help="Column set: " + ", ".join(DIFF_COLUMNS) + " (default: all)"),
    ] = None,
    columns: Annotated[
        list[str] | None,
        typer.Option(
            "--columns",
            "-c",
            help="Row columns instead (comma list or repeated); dict columns as "
            "unsupported.problem or rubric.specificity",
        ),
    ] = None,
    out: Annotated[Path | None, typer.Option("--out", "-o")] = None,
) -> None:
    """Per-RFP mean ± sd of two labels' summary.json side by side, with the delta (free)."""
    summaries = []
    for label in (a, b):
        path = _results(label) / "summary.json"
        if not path.exists():
            console.print(f"[red]no summary.json for label {label!r}; run report first[/red]")
            raise typer.Exit(1)
        summaries.append(LabelSummary.model_validate_json(path.read_text(encoding="utf-8")))
    if columns:
        cols = [c.strip() for entry in columns for c in entry.split(",") if c.strip()]
    elif what is not None:
        if what not in DIFF_COLUMNS:
            raise typer.BadParameter(f"--what must be one of {', '.join(DIFF_COLUMNS)}")
        cols = DIFF_COLUMNS[what]
    else:
        cols = [c for group in DIFF_COLUMNS.values() for c in group]
    try:
        rows = do_diff(summaries[0], summaries[1], cols)
    except KeyError as exc:
        raise typer.BadParameter(f"unknown column {exc}") from exc
    md = render_diff(summaries[0], summaries[1], rows)
    typer.echo(md)
    if out:
        out.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    app()
