"""Debug entry point: ``python -m rfp_agent.splitting <pdf> [--out split.json]``.

Prints the section tree to stderr and the ``SplitDocument`` JSON to stdout or ``--out``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rfp_agent.parsing import parse_pdf
from rfp_agent.parsing.heuristics import count_words
from rfp_agent.splitting import split_document


def main(
    pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="RFP PDF to split")],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Write JSON here")] = None,
) -> None:
    split = split_document(parse_pdf(pdf))
    console = Console(stderr=True)
    chunks = split.chunks()
    console.print(
        f"[bold]{pdf.name}[/bold]: {len(split.sections)} sections, {len(chunks)} chunks, "
        f"max {max((count_words(c.text) for c in chunks), default=0)} words per chunk"
    )
    tree = Table("id", "pages", "kind", "chunks", "words", "title")
    for s in split.sections:
        words = sum(count_words(c.text) for c in s.chunks)
        pages = f"{s.page_start}-{s.page_end}" if s.page_end != s.page_start else str(s.page_start)
        tree.add_row(
            s.id, pages, s.kind.value[:3], str(len(s.chunks)), str(words),
            "  " * (s.level - 1) + s.title,
        )  # fmt: skip
    console.print(tree)

    payload = split.model_dump_json(indent=2)
    if out:
        out.write_text(payload, encoding="utf-8")
        console.print(f"wrote {out}")
    else:
        sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    typer.run(main)
