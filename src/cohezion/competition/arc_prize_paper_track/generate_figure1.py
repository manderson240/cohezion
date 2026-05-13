"""Generate Figure 1: Compound Loop Architecture diagram."""

from __future__ import annotations

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def draw_compound_loop():
    _fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Title
    ax.text(5, 5.6, "Figure 1: The Compound Loop", fontsize=16, ha="center", fontweight="bold")

    # Phase boxes
    phases = [
        ("ALIGNMENT\nGATE", 1.5, 3.5, "#4A90D9"),
        ("EXECUTION", 4.0, 3.5, "#7ED321"),
        ("RETROSPECTION", 6.5, 3.5, "#F5A623"),
        ("SKILL\nREFINEMENT", 9.0, 3.5, "#D0021B"),
    ]

    for label, x, y, color in phases:
        box = FancyBboxPatch(
            (x - 0.8, y - 0.4),
            1.6,
            0.8,
            boxstyle="round,pad=0.05,rounding_size=0.1",
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            alpha=0.85,
        )
        ax.add_patch(box)
        ax.text(
            x, y, label, ha="center", va="center", fontsize=10, fontweight="bold", color="white"
        )

    # Arrows between phases (circular flow)
    arrow_style = "Simple,head_width=8,head_length=6"
    kw = dict(arrowstyle=arrow_style, color="#333333", linewidth=2)

    # Alignment -> Execution
    ax.annotate("", xy=(3.2, 3.5), xytext=(2.3, 3.5), arrowprops=kw)
    ax.text(2.75, 3.75, "proceed", fontsize=7, ha="center", color="#555")

    # Execution -> Retrospection
    ax.annotate("", xy=(5.7, 3.5), xytext=(4.8, 3.5), arrowprops=kw)
    ax.text(5.25, 3.75, "complete", fontsize=7, ha="center", color="#555")

    # Retrospection -> Refinement
    ax.annotate("", xy=(8.2, 3.5), xytext=(7.3, 3.5), arrowprops=kw)
    ax.text(7.75, 3.75, "analyze", fontsize=7, ha="center", color="#555")

    # Refinement -> Alignment (wrap around)
    ax.annotate(
        "",
        xy=(1.5, 4.6),
        xytext=(9.0, 4.6),
        arrowprops=dict(
            arrowstyle=arrow_style, color="#333333", linewidth=2, connectionstyle="arc3,rad=-0.3"
        ),
    )
    ax.text(5.25, 5.1, "feedback", fontsize=7, ha="center", color="#555")

    # Central annotations
    ax.text(
        5,
        2.3,
        "Journey Tracker logs every state transition\nExperience Vault stores canonical task signatures\nSkill Library grows via recursive refinement",
        ha="center",
        va="center",
        fontsize=9,
        style="italic",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", edgecolor="#999"),
    )

    # Decision diamonds (governance checks)
    diamond_kw = dict(
        marker="D", markersize=14, color="#9013FE", markeredgecolor="black", markeredgewidth=1.2
    )
    ax.plot(2.75, 2.8, **diamond_kw)
    ax.text(2.75, 2.25, "HIHO\ncheck", ha="center", fontsize=7, color="#555")

    ax.plot(7.75, 2.8, **diamond_kw)
    ax.text(7.75, 2.25, "inflection\ndetect", ha="center", fontsize=7, color="#555")

    # Legend
    legend_elements = [
        mpatches.Patch(color="#4A90D9", label="Alignment Gate"),
        mpatches.Patch(color="#7ED321", label="Execution"),
        mpatches.Patch(color="#F5A623", label="Retrospection"),
        mpatches.Patch(color="#D0021B", label="Skill Refinement"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    out = "/home/mike-anderson/dev/cohezion/src/cohezion/competition/arc_prize_paper_track/figure1_compound_loop.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out}")
    plt.close()


if __name__ == "__main__":
    draw_compound_loop()
