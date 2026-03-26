"""6-axis capability scorecard for FLUME journey EVO physics benchmarks."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np


if TYPE_CHECKING:
    from pathlib import Path

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None


AXES = [
    "HIHO Coherence",
    "TRIUNE Balance",
    "Stability",
    "Exotic Charge",
    "Kordylewski Orbit",
    "SPIN Phase",
]
MAX_VALUES = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]


@dataclass(frozen=True)
class StatisticalComparison:
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
    AXES = AXES
    MAX_VALUES = MAX_VALUES

    def plot(
        self,
        values: list[float],
        title: str = "FLUME EVO Capability Scorecard",
        filename: str | Path | None = None,
    ) -> Any:
        if len(values) != len(self.AXES):
            raise ValueError(f"Expected {len(self.AXES)} values, got {len(values)}")
        if PLOTLY_AVAILABLE:
            return self._plot_plotly(values, title, filename)
        return self._plot_matplotlib(values, title, filename)

    def _plot_plotly(
        self, values: list[float], title: str, filename: str | Path | None
    ) -> go.Figure:
        normalized = [v / m for v, m in zip(values, self.MAX_VALUES, strict=True)]
        normalized += normalized[:1]
        angles = [n / len(self.AXES) * 360 for n in range(len(self.AXES))]
        angles += angles[:1]
        tick_labels = [f"{a}\n{v:.2f}" for a, v in zip(self.AXES, values, strict=True)]
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
        fig.update_layout(
            title={"text": title, "font_size": 18, "x": 0.5},
            polar={
                "radialaxis": {"visible": True, "range": [0.0, 1.0], "tickfont_size": 10},
                "angularaxis": {
                    "tickvals": [n / len(self.AXES) * 360 for n in range(len(self.AXES))],
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
        import matplotlib.pyplot as plt

        normalized = [v / m for v, m in zip(values, self.MAX_VALUES, strict=True)]
        normalized += normalized[:1]
        n = len(self.AXES)
        angles = [i / n * 2 * np.pi for i in range(n)]
        angles += angles[:1]
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
        ax.plot(angles, normalized, "o-", linewidth=2.5, color="steelblue")
        ax.fill(angles, normalized, alpha=0.3, color="steelblue")
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(
            [f"{a}\n{v:.2f}" for a, v in zip(self.AXES, values, strict=True)], size=10
        )
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
        if PLOTLY_AVAILABLE:
            return self._compare_plotly(
                group1_values, group2_values, group1_label, group2_label, title, filename
            )
        return self._compare_mpl(
            group1_values, group2_values, group1_label, group2_label, title, filename
        )

    def _compare_plotly(
        self,
        g1: list[float],
        g2: list[float],
        l1: str,
        l2: str,
        title: str,
        filename: str | Path | None,
    ) -> go.Figure:
        n1 = [v / m for v, m in zip(g1, self.MAX_VALUES, strict=True)]
        n1 += n1[:1]
        n2 = [v / m for v, m in zip(g2, self.MAX_VALUES, strict=True)]
        n2 += n2[:1]
        angles = [i / len(self.AXES) * 360 for i in range(len(self.AXES))]
        angles += angles[:1]
        fig = go.Figure(
            [
                go.Scatterpolar(
                    r=n1,
                    theta=angles,
                    fill="toself",
                    fillcolor="rgba(0, 113, 188, 0.3)",
                    line_color="rgba(0, 113, 188, 1.0)",
                    name=l1,
                    marker={"size": 6},
                ),
                go.Scatterpolar(
                    r=n2,
                    theta=angles,
                    fill="toself",
                    fillcolor="rgba(200, 50, 50, 0.3)",
                    line_color="rgba(200, 50, 50, 1.0)",
                    name=l2,
                    marker={"size": 6},
                ),
            ]
        )
        fig.update_layout(
            title={"text": title, "font_size": 18, "x": 0.5},
            polar={"radialaxis": {"visible": True, "range": [0.0, 1.0], "tickfont_size": 10}},
            showlegend=True,
            legend={"x": 0.85, "y": 0.95},
            margin={"l": 60, "r": 60, "t": 60, "b": 60},
            width=800,
            height=650,
        )
        if filename is not None:
            fig.write_html(str(filename))
        return fig

    def _compare_mpl(
        self,
        g1: list[float],
        g2: list[float],
        l1: str,
        l2: str,
        title: str,
        filename: str | Path | None,
    ) -> Any:
        import matplotlib.pyplot as plt

        n = len(self.AXES)
        angles = [i / n * 2 * np.pi for i in range(n)]
        angles += angles[:1]
        n1 = [v / m for v, m in zip(g1, self.MAX_VALUES, strict=True)]
        n1 += n1[:1]
        n2 = [v / m for v, m in zip(g2, self.MAX_VALUES, strict=True)]
        n2 += n2[:1]
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
        ax.plot(angles, n1, "o-", linewidth=2.5, color="steelblue", label=l1)
        ax.fill(angles, n1, alpha=0.3, color="steelblue")
        ax.plot(angles, n2, "s-", linewidth=2.5, color="crimson", label=l2)
        ax.fill(angles, n2, alpha=0.3, color="crimson")
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(self.AXES, size=9)
        ax.set_ylim(0.0, 1.0)
        ax.set_title(title, size=16, pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        plt.tight_layout()
        if filename is not None:
            plt.savefig(str(filename), dpi=150, bbox_inches="tight")
        return fig


class LongitudinalTracker:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []
        self._axes = AXES

    def record(self, run_id: str, scores: dict[str, float]) -> None:
        self._history.append({"run_id": run_id, "scores": scores, "timestamp": time.time()})

    def get_trend_summary(self) -> dict[str, Any]:
        if len(self._history) < 2:
            return {"error": "Need at least 2 runs for trend analysis"}
        key_map = {
            "HIHO Coherence": "coherence",
            "TRIUNE Balance": "triune_balance",
            "Stability": "stability",
            "Exotic Charge": "exotic_charge",
            "Kordylewski Orbit": "kordylewski_orbit",
            "SPIN Phase": "spin_phase",
        }
        trends: dict[str, Any] = {}
        for ax in self._axes:
            key = key_map.get(ax, ax.lower().replace(" ", "_"))
            values = [
                (i, run["scores"].get(key, 0.0))
                for i, run in enumerate(self._history)
                if key in run["scores"]
            ]
            if len(values) < 2:
                continue
            indices = [v[0] for v in values]
            scores_arr = np.array([v[1] for v in values])
            slope = float(np.polyfit(indices, scores_arr, 1)[0]) if len(values) > 1 else 0.0
            first_val = values[0][1]
            last_val = values[-1][1]
            delta = last_val - first_val
            pct = (delta / first_val * 100) if first_val != 0 else 0.0
            trends[ax] = {
                "slope": slope,
                "delta": delta,
                "percent_change": pct,
                "first_value": first_val,
                "last_value": last_val,
                "n_runs": len(values),
                "direction": "improving"
                if slope > 0.01
                else ("declining" if slope < -0.01 else "stable"),
            }
        return trends

    def get_weakest_axis(self) -> str | None:
        if not self._history:
            return None
        key_map = {k.lower().replace(" ", "_"): k for k in self._axes}
        averages: dict[str, list[float]] = {}
        for run in self._history:
            for key, score in run["scores"].items():
                axis = key_map.get(key, key)
                if axis not in averages:
                    averages[axis] = []
                averages[axis].append(score)
        if not averages:
            return None
        avg_scores = {ax: np.mean(vals) for ax, vals in averages.items()}
        return min(avg_scores, key=avg_scores.get)  # type: ignore[arg-type]

    def get_strongest_axis(self) -> str | None:
        if not self._history:
            return None
        key_map = {k.lower().replace(" ", "_"): k for k in self._axes}
        averages: dict[str, list[float]] = {}
        for run in self._history:
            for key, score in run["scores"].items():
                axis = key_map.get(key, key)
                if axis not in averages:
                    averages[axis] = []
                averages[axis].append(score)
        if not averages:
            return None
        avg_scores = {ax: np.mean(vals) for ax, vals in averages.items()}
        return max(avg_scores, key=avg_scores.get)  # type: ignore[arg-type]


class CapabilityScorecard:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._longitudinal = LongitudinalTracker()
        self._radar = RadarChart()

    def record_run(
        self,
        run_id: str,
        episodes: list[dict[str, Any]],
        biographies: list[dict[str, Any]] | None = None,
    ) -> None:
        scores: dict[str, float] = {}
        if biographies:
            from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

            engine = EVOPhysicsMetrics()
            all_metrics: dict[str, list[float]] = {}
            for bio in biographies:
                if not bio:
                    continue
                results = engine.compute_all(
                    bio.get("biography", bio) if isinstance(bio, dict) else bio
                )
                for key, result in results.items():
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append(result.mean)
            for key, values in all_metrics.items():
                scores[key] = float(np.mean(values))
        coherences = [float(e.get("coherence", 0.5)) for e in episodes]
        rewards = [float(e.get("reward", 0.0)) for e in episodes]
        successes = [bool(e.get("success", False)) for e in episodes]
        self._runs[run_id] = {
            "timestamp": time.time(),
            "run_id": run_id,
            "n_episodes": len(episodes),
            "mean_coherence": float(np.mean(coherences)),
            "std_coherence": float(np.std(coherences, ddof=1)),
            "mean_reward": float(np.mean(rewards)),
            "success_rate": float(np.mean(successes)),
            "scores": scores,
            "per_episode": episodes,
        }
        self._longitudinal.record(run_id, scores)

    def generate_report(self) -> dict[str, Any]:
        if not self._runs:
            return {"error": "No runs recorded yet"}
        latest_id = max(self._runs, key=lambda r: self._runs[r]["timestamp"])
        latest = self._runs[latest_id]
        current_values = [
            latest.get("scores", {}).get(ax.lower().replace(" ", "_"), 0.0) for ax in AXES
        ]
        return {
            "latest_run": latest_id,
            "latest_run_timestamp": latest.get("timestamp"),
            "total_runs": len(self._runs),
            "run_ids": sorted(self._runs.keys()),
            "latest": {
                "n_episodes": latest.get("n_episodes"),
                "mean_coherence": latest.get("mean_coherence"),
                "std_coherence": latest.get("std_coherence"),
                "mean_reward": latest.get("mean_reward"),
                "success_rate": latest.get("success_rate"),
                "scores": latest.get("scores", {}),
            },
            "current_capabilities": dict(zip(AXES, current_values, strict=True)),
            "longitudinal": self._longitudinal.get_trend_summary(),
        }

    def plot_radar(
        self,
        run_id: str | None = None,
        title: str | None = None,
        filename: str | Path | None = None,
    ) -> Any:
        if not self._runs:
            raise ValueError("No runs recorded yet")
        if run_id is None:
            run_id = max(self._runs, key=lambda r: self._runs[r]["timestamp"])
        run = self._runs[run_id]
        scores = run.get("scores", {})
        values = [scores.get(ax.lower().replace(" ", "_"), 0.0) for ax in AXES]
        chart_title = title or f"FLUME EVO Capability Scorecard — {run_id}"
        return self._radar.plot(values, chart_title, filename)

    def compare_runs(
        self, run_id_1: str, run_id_2: str, filename: str | Path | None = None
    ) -> list[StatisticalComparison]:
        if run_id_1 not in self._runs or run_id_2 not in self._runs:
            raise ValueError("One or both run IDs not found")
        r1, r2 = self._runs[run_id_1], self._runs[run_id_2]
        s1, s2 = r1.get("scores", {}), r2.get("scores", {})
        v1 = [s1.get(ax.lower().replace(" ", "_"), 0.0) for ax in AXES]
        v2 = [s2.get(ax.lower().replace(" ", "_"), 0.0) for ax in AXES]
        if filename:
            self._radar.compare(v1, v2, run_id_1, run_id_2, filename=filename)
        comparisons = []
        for ax, a1, a2 in zip(AXES, v1, v2, strict=True):
            diff = a2 - a1
            pct = (diff / a1 * 100) if a1 != 0 else 0.0
            e1 = r1.get("per_episode", [])
            e2 = r2.get("per_episode", [])
            coh1 = np.array([float(x.get("coherence", 0.5)) for x in e1])
            coh2 = np.array([float(x.get("coherence", 0.5)) for x in e2])
            from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

            mwu = _mann_whitney_u(coh1, coh2)
            comparisons.append(
                StatisticalComparison(
                    metric=ax,
                    group1_mean=a1,
                    group2_mean=a2,
                    difference=diff,
                    percent_change=pct,
                    p_value=mwu.p_value,
                    significant=mwu.significant,
                    n_group1=len(e1),
                    n_group2=len(e2),
                )
            )
        return comparisons

    def export_json(self, path: str | Path) -> None:
        with open(path, "w") as f:
            json.dump(self._runs, f, indent=2, default=str)

    def import_json(self, path: str | Path) -> None:
        with open(path) as f:
            self._runs = json.load(f)
