"""A before/after chart of two labels' ``summary.json``, as a self-contained SVG.

One small panel per metric, one row per RFP, a dumbbell per row: a light dot for label A
(before), a dark dot for label B (after), joined by a thin line, and B's value written
next to it with A's in brackets. The values are the per-RFP means from the consistency
block, so the chart and ``diff`` show the same numbers. No plotting library: the SVG is
written by hand so the harness keeps its dependency list, and the colours follow the
system's light or dark setting through a ``prefers-color-scheme`` block.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape

from evals.harness.report import LabelSummary

RFP_NAMES = {"colfax": "Colfax", "federal_way": "Federal Way", "missouri": "Missouri"}


@dataclass(frozen=True)
class Panel:
    metric: str  # key in Consistency.metrics
    title: str
    fmt: Callable[[float], str]
    step: float  # tick step; the axis snaps outward to it


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def _usd(v: float) -> str:
    return f"${v:.3f}"


DEFAULT_PANELS = (
    Panel("recall", "Recall vs. reference", _pct, 0.05),
    Panel("precision", "Precision (judge)", _pct, 0.05),
    Panel("judged_coverage", "Mandatory coverage confirmed by the judge", _pct, 0.05),
    Panel("cost_usd", "Pipeline cost per run", _usd, 0.02),
)

# Reference palette (dataviz skill): blue ramp steps 250 and 550, light and dark surfaces.
STYLE = """
.surface { fill: #fcfcfb; }
.title { fill: #0b0b0b; font-weight: 600; font-size: 15px; }
.ptitle { fill: #0b0b0b; font-weight: 600; font-size: 13px; }
.label { fill: #52514e; font-size: 12px; }
.value { fill: #0b0b0b; font-size: 12px; font-variant-numeric: tabular-nums; }
.was { fill: #898781; font-size: 12px; font-variant-numeric: tabular-nums; }
.tick { fill: #898781; font-size: 11px; font-variant-numeric: tabular-nums; }
.grid { stroke: #e1e0d9; stroke-width: 1; }
.link { stroke: #c3c2b7; stroke-width: 2; stroke-linecap: round; }
.a { fill: #86b6ef; stroke: #fcfcfb; stroke-width: 2; }
.b { fill: #1c5cab; stroke: #fcfcfb; stroke-width: 2; }
text { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
@media (prefers-color-scheme: dark) {
  .surface { fill: #1a1a19; }
  .title, .ptitle, .value { fill: #f0efec; }
  .label { fill: #c3c2b7; }
  .grid { stroke: #2c2c2a; }
  .link { stroke: #383835; }
  .a { fill: #184f95; stroke: #1a1a19; }
  .b { fill: #6da7ec; stroke: #1a1a19; }
}
"""


def _axis(values: Sequence[float], step: float, cap: float | None) -> tuple[float, float]:
    lo = math.floor(min(values) / step - 1e-9) * step
    hi = math.ceil(max(values) / step + 1e-9) * step
    if cap is not None:
        hi = min(hi, cap)
    if hi - lo < 2 * step:
        lo = hi - 2 * step
    return lo, hi


def _means(summary: LabelSummary, metric: str) -> dict[str, float]:
    return {c.rfp: c.metrics[metric].mean for c in summary.consistency if metric in c.metrics}


def render_svg(
    a: LabelSummary,
    b: LabelSummary,
    *,
    a_name: str,
    b_name: str,
    title: str,
    panels: Sequence[Panel] = DEFAULT_PANELS,
) -> str:
    """Two columns of panels; each panel has a row per RFP present in both labels."""
    rfps = [c.rfp for c in a.consistency if any(d.rfp == c.rfp for d in b.consistency)]
    if not rfps:
        raise ValueError("the two labels share no RFP")

    width, cols, gutter, margin = 880, 2, 32, 16
    pw = (width - 2 * margin - gutter) / cols
    label_w, value_w = 92, 96  # row names on the left, "96% (99%)" on the right
    row_h, head_h, tick_h = 30, 30, 22
    ph = head_h + row_h * len(rfps) + tick_h
    top = 74  # title and legend
    rows_of_panels = math.ceil(len(panels) / cols)
    height = top + rows_of_panels * (ph + 24) + 4

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="0 0 {width} {height:.0f}" role="img" aria-label="{escape(title)}">',
        f"<style>{STYLE}</style>",
        f'<rect class="surface" width="{width}" height="{height:.0f}" rx="8"/>',
        f'<text class="title" x="{margin}" y="30">{escape(title)}</text>',
    ]
    # Legend: the dot classes, then the names.
    lx = margin
    for cls, name in (("a", a_name), ("b", b_name)):
        out.append(f'<circle class="{cls}" cx="{lx + 6}" cy="51" r="6"/>')
        out.append(f'<text class="label" x="{lx + 18}" y="55">{escape(name)}</text>')
        lx += 30 + 7.2 * len(name)

    for i, panel in enumerate(panels):
        ma, mb = _means(a, panel.metric), _means(b, panel.metric)
        shown = [r for r in rfps if r in ma and r in mb]
        if not shown:
            continue
        cap = 1.0 if panel.fmt is _pct else None
        lo, hi = _axis([*(ma[r] for r in shown), *(mb[r] for r in shown)], panel.step, cap)
        x0 = margin + (i % cols) * (pw + gutter)
        y0 = top + (i // cols) * (ph + 24)
        px0, px1 = x0 + label_w, x0 + pw - value_w

        def sx(v: float, lo=lo, hi=hi, px0=px0, px1=px1) -> float:
            return px0 + (v - lo) / (hi - lo) * (px1 - px0)

        out.append(f'<text class="ptitle" x="{x0}" y="{y0 + 16}">{escape(panel.title)}</text>')
        plot_top, plot_bot = y0 + head_h, y0 + head_h + row_h * len(rfps)
        n_ticks = round((hi - lo) / panel.step)
        for k in range(n_ticks + 1):
            v = lo + k * panel.step
            x = sx(v)
            out.append(
                f'<line class="grid" x1="{x:.1f}" y1="{plot_top}" x2="{x:.1f}" y2="{plot_bot}"/>'
            )
            out.append(
                f'<text class="tick" x="{x:.1f}" y="{plot_bot + 15}" '
                f'text-anchor="middle">{panel.fmt(v)}</text>'
            )
        for j, rfp in enumerate(rfps):
            if rfp not in shown:
                continue
            cy = plot_top + row_h * j + row_h / 2
            va, vb = ma[rfp], mb[rfp]
            xa, xb = sx(va), sx(vb)
            name = RFP_NAMES.get(rfp, rfp)
            tip = f"{name}, {panel.title}: {a_name} {panel.fmt(va)}, {b_name} {panel.fmt(vb)}"
            out.append(f"<g><title>{escape(tip)}</title>")
            out.append(f'<text class="label" x="{x0}" y="{cy + 4:.1f}">{escape(name)}</text>')
            out.append(
                f'<line class="link" x1="{xa:.1f}" y1="{cy:.1f}" x2="{xb:.1f}" y2="{cy:.1f}"/>'
            )
            out.append(f'<circle class="a" cx="{xa:.1f}" cy="{cy:.1f}" r="6"/>')
            out.append(f'<circle class="b" cx="{xb:.1f}" cy="{cy:.1f}" r="6"/>')
            tx = px1 + 12
            out.append(
                f'<text x="{tx:.1f}" y="{cy + 4:.1f}"><tspan class="value">{panel.fmt(vb)}</tspan>'
                f'<tspan class="was"> ({panel.fmt(va)})</tspan></text>'
            )
            out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"
