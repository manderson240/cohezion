#!/usr/bin/env python3
"""Cohezion Evaluate: Compute FLUME metrics with statistical rigor.

Loads trajectory data from quickstart.py and computes 6 capability metrics
derived from the 12D manifold physics. Each metric has a bootstrap 95%
confidence interval so you can assess significance.

The 6 FLUME Metrics:
  1. Coherence Amplitude    - How close the agent stays to HIHO (0.5)
  2. Phase Locking Rate     - Fraction of steps with SPIN alignment
  3. Exotic Charge Lifetime - Consecutive steps maintaining charge sign
  4. Orbit Quality          - Trajectory smoothness (low jerk = better)
  5. TRIUNE Balance Index   - Equality across Space/Field/Control fabrics
  6. Recovery Basin Radius  - Distance from HIHO where agent can still recover

Why these matter for LLM training:
  These metrics characterize the geometry of the agent's policy in a
  physically grounded way. A model that achieves high coherence amplitude
  and phase locking has learned stable reasoning patterns. High orbit
  quality indicates smooth decision-making. The recovery basin measures
  robustness -- how far the model can deviate before losing coherence.
  These provide richer training signals than scalar accuracy alone.

Usage:
  uv run python evaluate.py                     # Default: data/trajectories.json
  uv run python evaluate.py --input other.json  # Custom input
  uv run python evaluate.py --no-plot           # Skip radar chart
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_trajectories(path: Path) -> dict:
    """Load trajectory data from quickstart output."""
    if not path.exists():
        print(f"[ERROR] Trajectory file not found: {path}")
        print("Run quickstart.py first: uv run python quickstart.py")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    n_episodes = len(data["episodes"])
    n_steps = sum(len(ep["trajectory"]) for ep in data["episodes"])
    print(f"[OK] Loaded {n_episodes} episodes, {n_steps:,} trajectory steps")
    return data


# ---------------------------------------------------------------------------
# Metric computation functions
# ---------------------------------------------------------------------------


def compute_coherence_amplitude(episodes: list[dict]) -> list[float]:
    """Per-episode coherence amplitude: mean closeness to HIHO (0.5).

    Defined as 1 - mean|coherence - 1.0|, where coherence is already
    computed as proximity to HIHO. Higher = agent stays closer to the
    0.5 equilibrium across all 7 brane dimensions.
    """
    values = []
    for ep in episodes:
        coherences = [s["coherence"] for s in ep["trajectory"]]
        if coherences:
            values.append(float(np.mean(coherences)))
    return values


def compute_phase_locking_rate(episodes: list[dict]) -> list[float]:
    """Per-episode fraction of steps where rotation and precession are aligned.

    Phase locking occurs when the SPIN rotation (sigma_x) and precession
    (sigma_y) have the same sign -- the agent's internal intent and
    external behavior are in phase. This corresponds to constructive
    interference on the Bloch sphere.
    """
    values = []
    for ep in episodes:
        steps = ep["trajectory"]
        if not steps:
            continue
        locked = sum(1 for s in steps if s["spin_rotation"] * s["spin_precession"] > 0)
        values.append(locked / len(steps))
    return values


def compute_exotic_charge_lifetime(episodes: list[dict]) -> list[float]:
    """Per-episode mean consecutive steps maintaining charge polarity sign.

    "Exotic charge" is sustained deviation from neutral (charge != 0).
    Longer lifetimes indicate the agent can maintain a coherent strategy
    (exploitation or exploration) without oscillating. Measured as the
    mean run length of same-sign charge polarity.
    """
    values = []
    for ep in episodes:
        steps = ep["trajectory"]
        if not steps:
            continue

        run_lengths = []
        current_run = 1
        for i in range(1, len(steps)):
            same_sign = (steps[i]["charge_polarity"] >= 0) == (steps[i - 1]["charge_polarity"] >= 0)
            if same_sign:
                current_run += 1
            else:
                run_lengths.append(current_run)
                current_run = 1
        run_lengths.append(current_run)
        values.append(float(np.mean(run_lengths)))
    return values


def compute_orbit_quality(episodes: list[dict]) -> list[float]:
    """Per-episode orbit quality: inverse of trajectory jerk (3rd derivative).

    Low jerk means smooth trajectories through the manifold -- the agent
    isn't making erratic jumps. Computed from consecutive 12D state vectors.
    Normalized to [0, 1] where 1 = perfectly smooth.
    """
    values = []
    for ep in episodes:
        steps = ep["trajectory"]
        if len(steps) < 4:
            values.append(0.5)
            continue

        states = np.array([s["state_12d"] for s in steps])
        # Finite differences: velocity, acceleration, jerk
        vel = np.diff(states, axis=0)
        acc = np.diff(vel, axis=0)
        jerk = np.diff(acc, axis=0)

        mean_jerk = float(np.mean(np.linalg.norm(jerk, axis=1)))
        # Normalize: jerk of 0 -> quality 1.0, jerk of 1.0 -> quality ~0.37
        quality = float(np.exp(-mean_jerk))
        values.append(quality)
    return values


def compute_triune_balance(episodes: list[dict]) -> list[float]:
    """Per-episode TRIUNE balance index: equality across 3 fabric groups.

    The 12D manifold has 4 fabrics (Space, Field, Control, Precipitation),
    each with 3 dimensions. The TRIUNE balance measures how equally
    activated the first 3 fabrics are (dims 0-2, 3-5, 6-8). Perfect
    balance = 1.0, complete imbalance = 0.0.

    Uses 1 - normalized coefficient of variation of fabric norms.
    """
    values = []
    for ep in episodes:
        steps = ep["trajectory"]
        if not steps:
            continue

        balances = []
        for s in steps:
            state = np.array(s["state_12d"])
            space_norm = float(np.linalg.norm(state[0:3]))
            field_norm = float(np.linalg.norm(state[3:6]))
            control_norm = float(np.linalg.norm(state[6:9]))

            norms = [space_norm, field_norm, control_norm]
            mean_norm = np.mean(norms)
            if mean_norm > 1e-10:
                cv = float(np.std(norms) / mean_norm)
                balances.append(max(0.0, 1.0 - cv))
            else:
                balances.append(0.0)

        values.append(float(np.mean(balances)))
    return values


def compute_recovery_basin_radius(episodes: list[dict]) -> list[float]:
    """Per-episode recovery basin radius: max HIHO deviation that still recovers.

    Scans the trajectory for the largest HIHO deviation that is followed
    (within 10 steps) by a return to coherence > 0.7. Measures the
    robustness of the agent's attractor basin. Larger = more robust.
    """
    values = []
    for ep in episodes:
        steps = ep["trajectory"]
        if len(steps) < 11:
            values.append(0.0)
            continue

        max_recovery = 0.0
        for i in range(len(steps) - 10):
            deviation = steps[i]["hiho_deviation"]
            # Check if coherence recovers within 10 steps
            future_coherences = [steps[i + j]["coherence"] for j in range(1, 11)]
            if max(future_coherences) > 0.7:
                max_recovery = max(max_recovery, deviation)

        values.append(max_recovery)
    return values


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: list[float],
    n_boot: int = 10000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute bootstrap mean and confidence interval.

    Returns (mean, ci_lower, ci_upper).
    """
    if not values:
        return 0.0, 0.0, 0.0

    arr = np.array(values)
    observed_mean = float(np.mean(arr))

    rng = np.random.default_rng(seed)
    boot_means = np.zeros(n_boot)
    n = len(arr)

    for i in range(n_boot):
        sample = arr[rng.integers(0, n, size=n)]
        boot_means[i] = np.mean(sample)

    alpha = (1 - ci) / 2
    ci_lower = float(np.percentile(boot_means, 100 * alpha))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha)))

    return observed_mean, ci_lower, ci_upper


# ---------------------------------------------------------------------------
# Output formatting and plotting
# ---------------------------------------------------------------------------

METRIC_SPECS = [
    ("Coherence Amplitude", compute_coherence_amplitude, "[0,1] higher=better"),
    ("Phase Locking Rate", compute_phase_locking_rate, "[0,1] higher=better"),
    ("Exotic Charge Lifetime", compute_exotic_charge_lifetime, "steps, higher=better"),
    ("Orbit Quality", compute_orbit_quality, "[0,1] higher=better"),
    ("TRIUNE Balance Index", compute_triune_balance, "[0,1] higher=better"),
    ("Recovery Basin Radius", compute_recovery_basin_radius, "deviation, higher=better"),
]


def compute_all_metrics(episodes: list[dict]) -> dict[str, dict]:
    """Compute all 6 FLUME metrics with bootstrap CIs."""
    results = {}
    for name, fn, scale in METRIC_SPECS:
        values = fn(episodes)
        mean, ci_lo, ci_hi = bootstrap_ci(values)
        results[name] = {
            "mean": mean,
            "ci_lower": ci_lo,
            "ci_upper": ci_hi,
            "std": float(np.std(values)) if values else 0.0,
            "n": len(values),
            "scale": scale,
            "raw_values": values,
        }
    return results


def print_results(results: dict[str, dict]):
    """Print a formatted table of results."""
    print(f"\n{'=' * 78}")
    print("  FLUME Capability Metrics (6 metrics, bootstrap 95% CI, n=10000)")
    print(f"{'=' * 78}\n")

    header = f"  {'Metric':<28} {'Mean':>8} {'95% CI':>20} {'Std':>8}  {'Scale'}"
    print(header)
    print(f"  {'-' * 76}")

    for name, data in results.items():
        ci_str = f"[{data['ci_lower']:.4f}, {data['ci_upper']:.4f}]"
        print(f"  {name:<28} {data['mean']:8.4f} {ci_str:>20} {data['std']:8.4f}  {data['scale']}")

    print(f"\n  n = {list(results.values())[0]['n']} episodes per metric")
    print(f"{'=' * 78}")


def plot_radar(results: dict[str, dict], output_path: Path):
    """Generate a radar chart of the 6 FLUME metrics."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n  [SKIP] matplotlib not installed -- no radar chart generated")
        print("  Install with: uv pip install matplotlib")
        return

    # Normalize metrics to [0, 1] for radar chart
    names = list(results.keys())
    means = []
    for name in names:
        val = results[name]["mean"]
        # Normalize charge lifetime and recovery radius to ~[0,1]
        if "Lifetime" in name:
            val = min(val / 50.0, 1.0)  # 50 steps = max displayed
        elif "Radius" in name:
            val = min(val / 0.5, 1.0)  # 0.5 deviation = max displayed
        means.append(val)

    # Radar chart
    n_metrics = len(names)
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    means_plot = means + [means[0]]  # Close the polygon
    angles += [angles[0]]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.fill(angles, means_plot, alpha=0.25, color="#2563eb")
    ax.plot(angles, means_plot, "o-", linewidth=2, color="#2563eb", markersize=6)

    # Labels
    short_names = [
        "Coherence\nAmplitude",
        "Phase\nLocking",
        "Charge\nLifetime",
        "Orbit\nQuality",
        "TRIUNE\nBalance",
        "Recovery\nBasin",
    ]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(short_names, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, alpha=0.7)
    ax.set_title("FLUME Capability Radar", fontsize=14, fontweight="bold", pad=20)

    # Add value annotations
    for i, (angle, val) in enumerate(zip(angles[:-1], means)):
        ax.annotate(
            f"{val:.2f}",
            xy=(angle, val),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Radar chart saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate FLUME metrics from trajectory data")
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).parent / "data" / "trajectories.json"),
        help="Path to trajectories.json from quickstart.py",
    )
    parser.add_argument("--no-plot", action="store_true", help="Skip radar chart generation")
    args = parser.parse_args()

    data = load_trajectories(Path(args.input))
    episodes = data["episodes"]

    results = compute_all_metrics(episodes)
    print_results(results)

    # Save metrics to JSON
    output_dir = Path(__file__).parent / "data"
    metrics_path = output_dir / "metrics.json"
    serializable = {
        name: {k: v for k, v in vals.items() if k != "raw_values"} for name, vals in results.items()
    }
    with open(metrics_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Metrics saved to: {metrics_path}")

    # Radar chart
    if not args.no_plot:
        plot_radar(results, output_dir / "capability_radar.png")

    print("\n  Next: uv run python export_dataset.py")


if __name__ == "__main__":
    main()
