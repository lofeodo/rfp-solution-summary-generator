"""Write the summary JSON and its rendered markdown side by side (S10 picks the folder)."""

from __future__ import annotations

from pathlib import Path

from rfp_agent.render.markdown import render_markdown
from rfp_agent.schemas import SolutionSummary

JSON_NAME = "summary.json"
MARKDOWN_NAME = "summary.md"


def write_summary(summary: SolutionSummary, out_dir: Path) -> tuple[Path, Path]:
    """Write ``summary.json`` and ``summary.md`` into ``out_dir``; return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / JSON_NAME
    md_path = out_dir / MARKDOWN_NAME
    json_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    return json_path, md_path
