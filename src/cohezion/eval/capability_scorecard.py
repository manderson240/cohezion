"""Capability scorecard for FLUME journey benchmark evaluation.

Provides:
1. CapabilityScorecard — 6-axis radar chart of EVO physics capabilities
2. RadarChart — Plotly + matplotlib fallback radar visualization
3. LongitudinalTracker — Tracks scorecards across multiple benchmark runs
4. StatisticalComparison — Swarm vs self-supervised comparison tools

6 Axes (one per metric family):
  1. HIHO Coherence    — Ability to maintain coherence near 0.5
  2. TRIUNE Balance    — Equal Doer/Thinker/Knower activation
  3. Stability         — Low variance, consistent HIHO proximity
  4. Exotic Charge     — Sustained high charge accumulation
  5. Kordylewski Orbit — Stable L4/L5 Lagrange orbit maintenance
  6. SPIN Phase        — Monotonic phase accumulation

Example:
    scorecard = CapabilityScorecard()
    scorecard.record_run(
        run_id="run_001",
        episodes=[...],
        biographies=[...],
    )
    report = scorecard.generate_report()
    radar = scorecard.plot_radar()
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np


if TYPE_CHECKING:
    from pathlib import Path

    import plotly.graph_objects as go


try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


@dataclass(frozen=True)
class StatisticalComparison:
    """Result of comparing two benchmark populations (swarm vs self-supervised)."""

    metric: str
    group1_mean: float
    group2_mean: float
    difference: float
    percent_change: float
    p_value: float
    significant: bool
    n_group1: int
    n_group2: int


class RadarChart:
    """Radar/spider chart for 6-axis capability visualization.

    Uses Plotly if available, matplotlib as fallback.

    Attributes:
        axes: Names of the 6 capability axes.
        max_values: Upper bounds for each axis (for score normalization).
    """

    AXES = [
        "HIHO Coherence",
        "TRIUNE Balance",
        "Stability",
        "Exotic Charge",
        "Kordylewski Orbit",
        "SPIN Phase",
    ]

    MAX_VALUES = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    def __init__(self) -> None:
        self._axes = self.AXES
        self._max_values = self.MAX_VALUES

    def plot(
        self,
        values: list[float],
        title: str = "FLUME EVO Capability Scorecard",
        filename: str | Path | None = None,
    ) -> Any:
        """Plot a radar chart for the given capability values.

        Args:
            values: List of 6 values (one per axis).
            title: Chart title.
            filename: Optional path to save the HTML/SVG.

        Returns:
            Plotly Figure or matplotlib Figure.
        """
        if len(values) != len(self._axes):
            raise ValueError(f"Expected {len(self._axes)} values, got {len(values)}")

        if PLOTLY_AVAILABLE:
            return self._plot_plotly(values, title, filename)
        return self._plot_matplotlib(values, title, filename)

    def _plot_plotly(self, values: list[float], title: str, filename: str | Path | None) -> go.Figure:
        """Plot using Plotly."""
        import plotly.graph_objects as go

        normalized = [v / m for v, m in zip(values, self._max_values, strict=False)]
        normalized += normalized[:1]

        angles = [n / float(len(self._axes)) * 360 for n in range(len(self._axes))]
        angles += angles[:1]

        fig = go.Figure(
            data=[
                go.Scatterpolar(
                    r=normalized,
                    theta=angles,
                    fill="toself",
                    fillcolor="rgba(0, 113, 188, 0.3)",
                    line_color="rgba(0, 113, 188, 1.0)",
                    line_width=2.5,
                    name=title,
                    marker={"size": 6},
                )
            ]
        )

        tick_labels = [f"{a}\n{v:.2f}" for a, v in zip(self._axes, values, strict=False)]

        fig.update_layout(
            title={"text": title, "font_size": 18, "x": 0.5},
            polar={
                "radialaxis": {
                    "visible": True,
                    "range": [0.0, 1.0],
                    "tickfont_size": 10,
                },
                "angularaxis": {
                    "tickvals": [n / len(self._axes) * 360 for n in range(len(self._axes))],
                    "ticktext": tick_labels,
                    "tickfont_size": 11,
                },
            },
            showlegend=False,
            margin={"l": 60, "r": 60, "t": 60, "b": 60},
            width=700,
            height=600,
        )

        if filename is not None:
            fig.write_html(str(filename))

        return fig

    def _plot_matplotlib(self, values: list[float], title: str, filename: str | Path | None) -> Any:
        """Plot using matplotlib as fallback."""
        import matplotlib.pyplot as plt

        normalized = [v / m for v, m in zip(values, self._max_values, strict=False)]
        normalized += normalized[:1]

        angles = [n / float(len(self._axes)) * 2 * np.pi for n in range(len(self._axes))]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})

        ax.plot(angles, normalized, "o-", linewidth=2.5, color="steelblue")
        ax.fill(angles, normalized, alpha=0.3, color="steelblue")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([f"{a}\n{v:.2f}" for a, v in zip(self._axes, values, strict=False)], size=10)
        ax.set_ylim(0.0, 1.0)
        ax.set_title(title, size=16, pad=20)

        plt.tight_layout()

        if filename is not None:
            plt.savefig(str(filename), dpi=150, bbox_inches="tight")

        return fig

    def compare(
        self,
        group1_values: list[float],
        group2_values: list[float],
        group1_label: str = "Swarm",
        group2_label: str = "Self-Supervised",
        title: str = "Capability Comparison",
        filename: str | Path | None = None,
    ) -> Any:
        """Plot overlaid radar charts for two groups.

        Args:
            group1_values: Values for group 1.
            group2_values: Values for group 2.
            group1_label: Label for group 1.
            group2_label: Label for group 2.
            title: Chart title.
            filename: Optional path to save.

        Returns:
            Plotly Figure or matplotlib Figure.
        """
        if PLOTLY_AVAILABLE:
            import plotly.graph_objects as go

            norm1 = [v / m for v, m in zip(group1_values, self._max_values, strict=False)]
            norm1 += norm1[:1]
            norm2 = [v / m for v, m in zip(group2_values, self._max_values, strict=False)]
            norm2 += norm2[:1]

            angles = [n / float(len(self._axes)) * 360 for n in range(len(self._axes))]
            angles += angles[:1]

            fig = go.Figure()
            fig.add_trace(
                go.Scatterpolar(
                    r=norm1,
                    theta=angles,
                    fill="toself",
                    fillcolor="rgba(0, 113, 188, 0.3)",
                    line_color="rgba(0, 113, 188, 1.0)",
                    name=group1_label,
                    marker={"size": 6},
                )
            )
            fig.add_trace(
                go.Scatterpolar(
                    r=norm2,
                    theta=angles,
                    fill="toself",
                    fillcolor="rgba(200, 50, 50, 0.3)",
                    line_color="rgba(200, 50, 50, 1.0)",
                    name=group2_label,
                    marker={"size": 6},
                )
            )

            tick_labels = [
                f"{a}\n{g1:.2f} vs {g2:.2f}"
                for a, g1, g2 in zip(self._axes, group1_values, group2_values, strict=False)
            ]

            fig.update_layout(
                title={"text": title, "font_size": 18, "x": 0.5},
                polar={
                    "radialaxis": {"visible": True, "range": [0.0, 1.0], "tickfont_size": 10},
                    "angularaxis": {
                        "tickvals": [n / len(self._axes) * 360 for n in range(len(self._axes))],
                        "ticktext": tick_labels,
                        "tickfont_size": 10,
                    },
                },
                showlegend=True,
                legend={"x": 0.85, "y": 0.95},
                margin={"l": 60, "r": 60, "t": 60, "b": 60},
                width=800,
                height=650,
            )

            if filename is not None:
                fig.write_html(str(filename))

            return fig

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})

        n_axes = len(self._axes)
        angles = [i / float(n_axes) * 2 * np.pi for i in range(n_axes)]
        angles += angles[:1]

        norm1 = [v / m for v, m in zip(group1_values, self._max_values, strict=False)]
        norm1 += norm1[:1]
        norm2 = [v / m for v, m in zip(group2_values, self._max_values, strict=False)]
        norm2 += norm2[:1]

        ax.plot(angles, norm1, "o-", linewidth=2.5, color="steelblue", label=group1_label)
        ax.fill(angles, norm1, alpha=0.3, color="steelblue")
        ax.plot(angles, norm2, "s-", linewidth=2.5, color="crimson", label=group2_label)
        ax.fill(angles, norm2, alpha=0.3, color="crimson")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(self._axes, size=9)
        ax.set_ylim(0.0, 1.0)
        ax.set_title(title, size=16, pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

        plt.tight_layout()

        if filename is not None:
            plt.savefig(str(filename), dpi=150, bbox_inches="tight")

        return fig


class CapabilityScorecard:
    """6-axis capability scorecard tracking FLUME EVO physics benchmarks.

    Records benchmark runs and generates longitudinal reports tracking
    improvement across 6 EVO physics axes.

    Example:
        scorecard = CapabilityScorecard()
        scorecard.record_run("run_001", episodes=[...], biographies=[...])
        report = scorecard.generate_report()
        radar = scorecard.plot_radar()
    """

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._longitudinal_tracker = LongitudinalTracker()
        self._radar = RadarChart()
        self._metrics_computer: Any | None = None

    def record_run(
        self,
        run_id: str,
        episodes: list[dict[str, Any]],
        biographies: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        """Record a benchmark run.

        Args:
            run_id: Unique identifier for this run.
            episodes: List of episode summary dicts (one per episode).
            biographies: Optional list of biography lists for detailed metrics.
        """
        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

        metrics_computer = EVOPhysicsMetrics()

        scores: dict[str, float] = {}

        if biographies:
            all_metrics = {}
            for bio in biographies:
                results = metrics_computer.compute_all(bio)
                for key, result in results.items():
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append(result.mean)

            for key, values in all_metrics.items():
                scores[key] = float(np.mean(values)) if values else 0.0

        episode_coherences = [float(e.get("coherence", 0.5)) for e in episodes]
        episode_rewards = [float(e.get("reward", 0.0)) for e in episodes]
        episode_successes = [bool(e.get("success", False)) for e in episodes]

        self._runs[run_id] = {
            "timestamp": time.time(),
            "run_id": run_id,
            "n_episodes": len(episodes),
            "mean_coherence": float(np.mean(episode_coherences)),
            "std_coherence": float(np.std(episode_coherences, ddof=1)),
            "mean_reward": float(np.mean(episode_rewards)),
            "success_rate": float(np.mean(episode_successes)),
            "scores": scores,
            "per_episode": episodes,
        }

        self._longitudinal_tracker.record(run_id, scores)

    def generate_report(self) -> dict[str, Any]:
        """Generate a human-readable report of all recorded runs.

        Returns:
            Dictionary with full scorecard state.
        """
        if not self._runs:
            return {"error": "No runs recorded yet"}

        latest_run_id = max(self._runs, key=lambda r: self._runs[r]["timestamp"])
        latest = self._runs[latest_run_id]

        run_ids = sorted(self._runs.keys())
        longitudinal = self._longitudinal_tracker.get_trend_summary()

        axes = RadarChart.AXES
        latest_scores = latest.get("scores", {})
        current_values = [latest_scores.get(ax.lower().replace(" ", "_"), 0.0) for ax in axes]

        report = {
            "latest_run": latest_run_id,
            "latest_run_timestamp": latest.get("timestamp"),
            "total_runs": len(self._runs),
            "run_ids": run_ids,
            "latest": {
                "n_episodes": latest.get("n_episodes"),
                "mean_coherence": latest.get("mean_coherence"),
                "std_coherence": latest.get("std_coherence"),
                "mean_reward": latest.get("mean_reward"),
                "success_rate": latest.get("success_rate"),
                "scores": latest.get("scores", {}),
            },
            "current_capabilities": dict(zip(axes, current_values, strict=False)),
            "longitudinal": longitudinal,
        }

        return report

    def plot_radar(
        self,
        run_id: str | None = None,
        title: str | None = None,
        filename: str | Path | None = None,
    ) -> Any:
        """Plot a radar chart for a specific run or the latest run.

        Args:
            run_id: Run to plot. None = latest run.
            title: Chart title. None = auto-generated.
            filename: Optional path to save.

        Returns:
            Plotly Figure or matplotlib Figure.
        """
        if not self._runs:
            raise ValueError("No runs recorded yet")

        if run_id is None:
            run_id = max(self._runs, key=lambda r: self._runs[r]["timestamp"])

        run = self._runs[run_id]
        scores = run.get("scores", {})

        axes = RadarChart.AXES
        values = [scores.get(ax.lower().replace(" ", "_"), 0.0) for ax in axes]

        chart_title = title or f"FLUME EVO Capability Scorecard — {run_id}"

        return self._radar.plot(values, chart_title, filename)

    def compare_runs(
        self,
        run_id_1: str,
        run_id_2: str,
        filename: str | Path | None = None,
    ) -> list[StatisticalComparison]:
        """Compare two benchmark runs using Mann-Whitney U.

        Args:
            run_id_1: First run ID.
            run_id_2: Second run ID.
            filename: Optional path to save comparison radar chart.

        Returns:
            List of StatisticalComparison objects, one per metric.
        """
        if run_id_1 not in self._runs or run_id_2 not in self._runs:
            raise ValueError("One or both run IDs not found")

        run1 = self._runs[run_id_1]
        run2 = self._runs[run_id_2]

        scores1 = run1.get("scores", {})
        scores2 = run2.get("scores", {})

        axes = RadarChart.AXES
        values1 = [scores1.get(ax.lower().replace(" ", "_"), 0.0) for ax in axes]
        values2 = [scores2.get(ax.lower().replace(" ", "_"), 0.0) for ax in axes]

        if filename is not None:
            self._radar.compare(values1, values2, run_id_1, run_id_2, filename=filename)

        comparisons = []
        for ax, v1, v2 in zip(axes, values1, values2, strict=False):
            diff = v2 - v1
            pct = (diff / v1 * 100) if v1 != 0 else 0.0

            from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

            eps1 = run1.get("per_episode", [])
            eps2 = run2.get("per_episode", [])

            coh1 = np.array([float(e.get("coherence", 0.5)) for e in eps1])
            coh2 = np.array([float(e.get("coherence", 0.5)) for e in eps2])

            comparison = _mann_whitney_u(coh1, coh2)

            comparisons.append(
                StatisticalComparison(
                    metric=ax,
                    group1_mean=v1,
                    group2_mean=v2,
                    difference=diff,
                    percent_change=pct,
                    p_value=comparison.p_value,
                    significant=comparison.significant,
                    n_group1=len(eps1),
                    n_group2=len(eps2),
                )
            )

        return comparisons

    def export_json(self, path: str | Path) -> None:
        """Export scorecard to JSON.

        Args:
            path: Path to write the JSON file.
        """
        with open(path, "w") as f:
            json.dump(self._runs, f, indent=2, default=str)

    def import_json(self, path: str | Path) -> None:
        """Import scorecard from JSON.

        Args:
            path: Path to read the JSON file.
        """
        with open(path) as f:
            self._runs = json.load(f)


class LongitudinalTracker:
    """Tracks capability scorecards across multiple benchmark runs.

    Provides longitudinal analysis: improvement/decline trends across runs,
    identification of weakest axes, and swarm vs self-supervised comparison.
    """

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []
        self._axes = RadarChart.AXES

    def record(self, run_id: str, scores: dict[str, float]) -> None:
        """Record a run's scores.

        Args:
            run_id: Run identifier.
            scores: Dictionary mapping metric name to score.
        """
        self._history.append({"run_id": run_id, "scores": scores, "timestamp": time.time()})

    def get_trend_summary(self) -> dict[str, Any]:
        """Get a summary of trends across all recorded runs.

        Returns:
            Dictionary with per-axis trend information.
        """
        if len(self._history) < 2:
            return {"error": "Need at least 2 runs for trend analysis"}

        axes_key_map = {
            "HIHO Coherence": "coherence",
            "TRIUNE Balance": "triune_balance",
            "Stability": "stability",
            "Exotic Charge": "exotic_charge",
            "Kordylewski Orbit": "kordylewski_orbit",
            "SPIN Phase": "spin_phase",
        }

        trends: dict[str, dict[str, Any]] = {}

        for ax in self._axes:
            key = axes_key_map.get(ax, ax.lower().replace(" ", "_"))
            values = [(i, run["scores"].get(key, 0.0)) for i, run in enumerate(self._history) if key in run["scores"]]

            if len(values) < 2:
                continue

            indices = [v[0] for v in values]
            scores_arr = np.array([v[1] for v in values])

            if len(scores_arr) > 1:
                slope = float(np.polyfit(indices, scores_arr, 1)[0])
            else:
                slope = 0.0

            first_val = values[0][1]
            last_val = values[-1][1]
            delta = last_val - first_val
            pct_change = (delta / first_val * 100) if first_val != 0 else 0.0

            trends[ax] = {
                "slope": slope,
                "delta": delta,
                "percent_change": pct_change,
                "first_value": first_val,
                "last_value": last_val,
                "n_runs": len(values),
                "direction": "improving" if slope > 0.01 else ("declining" if slope < -0.01 else "stable"),
            }

        return trends

    def get_weakest_axis(self) -> str | None:
        """Return the axis with the lowest average score across all runs.

        Returns:
            Name of the weakest axis, or None if no data.
        """
        if not self._history:
            return None

        axes_key_map = {
            "HIHO Coherence": "coherence",
            "TRIUNE Balance": "triune_balance",
            "Stability": "stability",
            "Exotic Charge": "exotic_charge",
            "Kordylewski Orbit": "kordylewski_orbit",
            "SPIN Phase": "spin_phase",
        }

        axis_averages: dict[str, float] = {}

        for ax in self._axes:
            key = axes_key_map.get(ax, ax.lower().replace(" ", "_"))
            values = [run["scores"].get(key, 0.0) for run in self._history if key in run["scores"]]
            if values:
                axis_averages[ax] = float(np.mean(values))

        if not axis_averages:
            return None

        return min(axis_averages, key=axis_averages.get)  # type: ignore[arg-type]

    def get_strongest_axis(self) -> str | None:
        """Return the axis with the highest average score across all runs.

        Returns:
            Name of the strongest axis, or None if no data.
        """
        if not self._history:
            return None

        axes_key_map = {
            "HIHO Coherence": "coherence",
            "TRIUNE Balance": "triune_balance",
            "Stability": "stability",
            "Exotic Charge": "exotic_charge",
            "Kordylewski Orbit": "kordylewski_orbit",
            "SPIN Phase": "spin_phase",
        }

        axis_averages: dict[str, float] = {}

        for ax in self._axes:
            key = axes_key_map.get(ax, ax.lower().replace(" ", "_"))
            values = [run["scores"].get(key, 0.0) for run in self._history if key in run["scores"]]
            if values:
                axis_averages[ax] = float(np.mean(values))

        if not axis_averages:
            return None

        return max(axis_averages, key=axis_averages.get)  # type: ignore[arg-type]
