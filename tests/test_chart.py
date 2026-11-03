"""The before/after SVG chart reads two committed summaries and writes valid SVG (free)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from typer.testing import CliRunner

from evals.harness import __main__ as cli
from evals.harness.chart import DEFAULT_PANELS, render_svg
from evals.harness.report import LabelSummary

RESULTS = Path(__file__).resolve().parents[1] / "evals" / "results"
SVG = "{http://www.w3.org/2000/svg}"


def _load(label: str) -> LabelSummary:
    return LabelSummary.model_validate_json((RESULTS / label / "summary.json").read_text("utf-8"))


def test_render_svg_has_one_dumbbell_per_rfp_and_panel():
    a, b = _load("baseline"), _load("prompt_structure")
    svg = render_svg(a, b, a_name="Old", b_name="New", title="Old vs. new")
    root = ET.fromstring(svg)
    rows = [g for g in root.iter(f"{SVG}g") if g.find(f"{SVG}title") is not None]
    assert len(rows) == 4 * len(DEFAULT_PANELS)
    # NYESD judged coverage: baseline mean 78%, new prompts 91%.
    nyesd = next(
        g.find(f"{SVG}title").text
        for g in rows
        if g.find(f"{SVG}title").text.startswith("NYESD, Mandatory coverage")
    )
    assert "Old 78%" in nyesd and "New 91%" in nyesd


def test_render_svg_drops_panels_a_label_was_not_scored_on():
    # ablation_vlm was scored on match and cost only: two panels, laid out in one row.
    svg = render_svg(
        _load("baseline"), _load("ablation_vlm"), a_name="Off", b_name="On", title="VLM"
    )
    root = ET.fromstring(svg)
    titles = [t.text for t in root.iter(f"{SVG}text") if t.get("class") == "ptitle"]
    assert titles == ["Recall vs. reference", "Pipeline cost per run"]
    assert float(root.get("height")) < 300


def test_chart_command_writes_the_file(tmp_path):
    out = tmp_path / "chart.svg"
    result = CliRunner().invoke(
        cli.app, ["chart", "baseline", "prompt_structure", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    ET.fromstring(out.read_text("utf-8"))


def test_chart_command_refuses_an_unknown_label(tmp_path):
    result = CliRunner().invoke(
        cli.app, ["chart", "baseline", "no_such_label", "--out", str(tmp_path / "x.svg")]
    )
    assert result.exit_code == 1
