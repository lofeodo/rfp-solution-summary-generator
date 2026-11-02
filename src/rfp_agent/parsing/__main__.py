"""Debug entry point: ``python -m rfp_agent.parsing <pdf> [--out parsed.json]``.

Prints a summary to stderr and the ``ParsedDocument`` JSON to stdout or ``--out``.
The pipeline CLI (S10) is separate; this exists to inspect parsing on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rfp_agent.observability import RunRecorder
from rfp_agent.parsing import parse_pdf
from rfp_agent.schemas import ParsedDocument


def main(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF to parse")],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
    judge: Annotated[
        bool,
        typer.Option("--judge", help="Run the S4 parse-quality judge on flagged pages (paid)"),
    ] = False,
) -> None:
    doc = parse_pdf(pdf)
    console = Console(stderr=True)
    if judge:
        doc = _judge(doc, console)
    console.print(
        f"[bold]{doc.title or pdf.name}[/bold]: {doc.page_count} pages, "
        f"{sum(p.word_count for p in doc.pages)} words, {len(doc.tables)} tables, "
        f"{len(doc.images)} images, {len(doc.outline)} outline entries"
    )
    flags = Table("page", "flag", "detail", title="Flags")
    for f in doc.flags:
        flags.add_row(str(f.page), f.reason.value, f.detail or "")
    console.print(flags)
    refs = Table("page", "kind", "name", "present", "section", title="Referenced documents")
    for r in doc.referenced_documents:
        refs.add_row(str(r.page), r.kind.value, r.url or r.name, str(r.present), r.section or "")
    console.print(refs)

    payload = doc.model_dump_json(indent=2)
    if out:
        out.write_text(payload, encoding="utf-8")
        console.print(f"wrote {out}")
    else:
        sys.stdout.write(payload + "\n")


def _judge(doc: ParsedDocument, console: Console) -> ParsedDocument:
    """Run the quality pass and print one row per judged page. Flags printed afterwards
    are the surviving ones."""
    from rfp_agent.parsing.quality import run_quality_pass

    rec = RunRecorder.from_settings(doc.source_path)
    with rec.activate(write=False):
        doc, report = run_quality_pass(doc)
    table = Table("page", "kind", "usable", "missing", "confirmed", "trigger", "action")
    for esc in report.escalations:
        j = report.judgements.get(esc.page)
        table.add_row(
            str(esc.page),
            j.page_kind.value if j else "?",
            str(j.text_usable) if j else "?",
            str(j.content_missing) if j else "?",
            ", ".join(f.value for f in j.confirmed_flags) if j else "?",
            esc.triggered_by.value if esc.confirmed_bad else "-",
            esc.action,
        )
    console.print(table)
    t = rec.totals()
    console.print(
        f"judge: {len(report.judged_pages)} calls, {t.input_tokens} in / {t.output_tokens} out "
        f"tokens, ${t.cost_usd:.5f}, {t.latency_s:.1f} s, {t.retries} retries"
    )
    return doc


if __name__ == "__main__":
    typer.run(main)
