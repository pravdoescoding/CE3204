
from __future__ import annotations

from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def _color_for_utilization(u: Optional[float]) -> str:
    if u is None:
        return "gray"
    if u < 0.4:
        return "gold"
    if u < 0.8:
        return "green"
    if u <= 1.0:
        return "limegreen"
    return "red"


def draw_frame(results: Dict[str, Any], optimized: bool = False) -> plt.Figure:
    rows = results.get("results_by_storey", [])
    if not rows:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No frame results to display.", ha="center", va="center")
        ax.axis("off")
        return fig

    beam_span = results.get("input", {}).get("beam_span_m", 4.0)
    total_height = sum(float(r["height_m"]) for r in rows)

    fig, ax = plt.subplots(figsize=(11, max(4.5, 1.2 * len(rows))))
    y0 = 0.0
    for row in rows:
        y1 = y0 + float(row["height_m"])
        beam_u = row.get("beam_utilization_ratio")
        col_u = row.get("column_utilization_ratio")
        beam_color = _color_for_utilization(beam_u)
        column_color = _color_for_utilization(col_u)

        ax.plot([0, 0], [y0, y1], linewidth=5, color=column_color)
        ax.plot([beam_span, beam_span], [y0, y1], linewidth=5, color=column_color)
        ax.plot([0, beam_span], [y1, y1], linewidth=5, color=beam_color)

        ax.text(
            -0.12 * beam_span,
            (y0 + y1) / 2,
            f"C: {row.get('column_section', '')}\nU={col_u:.3f}",
            va="center",
            ha="right",
            fontsize=9,
        )
        ax.text(
            beam_span / 2,
            y1 + 0.03 * total_height,
            f"B: {row.get('beam_section', '')} | U={beam_u:.3f}",
            va="bottom",
            ha="center",
            fontsize=9,
        )
        ax.text(
            beam_span + 0.12 * beam_span,
            (y0 + y1) / 2,
            f"Storey {row.get('storey')}",
            va="center",
            ha="left",
            fontsize=9,
        )
        y0 = y1

    legend_lines = [
        Line2D([0], [0], color="gold", lw=5, label="U < 0.4  (overdesigned)"),
        Line2D([0], [0], color="green", lw=5, label="0.4 ≤ U < 0.8"),
        Line2D([0], [0], color="limegreen", lw=5, label="0.8 ≤ U ≤ 1.0"),
        Line2D([0], [0], color="red", lw=5, label="U > 1.0  (failing)"),
    ]

    ax.legend(
        handles=legend_lines,
        title="Utilization Ratio Legend",
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        borderaxespad=0.0,
    )

    ax.set_title("Steel Frame Visualization")
    ax.set_xlim(-0.4 * beam_span, 1.55 * beam_span)
    ax.set_ylim(0, total_height * 1.10)
    ax.set_xlabel("Beam Span (m)")
    ax.set_ylabel("Height (m)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig
