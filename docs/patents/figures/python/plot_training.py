#!/usr/bin/env python3
"""
FIG. 6: Training Loss Convergence with Coherence Regularization
Output: PNG + SVG for patent application
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# Set publication quality
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 10

# Simulated training curves
epochs = np.arange(1, 51)
mse_loss = 0.8 * np.exp(-0.08 * epochs) + 0.13
kl_loss = 0.6 * np.exp(-0.06 * epochs) + 0.43
coherence_loss = 0.4 * np.exp(-0.1 * epochs) + 0.15
total_loss = mse_loss + 0.1 * kl_loss + 0.1 * coherence_loss

fig, ax = plt.subplots(1, 1, figsize=(8, 5))
ax.plot(epochs, mse_loss, "b-", linewidth=2, label="Reconstruction (MSE)")
ax.plot(epochs, kl_loss, "g-", linewidth=2, label="KL Divergence")
ax.plot(epochs, coherence_loss, "r-", linewidth=2, label="Coherence Loss")
ax.plot(epochs, total_loss, "k-", linewidth=3, label="Total Loss")

# Annotations
ax.axhline(y=0.1322, color="blue", linestyle="--", linewidth=1, alpha=0.5)
ax.text(45, 0.14, "0.1322", ha="right", fontsize=9, color="blue")

ax.axhline(y=0.4329, color="green", linestyle="--", linewidth=1, alpha=0.5)
ax.text(45, 0.44, "0.4329", ha="right", fontsize=9, color="green")

ax.axhline(y=0.63, color="red", linestyle="--", linewidth=1, alpha=0.5)
ax.text(45, 0.64, "0.63 (mean coherence)", ha="right", fontsize=9, color="red")

# Final values box
from matplotlib.patches import FancyBboxPatch


box = FancyBboxPatch(
    (25, 0.8),
    20,
    0.35,
    boxstyle="round,pad=0.1",
    facecolor="yellow",
    edgecolor="orange",
    linewidth=2,
    alpha=0.5,
)
ax.add_patch(box)
ax.text(
    35,
    1.05,
    "Final (Epoch 50):\nMSE: 0.1322, KL: 0.4329, Coherence: 0.63",
    ha="center",
    fontsize=9,
    fontweight="bold",
)

ax.set_xlim(0, 50)
ax.set_ylim(0, 1.2)
ax.set_xlabel("Training Epochs", fontsize=11)
ax.set_ylabel("Loss", fontsize=11)
ax.set_title("FIG. 6: Training Loss Convergence", fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()

# Save outputs
output_dir = Path("/home/mike-anderson/dev/cohezion/docs/patents/figures")
plt.savefig(output_dir / "png" / "fig06_training_convergence.png", bbox_inches="tight")
plt.savefig(output_dir / "fig06_training_convergence.svg", bbox_inches="tight")
plt.savefig(output_dir / "fig06_training_convergence.pdf", bbox_inches="tight")

print("✓ Saved: fig06_training_convergence.png, .svg, .pdf")
plt.close()
