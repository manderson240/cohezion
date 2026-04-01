#!/usr/bin/env python3
"""
FLUME Patent Drawing Generator

Generates formal patent drawings for FLUME provisional application:
- FIG. 1: System architecture
- FIG. 2: VAE encoder-decoder
- FIG. 3: 12D physics-grounded state
- FIG. 4: Continuous trajectory prediction
- FIG. 5: HIHO double-well potential
- FIG. 6: Training loss convergence
- FIG. 7: Journey tracking dual-tier logging
- FIG. 8: Multi-scale reasoning flowchart

Output: PNG files in docs/patents/figures/
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle


# Create output directory
FIGURE_DIR = Path("/home/mike-anderson/dev/cohezion/docs/patents/figures")
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# Set publication quality
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 10
plt.rcParams["axes.linewidth"] = 1.5

print("=== FLUME Patent Drawing Generator ===\n")


def draw_figure_1():
    """FIG. 1: System Architecture - Triune Hierarchical Compression Pipeline"""
    print("Generating FIG. 1: System Architecture...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("FIG. 1: FLUME System Architecture", fontsize=12, fontweight="bold", pad=20)

    # Knower Encoder (2048D)
    knower = FancyBboxPatch(
        (1, 4), 2, 1, boxstyle="round,pad=0.1", facecolor="lightblue", edgecolor="blue", linewidth=2
    )
    ax.add_patch(knower)
    ax.text(2, 4.5, "Knower Encoder\n(2048D)", ha="center", va="center", fontsize=10)

    # Thinker VAE (512D)
    thinker = FancyBboxPatch(
        (4, 4),
        2,
        1,
        boxstyle="round,pad=0.1",
        facecolor="lightgreen",
        edgecolor="green",
        linewidth=2,
    )
    ax.add_patch(thinker)
    ax.text(5, 4.5, "Thinker VAE\n(512D)", ha="center", va="center", fontsize=10)

    # Doer Projector (12D)
    doer = FancyBboxPatch(
        (7, 4), 2, 1, boxstyle="round,pad=0.1", facecolor="lightcoral", edgecolor="red", linewidth=2
    )
    ax.add_patch(doer)
    ax.text(8, 4.5, "Doer Projector\n(12D)", ha="center", va="center", fontsize=10)

    # Arrows between tiers
    ax.annotate(
        "",
        xy=(4, 4.5),
        xytext=(3, 4.5),
        arrowprops=dict(arrowstyle="->", linewidth=2, color="blue"),
    )
    ax.annotate(
        "",
        xy=(7, 4.5),
        xytext=(6, 4.5),
        arrowprops=dict(arrowstyle="->", linewidth=2, color="green"),
    )

    # Text input
    ax.text(0.5, 4.5, "Text\nInput", ha="right", va="center", fontsize=9)
    ax.annotate("", xy=(1, 4.5), xytext=(0.7, 4.5), arrowprops=dict(arrowstyle="->", linewidth=1.5))

    # Observable output
    ax.text(9.5, 4.5, "Observable\nOutput", ha="left", va="center", fontsize=9)
    ax.annotate("", xy=(9, 4.5), xytext=(9.3, 4.5), arrowprops=dict(arrowstyle="->", linewidth=1.5))

    # Coherence regularizer
    coherence = FancyBboxPatch(
        (4, 2.5),
        2,
        0.8,
        boxstyle="round,pad=0.1",
        facecolor="yellow",
        edgecolor="orange",
        linewidth=2,
        linestyle="--",
    )
    ax.add_patch(coherence)
    ax.text(5, 2.9, "Coherence\nRegularizer\n(0.5 target)", ha="center", va="center", fontsize=9)

    # Connection to coherence
    ax.annotate(
        "",
        xy=(5, 4),
        xytext=(5, 3.3),
        arrowprops=dict(arrowstyle="->", linewidth=1.5, linestyle="--"),
    )

    # Trajectory navigator
    navigator = FancyBboxPatch(
        (4, 1),
        2,
        0.8,
        boxstyle="round,pad=0.1",
        facecolor="lavender",
        edgecolor="purple",
        linewidth=2,
        linestyle="--",
    )
    ax.add_patch(navigator)
    ax.text(5, 1.4, "Trajectory\nNavigator", ha="center", va="center", fontsize=9)

    # Connection to navigator
    ax.annotate(
        "",
        xy=(5, 4),
        xytext=(5, 1.8),
        arrowprops=dict(arrowstyle="->", linewidth=1.5, linestyle="--"),
    )

    # Dimension labels
    ax.text(2, 3.7, "2048D", ha="center", fontsize=8, style="italic")
    ax.text(5, 3.7, "512D", ha="center", fontsize=8, style="italic")
    ax.text(8, 3.7, "12D", ha="center", fontsize=8, style="italic")

    # Data flow label
    ax.text(
        5,
        0.3,
        "Data Flow: Text → Semantic → Reasoning → Physics",
        ha="center",
        fontsize=9,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig01_system_architecture.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig01_system_architecture.png")


def draw_figure_2():
    """FIG. 2: VAE Encoder-Decoder with HIHO Coherence Loss"""
    print("Generating FIG. 2: VAE Architecture...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(
        "FIG. 2: VAE Encoder-Decoder with HIHO Loss", fontsize=12, fontweight="bold", pad=20
    )

    # Input (2048D)
    ax.text(
        1,
        3,
        "2048D\nInput",
        ha="center",
        va="center",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightblue", linewidth=2),
    )

    # Encoder
    encoder = Rectangle((2.5, 2), 1.5, 2, linewidth=2, edgecolor="blue", facecolor="white")
    ax.add_patch(encoder)
    ax.text(3.25, 3, "Encoder", ha="center", va="center", fontsize=10)

    # Mu and log_var
    mu = Rectangle((4.5, 3.3), 1, 0.5, linewidth=2, edgecolor="green", facecolor="lightgreen")
    ax.add_patch(mu)
    ax.text(5, 3.55, "μ", ha="center", va="center", fontsize=12, fontweight="bold")

    logvar = Rectangle((4.5, 2.2), 1, 0.5, linewidth=2, edgecolor="green", facecolor="lightgreen")
    ax.add_patch(logvar)
    ax.text(5, 2.45, "log(σ²)", ha="center", va="center", fontsize=10)

    # Sampling
    sample = Circle((6.5, 3), 0.4, linewidth=2, edgecolor="red", facecolor="pink")
    ax.add_patch(sample)
    ax.text(6.5, 3, "ε", ha="center", va="center", fontsize=12, fontweight="bold")

    # Reparameterization
    ax.annotate(
        "", xy=(6.1, 3.55), xytext=(5.5, 3.55), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )
    ax.annotate(
        "", xy=(6.1, 2.45), xytext=(5.5, 2.45), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )
    ax.annotate("", xy=(6.1, 3), xytext=(6.9, 3), arrowprops=dict(arrowstyle="->", linewidth=1.5))

    # Latent z (512D)
    z = Rectangle((7.5, 2.7), 1, 0.6, linewidth=2, edgecolor="purple", facecolor="lavender")
    ax.add_patch(z)
    ax.text(8, 3, "z", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(8, 2.4, "512D", ha="center", fontsize=8)

    # Decoder
    decoder = Rectangle((2.5, 0.5), 1.5, 1, linewidth=2, edgecolor="blue", facecolor="white")
    ax.add_patch(decoder)
    ax.text(3.25, 1, "Decoder", ha="center", va="center", fontsize=10)

    # Reconstruction path
    ax.annotate("", xy=(8, 2.7), xytext=(8, 1.5), arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate("", xy=(4, 1), xytext=(9, 1), arrowprops=dict(arrowstyle="->", linewidth=1.5))

    # Output (2048D)
    ax.text(
        1,
        1,
        "2048D\nRecon",
        ha="center",
        va="center",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightblue", linewidth=2),
    )

    # Loss box
    loss_box = FancyBboxPatch(
        (4.5, 4.8),
        3,
        0.8,
        boxstyle="round,pad=0.1",
        facecolor="yellow",
        edgecolor="orange",
        linewidth=2,
    )
    ax.add_patch(loss_box)
    ax.text(6, 5.2, "Total Loss = Recon + KL + Coherence", ha="center", va="center", fontsize=9)

    # Connections to loss
    ax.annotate(
        "",
        xy=(5, 4.8),
        xytext=(3.25, 3),
        arrowprops=dict(arrowstyle="->", linewidth=1, linestyle="--"),
    )
    ax.annotate(
        "",
        xy=(6, 4.8),
        xytext=(8, 3),
        arrowprops=dict(arrowstyle="->", linewidth=1, linestyle="--"),
    )
    ax.annotate(
        "",
        xy=(6, 4.8),
        xytext=(6.5, 3),
        arrowprops=dict(arrowstyle="->", linewidth=1, linestyle="--"),
    )

    # Coherence loss detail
    ax.text(6, 5.5, "Coherence Loss: (μ_mean - 0.5)²", ha="center", fontsize=8, style="italic")

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig02_vae_architecture.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig02_vae_architecture.png")


def draw_figure_3():
    """FIG. 3: 12D Physics-Grounded State (Smith's 4 Fabrics)"""
    print("Generating FIG. 3: 12D Physics-Grounded State...")

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "FIG. 3: 12D Physics-Grounded State (Smith's 4 Fabrics)",
        fontsize=12,
        fontweight="bold",
        pad=20,
    )

    # Four fabrics as quadrants
    fabrics = [
        ("Space Fabric", ["x", "y", "z"], "lightblue", (1, 5)),
        ("Field Fabric", ["Tempic", "Electric", "Magnetic"], "lightgreen", (6, 5)),
        ("Control Fabric", ["Rotation", "Precession", "Charge"], "lightcoral", (1, 1)),
        ("Precipitation Fabric", ["Awareness", "Novelty", "Precipitation"], "lavender", (6, 1)),
    ]

    for name, dims, color, pos in fabrics:
        # Fabric box
        fabric = FancyBboxPatch(
            (pos[0], pos[1]),
            3.5,
            3.5,
            boxstyle="round,pad=0.1",
            facecolor=color,
            edgecolor="black",
            linewidth=2,
        )
        ax.add_patch(fabric)

        # Fabric name
        ax.text(
            pos[0] + 1.75, pos[1] + 3.2, name, ha="center", va="top", fontsize=10, fontweight="bold"
        )

        # Dimensions
        for i, dim in enumerate(dims):
            dim_box = Rectangle(
                pos[0] + 0.3,
                pos[1] + 2.5 - i * 0.8,
                2.9,
                0.6,
                linewidth=1.5,
                edgecolor="black",
                facecolor="white",
            )
            ax.add_patch(dim_box)
            ax.text(
                pos[0] + 1.75,
                pos[1] + 2.8 - i * 0.8,
                f"Dim {dims.index(dim) + 1}: {dim}",
                ha="center",
                va="center",
                fontsize=9,
            )

    # Central label
    ax.text(
        5,
        4.7,
        "12D Observable State",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="yellow", linewidth=2),
    )

    # Smith attribution
    ax.text(
        5,
        0.3,
        "Smith's 12-Parameter Reality Framework (1962)",
        ha="center",
        fontsize=9,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig03_12d_physics_state.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig03_12d_physics_state.png")


def draw_figure_4():
    """FIG. 4: Continuous Trajectory Prediction in 512D Manifold"""
    print("Generating FIG. 4: Trajectory Prediction...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title(
        "FIG. 4: Continuous Trajectory in 512D Manifold", fontsize=12, fontweight="bold", pad=20
    )

    # Manifold surface (curved)
    x = np.linspace(1, 9, 100)
    y = 2 + 0.5 * np.sin(x)
    ax.plot(x, y, "b-", linewidth=2, alpha=0.3, label="512D Manifold")

    # Start point
    ax.plot(2, 2.5, "go", markersize=15, label="Start Latent")
    ax.text(2, 2.3, "Start", ha="center", fontsize=9)

    # End point
    ax.plot(8, 2.5, "ro", markersize=15, label="Goal Latent")
    ax.text(8, 2.3, "Goal", ha="center", fontsize=9)

    # Trajectory path
    traj_x = np.linspace(2, 8, 50)
    traj_y = 2 + 0.5 * np.sin(traj_x)
    ax.plot(traj_x, traj_y, "g-", linewidth=3, label="Geodesic Trajectory")

    # Intermediate points
    for i, (x_pt, y_pt) in enumerate(zip(traj_x[::10], traj_y[::10])):
        ax.plot(x_pt, y_pt, "b.", markersize=10)
        if i == 0:
            ax.text(x_pt, y_pt + 0.3, f"Step {i}", ha="center", fontsize=8)
        elif i == len(traj_x[::10]) - 1:
            ax.text(x_pt, y_pt + 0.3, f"Step {i}", ha="center", fontsize=8)

    # Interpolation arrow
    ax.annotate(
        "",
        xy=(5, 3.5),
        xytext=(3, 3.5),
        arrowprops=dict(arrowstyle="->", linewidth=2, color="blue"),
    )
    ax.text(4, 3.7, "Interpolation: z = α·z₁ + (1-α)·z₂", ha="center", fontsize=9, style="italic")

    # Projection to 12D
    ax.annotate(
        "", xy=(5, 2.5), xytext=(5, 1.5), arrowprops=dict(arrowstyle="->", linewidth=2, color="red")
    )
    ax.text(5.5, 2, "Project to\n12D", ha="left", fontsize=9)

    # 12D output box
    output = Rectangle(6, 0.5, 2, 0.8, linewidth=2, edgecolor="red", facecolor="lightcoral")
    ax.add_patch(output)
    ax.text(7, 0.9, "12D\nObservable", ha="center", va="center", fontsize=9)

    # Legend
    ax.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig04_trajectory_prediction.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig04_trajectory_prediction.png")


def draw_figure_5():
    """FIG. 5: HIHO Double-Well Potential Energy Landscape"""
    print("Generating FIG. 5: HIHO Double-Well Potential...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 3)
    ax.set_xlabel("Coherence", fontsize=11)
    ax.set_ylabel("Free Energy", fontsize=11)
    ax.set_title("FIG. 5: HIHO Double-Well Potential", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Double-well potential: V(x) = (x - 0.5)^4 - 0.5*(x - 0.5)^2
    x = np.linspace(0, 1, 100)
    V = (x - 0.5) ** 4 - 0.5 * (x - 0.5) ** 2
    V = V - V.min()  # Shift to make minimum at 0
    V = V / V.max() * 2  # Scale

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

    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig05_hiho_double_well.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig05_hiho_double_well.png")


def draw_figure_6():
    """FIG. 6: Training Loss Convergence with Coherence Regularization"""
    print("Generating FIG. 6: Training Loss Convergence...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 1.2)
    ax.set_xlabel("Training Epochs", fontsize=11)
    ax.set_ylabel("Loss", fontsize=11)
    ax.set_title("FIG. 6: Training Loss Convergence", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Simulated training curves
    epochs = np.arange(1, 51)
    mse_loss = 0.8 * np.exp(-0.08 * epochs) + 0.13
    kl_loss = 0.6 * np.exp(-0.06 * epochs) + 0.43
    coherence_loss = 0.4 * np.exp(-0.1 * epochs) + 0.15
    total_loss = mse_loss + 0.1 * kl_loss + 0.1 * coherence_loss

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
    box = FancyBboxPatch(
        25,
        0.8,
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

    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig06_training_convergence.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig06_training_convergence.png")


def draw_figure_7():
    """FIG. 7: Journey Tracking Dual-Tier Logging"""
    print("Generating FIG. 7: Journey Tracking...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("FIG. 7: Dual-Tier Journey Tracking", fontsize=12, fontweight="bold", pad=20)

    # 12D Observable tier
    obs_tier = FancyBboxPatch(
        1, 4, 8, 1.5, boxstyle="round,pad=0.1", facecolor="lightcoral", edgecolor="red", linewidth=2
    )
    ax.add_patch(obs_tier)
    ax.text(
        5,
        4.75,
        "12D Observable State Tier",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    # Dimensions in observable tier
    dims = ["spatial", "tempic", "logic", "awareness"]
    for i, dim in enumerate(dims):
        ax.text(2 + i * 2, 4.3, f"{dim}", ha="center", fontsize=9)

    # 2048D Semantic tier
    sem_tier = FancyBboxPatch(
        1, 2, 8, 1.5, boxstyle="round,pad=0.1", facecolor="lightblue", edgecolor="blue", linewidth=2
    )
    ax.add_patch(sem_tier)
    ax.text(
        5,
        2.75,
        "2048D Semantic Context Tier",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
    )

    # LLM embedding
    ax.text(5, 2.3, "LLM Embedding (2048D)", ha="center", fontsize=9, style="italic")

    # Per-step logging
    ax.annotate(
        "",
        xy=(5, 4),
        xytext=(5, 3.5),
        arrowprops=dict(arrowstyle="<->", linewidth=2, color="purple"),
    )
    ax.text(5.5, 3.75, "Per-Step\nLogging", ha="left", fontsize=9)

    # Coherence tracking
    coherence_box = Rectangle(7, 4.2, 1.5, 0.5, linewidth=2, edgecolor="orange", facecolor="yellow")
    ax.add_patch(coherence_box)
    ax.text(7.75, 4.45, "Coherence", ha="center", va="center", fontsize=8)

    # Phi score
    phi_box = Rectangle(7, 2.2, 1.5, 0.5, linewidth=2, edgecolor="purple", facecolor="lavender")
    ax.add_patch(phi_box)
    ax.text(7.75, 2.45, "Phi Score", ha="center", va="center", fontsize=8)

    # Thermodynamic state
    thermo_box = Rectangle(1, 0.3, 2, 0.5, linewidth=2, edgecolor="green", facecolor="lightgreen")
    ax.add_patch(thermo_box)
    ax.text(2, 0.55, "Thermodynamic\nState", ha="center", va="center", fontsize=8)

    # Topological features
    topo_box = Rectangle(4, 0.3, 2, 0.5, linewidth=2, edgecolor="brown", facecolor="moccasin")
    ax.add_patch(topo_box)
    ax.text(5, 0.55, "Topological\nFeatures", ha="center", va="center", fontsize=8)

    # Journey export
    export_box = Rectangle(7, 0.3, 2, 0.5, linewidth=2, edgecolor="black", facecolor="white")
    ax.add_patch(export_box)
    ax.text(8, 0.55, "Journey\nExport", ha="center", va="center", fontsize=8)

    # Arrows
    ax.annotate("", xy=(2, 0.8), xytext=(2, 2), arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate("", xy=(5, 0.8), xytext=(5, 2), arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate("", xy=(8, 0.8), xytext=(8, 2), arrowprops=dict(arrowstyle="->", linewidth=1.5))

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig07_journey_tracking.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig07_journey_tracking.png")


def draw_figure_8():
    """FIG. 8: Multi-Scale Reasoning Flowchart"""
    print("Generating FIG. 8: Multi-Scale Reasoning...")

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("FIG. 8: Multi-Scale Reasoning Operation", fontsize=12, fontweight="bold", pad=20)

    # Start
    start = Circle((5, 9), 0.5, linewidth=2, edgecolor="black", facecolor="lightgreen")
    ax.add_patch(start)
    ax.text(5, 9, "Start", ha="center", va="center", fontsize=9)

    # Task input
    task = Rectangle(3, 7.5, 4, 0.8, linewidth=2, edgecolor="blue", facecolor="lightblue")
    ax.add_patch(task)
    ax.text(5, 7.9, "Task: Natural Language", ha="center", va="center", fontsize=9)

    # Knower scale
    knower = Rectangle(1, 6, 2.5, 1, linewidth=2, edgecolor="blue", facecolor="aliceblue")
    ax.add_patch(knower)
    ax.text(2.25, 6.5, "Knower Scale\n(2048D)", ha="center", va="center", fontsize=9)

    # Thinker scale
    thinker = Rectangle(3.75, 6, 2.5, 1, linewidth=2, edgecolor="green", facecolor="lightgreen")
    ax.add_patch(thinker)
    ax.text(5, 6.5, "Thinker Scale\n(512D)", ha="center", va="center", fontsize=9)

    # Doer scale
    doer = Rectangle(6.5, 6, 2.5, 1, linewidth=2, edgecolor="red", facecolor="lightcoral")
    ax.add_patch(doer)
    ax.text(7.75, 6.5, "Doer Scale\n(12D)", ha="center", va="center", fontsize=9)

    # Arrows between scales
    ax.annotate(
        "", xy=(3.75, 6.5), xytext=(3.5, 6.5), arrowprops=dict(arrowstyle="->", linewidth=2)
    )
    ax.annotate(
        "", xy=(6.5, 6.5), xytext=(6.25, 6.5), arrowprops=dict(arrowstyle="->", linewidth=2)
    )

    # Operations
    exhaustive = Rectangle(1, 4.5, 2.5, 0.8, linewidth=2, edgecolor="blue", facecolor="white")
    ax.add_patch(exhaustive)
    ax.text(2.25, 4.9, "Exhaustive Search", ha="center", fontsize=8)

    trajectory = Rectangle(3.75, 4.5, 2.5, 0.8, linewidth=2, edgecolor="green", facecolor="white")
    ax.add_patch(trajectory)
    ax.text(5, 4.9, "Trajectory Prediction", ha="center", fontsize=8)

    physical = Rectangle(6.5, 4.5, 2.5, 0.8, linewidth=2, edgecolor="red", facecolor="white")
    ax.add_patch(physical)
    ax.text(7.75, 4.9, "Physical Grounding", ha="center", fontsize=8)

    # Arrows down
    ax.annotate(
        "", xy=(2.25, 6), xytext=(2.25, 5.3), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )
    ax.annotate("", xy=(5, 6), xytext=(5, 5.3), arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate(
        "", xy=(7.75, 6), xytext=(7.75, 5.3), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )

    # Merge
    merge = Circle((5, 3), 0.5, linewidth=2, edgecolor="black", facecolor="yellow")
    ax.add_patch(merge)

    # Arrows to merge
    ax.annotate(
        "", xy=(2.25, 3.5), xytext=(2.25, 4.5), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )
    ax.annotate("", xy=(5, 3.5), xytext=(5, 4.5), arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate(
        "", xy=(7.75, 3.5), xytext=(7.75, 4.5), arrowprops=dict(arrowstyle="->", linewidth=1.5)
    )

    # Coherence check
    coherence = Rectangle(3, 2, 4, 0.8, linewidth=2, edgecolor="orange", facecolor="yellow")
    ax.add_patch(coherence)
    ax.text(5, 2.4, "Coherence Check (0.5)", ha="center", va="center", fontsize=9)

    # Decision
    ax.annotate("", xy=(5, 3), xytext=(5, 2.8), arrowprops=dict(arrowstyle="->", linewidth=2))

    # End
    end = Circle((5, 0.5), 0.5, linewidth=2, edgecolor="black", facecolor="lightcoral")
    ax.add_patch(end)
    ax.text(5, 0.5, "End", ha="center", va="center", fontsize=9)

    # Final arrow
    ax.annotate("", xy=(5, 0.5), xytext=(5, 2), arrowprops=dict(arrowstyle="->", linewidth=2))

    # Scale labels
    ax.text(
        5,
        5.5,
        "Multi-Scale Operation",
        ha="center",
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="white", linewidth=2),
    )

    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "fig08_multi_scale_reasoning.png", bbox_inches="tight")
    plt.close()
    print("  ✓ Saved: fig08_multi_scale_reasoning.png")


# Generate all figures
if __name__ == "__main__":
    draw_figure_1()
    draw_figure_2()
    draw_figure_3()
    draw_figure_4()
    draw_figure_5()
    draw_figure_6()
    draw_figure_7()
    draw_figure_8()

    print(f"\n=== Complete ===")
    print(f"Generated 8 patent figures in: {FIGURE_DIR.absolute()}")
    print("\nFigures:")
    for i, fig_file in enumerate(sorted(FIGURE_DIR.glob("fig*.png")), 1):
        print(f"  FIG. {i}: {fig_file.name}")
