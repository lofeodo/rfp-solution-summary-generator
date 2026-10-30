"""Debug entry point: ``python -m rfp_agent.agents.requirements <pdf> [--single-call]
[--out requirements.json] [--concurrency N]``.

Parses and splits the PDF, runs the extractor under a non-writing recorder, prints the
requirements table, ambiguities, gaps, the report and the run totals to stderr, and the
``RequirementsOutput`` JSON to stdout or ``--out``. The pipeline CLI (S10) is separate.
"""

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rfp_agent.agents.requirements import extract_requirements
from rfp_agent.config import get_settings
from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.splitting import split_document


def run(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF")],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
    single_call: Annotated[
        bool, typer.Option("--single-call", help="One call over the whole document")
    ] = False,
    concurrency: Annotated[
        int | None, typer.Option("--concurrency", help="Parallel chunk calls")
    ] = None,
) -> None:
    settings = get_settings()
    if concurrency is not None:
        settings = settings.model_copy(update={"extract_concurrency": concurrency})
    parsed = parse_pdf(pdf)
    split = split_document(parsed)
    console = Console(stderr=True)
    recorder = RunRecorder.from_settings(pdf, settings)
    with recorder.activate(write=False):
        output, report = extract_requirements(
            split, title=parsed.title, settings=settings, single_call=single_call
        )
    table = Table("id", "strict", "type", "ok", "chunks", "text", title="Requirements")
    for r in output.requirements:
        lineage = f" <{','.join(r.merged_from)}" if r.merged_from else ""
        conflicts = f" !{','.join(r.conflicts_with)}" if r.conflicts_with else ""
        table.add_row(
            r.id,
            r.strictness.value[:4],
            r.type.value,
            "" if r.quote_verified else "[red]no[/red]",
            ",".join(r.chunk_ids) + lineage + conflicts,
            r.text,
        )
    console.print(table)
    for a in output.ambiguities:
        refs = ", ".join(a.requirement_ids) or "-"
        console.print(f"[yellow]{a.id}[/yellow] ({refs}) {a.description}")
    for g in output.gaps:
        console.print(f"[magenta]{g.id}[/magenta] [{g.referenced_document or '-'}] {g.description}")
    t = recorder.totals()
    console.print(
        f"\n{report}\n"
        f"calls: {len(recorder.log.nodes)}  tokens in/out: {t.input_tokens}/{t.output_tokens} "
        f"(cached {t.cached_input_tokens})  cost: ${t.cost_usd:.4f}  "
        f"latency: {t.latency_s:.1f} s summed, retries: {t.retries}"
    )
    payload = output.model_dump_json(indent=2)
    if out:
        out.write_text(payload, encoding="utf-8")
        console.print(f"wrote {out}")
    else:
        sys.stdout.write(payload + "\n")


def main() -> None:
    typer.run(run)


if __name__ == "__main__":
    main()
