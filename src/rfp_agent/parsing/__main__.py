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

from rfp_agent.parsing import parse_pdf


def main(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF to parse")],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
) -> None:
    doc = parse_pdf(pdf)
    console = Console(stderr=True)
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


if __name__ == "__main__":
    typer.run(main)
