#!/usr/bin/env python3
"""
FIG. 5: HIHO Double-Well Potential Energy Landscape
Output: PNG + SVG for patent application
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# Set publication quality
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 10

# Double-well potential: V(x) = (x - 0.5)^4 - 0.5*(x - 0.5)^2
x = np.linspace(0, 1, 100)
V = (x - 0.5) ** 4 - 0.5 * (x - 0.5) ** 2
V = V - V.min()  # Shift to make minimum at 0
V = V / V.max() * 2  # Scale

fig, ax = plt.subplots(1, 1, figsize=(8, 5))
ax.plot(x, V, "b-", linewidth=3, label="Free Energy Landscape")

# Minimum at 0.5
ax.axvline(x=0.5, color="red", linestyle="--", linewidth=2, label="HIHO Target (0.5)")
ax.plot(0.5, 0, "ro", markersize=15)
ax.text(0.5, 0.2, "Minimum\n(0.5)", ha="center", fontsize=9, fontweight="bold")

# Wells
ax.fill_between(x, 0, V, alpha=0.3, color="blue")

# Annotations
ax.text(
    0.25,
    1.5,
    "Exploration\n(novelty)",
    ha="center",
    fontsize=9,
    bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.5),
)
ax.text(
    0.75,
    1.5,
    "Exploitation\n(precipitation)",
    ha="center",
    fontsize=9,
    bbox=dict(boxstyle="round", facecolor="lightcoral", alpha=0.5),
)

# Thermodynamic derivation
ax.text(
    0.5,
    2.5,
    "Thermodynamic Ground State:\nMax Entropy at p = 0.5",
    ha="center",
    fontsize=9,
    style="italic",
    bbox=dict(boxstyle="round", facecolor="yellow", alpha=0.5),
)

ax.set_xlabel("Coherence", fontsize=11)
ax.set_ylabel("Free Energy", fontsize=11)
ax.set_title("FIG. 5: HIHO Double-Well Potential", fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()

# Save outputs
output_dir = Path("/home/mike-anderson/dev/cohezion/docs/patents/figures")
plt.savefig(output_dir / "png" / "fig05_hiho_double_well.png", bbox_inches="tight")
plt.savefig(output_dir / "fig05_hiho_double_well.svg", bbox_inches="tight")
plt.savefig(output_dir / "fig05_hiho_double_well.pdf", bbox_inches="tight")

print("✓ Saved: fig05_hiho_double_well.png, .svg, .pdf")
plt.close()
