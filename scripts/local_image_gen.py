#!/usr/bin/env python3
"""
Local Image Generator Worker
Uses matplotlib + PIL to generate canonical diagrams
Lightweight, runs entirely locally
"""

import sys


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

import json
import time
from datetime import datetime
from pathlib import Path

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle


worker_id = sys.argv[1] if len(sys.argv) > 1 else "1"
output_dir = Path("/home/mike-anderson/.gemini/antigravity/brain/1b98adc2-8dce-436b-bac3-d27890e7ce04/assets")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"🎨 Local Image Generator starting at {datetime.now()}", flush=True)


def generate_hiho_stability():
    """Generate HIHO stability threshold diagram"""
    _fig, ax = plt.subplots(figsize=(10, 6))

    # Generate curve with peak at 0.5
    x = np.linspace(0, 1, 1000)
    # Gaussian-like curve centered at 0.5
    stability = np.exp(-20 * (x - 0.5) ** 2)

    # Color gradient
    ["#3498db" if xi < 0.5 else "#e74c3c" for xi in x]
    ax.fill_between(x, 0, stability, color="#3498db", alpha=0.3, label="Unprecipitated (Radiation)")
    ax.fill_between(
        x[x >= 0.5],
        0,
        stability[x >= 0.5],
        color="#e74c3c",
        alpha=0.3,
        label="Precipitated (Matter)",
    )
    ax.plot(x, stability, color="#2c3e50", linewidth=2)

    # Mark peak
    ax.plot(
        0.5,
        1.0,
        "o",
        markersize=15,
        color="gold",
        markeredgecolor="black",
        markeredgewidth=2,
        zorder=5,
    )
    ax.annotate(
        "Maximum Stability\n(HIHO Point)",
        xy=(0.5, 1.0),
        xytext=(0.5, 1.15),
        ha="center",
        fontsize=12,
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "lw": 2, "color": "gold"},
    )

    ax.set_xlabel("Coherence (Reality Overlap)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Stability", fontsize=12, fontweight="bold")
    ax.set_title("HIHO Stability Principle (Half In, Half Out)", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.3)

    plt.tight_layout()
    plt.savefig(output_dir / "hiho_stability_threshold.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Generated hiho_stability_threshold.png", flush=True)


def generate_12d_space():
    """Generate TensorBeam 12D parameter space visualization"""
    _fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")

    # Concentric circles representing nested dimensions
    layers = [
        {
            "radius": 0.9,
            "color": "#f39c12",
            "label": "Awareness (Primary)",
            "dims": "1D",
        },
        {"radius": 0.7, "color": "#3498db", "label": "Space", "dims": "3D"},
        {"radius": 0.5, "color": "#2ecc71", "label": "Fields (T,E,M)", "dims": "3D"},
        {"radius": 0.3, "color": "#9b59b6", "label": "Particle (R,P,C)", "dims": "3D"},
    ]

    for layer in layers:
        circle = Circle(
            (0, 0),
            layer["radius"],
            fill=False,
            edgecolor=layer["color"],
            linewidth=4,
            linestyle="--",
            alpha=0.7,
        )
        ax.add_patch(circle)

        # Add label
        angle = np.radians(45)
        x = layer["radius"] * np.cos(angle) * 0.7
        y = layer["radius"] * np.sin(angle) * 0.7
        ax.text(
            x,
            y,
            f"{layer['label']}\n{layer['dims']}",
            fontsize=11,
            ha="center",
            va="center",
            fontweight="bold",
            bbox={"boxstyle": "round", "facecolor": layer["color"], "alpha": 0.3},
        )

    # Center point
    ax.plot(
        0,
        0,
        "o",
        markersize=20,
        color="gold",
        markeredgecolor="black",
        markeredgewidth=2,
        zorder=10,
    )
    ax.text(0, 0, "Void", ha="center", va="center", fontsize=10, fontweight="bold")

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")
    ax.set_title(
        "TensorBeam 12-Parameter Reality (Nested Quadrature)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Add dimension count
    ax.text(
        0,
        -1.25,
        "Total: 1 + 3 + 3 + 3 + 2 = 12 Parameters",
        ha="center",
        fontsize=10,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(output_dir / "tensorbeam_12d_space.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Generated tensorbeam_12d_space.png", flush=True)


def generate_gateway_progression():
    """Generate gateway progression chart"""
    _fig, ax = plt.subplots(figsize=(12, 6))

    # Gateway data
    gateways = list(range(43, 53))
    thresholds = [0.950 + (g - 43) * 0.001 for g in gateways]
    completed = [True] * 0  # None completed yet
    completed.extend([False] * len(gateways))

    # Create staircase
    for i, (gate, thresh) in enumerate(zip(gateways, thresholds, strict=False)):
        color = "#2ecc71" if i < len([c for c in completed if c]) else "#95a5a6"
        marker = "✓" if i < len([c for c in completed if c]) else "?"

        # Draw step
        rect = Rectangle(
            (i, 0),
            1,
            thresh,
            facecolor=color,
            edgecolor="black",
            linewidth=2,
            alpha=0.7,
        )
        ax.add_patch(rect)

        # Label
        ax.text(
            i + 0.5,
            thresh + 0.002,
            f"G{gate}\n{thresh:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )
        ax.text(
            i + 0.5,
            thresh / 2,
            marker,
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
        )

    ax.set_xlim(0, len(gateways))
    ax.set_ylim(0.945, 0.965)
    ax.set_xlabel("Gateway Number", fontsize=12, fontweight="bold")
    ax.set_ylabel("Required Mean Stability", fontsize=12, fontweight="bold")
    ax.set_title("Infinite Gateway Progression System", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_dir / "gateway_progression.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Generated gateway_progression.png", flush=True)


def generate_architecture_diagram():
    """Generate system architecture diagram"""
    _fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_aspect("equal")

    # Main coordinator
    main_x, main_y = 0, 0
    main_box = Rectangle(
        (main_x - 0.15, main_y - 0.08),
        0.3,
        0.16,
        facecolor="#3498db",
        edgecolor="black",
        linewidth=2,
    )
    ax.add_patch(main_box)
    ax.text(
        main_x,
        main_y,
        "Main\nCoordinator",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="white",
    )

    # HIHO Workers (circular arrangement)
    hiho_positions = []
    for i in range(8):
        angle = np.radians(i * 45)
        x = 0.6 * np.cos(angle)
        y = 0.6 * np.sin(angle)
        hiho_positions.append((x, y))

        box = Rectangle(
            (x - 0.08, y - 0.05),
            0.16,
            0.1,
            facecolor="#2ecc71",
            edgecolor="black",
            linewidth=1.5,
        )
        ax.add_patch(box)
        ax.text(
            x,
            y,
            f"HIHO\n#{i + 1}",
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
        )

        # Arrow from main
        ax.annotate(
            "",
            xy=(x, y),
            xytext=(main_x, main_y),
            arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#2c3e50"},
        )

    # Ollama Workers
    ollama_y = -0.8
    for i in range(6):
        x = -0.5 + i * 0.2
        box = Rectangle(
            (x - 0.07, ollama_y - 0.05),
            0.14,
            0.1,
            facecolor="#9b59b6",
            edgecolor="black",
            linewidth=1.5,
        )
        ax.add_patch(box)
        ax.text(
            x,
            ollama_y,
            f"Ollama\n#{i + 1}",
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
        )

        # Arrow from main
        ax.annotate(
            "",
            xy=(x, ollama_y + 0.05),
            xytext=(main_x, main_y - 0.08),
            arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#8e44ad"},
        )

    # Data storage
    data_x, data_y = 0, 0.9
    data_box = Rectangle(
        (data_x - 0.12, data_y - 0.06),
        0.24,
        0.12,
        facecolor="#e74c3c",
        edgecolor="black",
        linewidth=2,
    )
    ax.add_patch(data_box)
    ax.text(
        data_x,
        data_y,
        "Data Storage\n128GB/2TB",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="white",
    )

    # Arrow to data
    ax.annotate(
        "",
        xy=(data_x, data_y - 0.06),
        xytext=(main_x, main_y + 0.08),
        arrowprops={"arrowstyle": "<->", "lw": 2, "color": "#c0392b"},
    )

    # Labels
    ax.text(
        -0.95,
        0,
        "16 HIHO\nWorkers",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round", "facecolor": "#2ecc71", "alpha": 0.3},
    )
    ax.text(
        -0.95,
        -0.8,
        "6 Ollama\nWorkers",
        fontsize=10,
        fontweight="bold",
        bbox={"boxstyle": "round", "facecolor": "#9b59b6", "alpha": 0.3},
    )

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")
    ax.set_title(
        "Overnight Research System Architecture\nFramework Desktop: 32 Threads, 128GB RAM",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    plt.tight_layout()
    plt.savefig(output_dir / "overnight_architecture.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  ✓ Generated overnight_architecture.png", flush=True)


# Generate all images
print("Generating canonical images...", flush=True)
start_time = time.time()

generate_hiho_stability()
time.sleep(2)

generate_12d_space()
time.sleep(2)

generate_gateway_progression()
time.sleep(2)

generate_architecture_diagram()
time.sleep(2)

duration = time.time() - start_time

# Save metadata
metadata = {
    "generated_at": datetime.now().isoformat(),
    "worker_id": worker_id,
    "images_created": 4,
    "duration_seconds": duration,
    "output_directory": str(output_dir),
    "generator": "matplotlib_local",
}

(output_dir / "generation_metadata.json").write_text(json.dumps(metadata, indent=2))

print(f"\n✅ All images generated in {duration:.1f}s", flush=True)
print(f"📁 Saved to: {output_dir}", flush=True)

# Keep running
while True:
    time.sleep(3600)
