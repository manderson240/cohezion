"""CapabilityScorecard - Track and compare EVO capability metrics.

6-axis capability model:
    1. Coherence Amplitude - Peak HIHO stability reached
    2. Phase Locking - Synchronization with vacuum oscillations
    3. Exotic Charge Lifetime - Duration of exotic vacuum excitation
    4. Orbit Quality - Stability of TRIUNE structure orbits
    5. TRIUNE Balance - Doer/Thinker/Knower equilibrium
    6. Recovery Basin Radius - Size of stability well accessible

Statistical comparison between swarm-advisor and self-supervised learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np


if TYPE_CHECKING:
    import pandas as pd
    from plotly.graph_objects import Figure


AXES = (
    "coherence_amplitude",
    "phase_locking",
    "exotic_charge_lifetime",
    "orbit_quality",
    "triune_balance",
    "recovery_basin_radius",
)

AXIS_LABELS = {
    "coherence_amplitude": "Coherence Amplitude",
    "phase_locking": "Phase Locking",
    "exotic_charge_lifetime": "Exotic Charge Lifetime",
    "orbit_quality": "Orbit Quality",
    "triune_balance": "TRIUNE Balance",
    "recovery_basin_radius": "Recovery Basin Radius",
}


@dataclass
class StatisticalComparison:
    """Statistical comparison between two learning paradigms."""

    delta_capability: dict[str, float]
    p_values: dict[str, float]
    effect_sizes: dict[str, float]
    sample_size_swarm: int
    sample_size_self_supervised: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of comparison results.
        """
        return {
            "delta_capability": self.delta_capability,
            "p_values": self.p_values,
            "effect_sizes": self.effect_sizes,
            "sample_size_swarm": self.sample_size_swarm,
            "sample_size_self_supervised": self.sample_size_self_supervised,
        }


class CapabilityScorecard:
    """Track and compare EVO capability metrics across 6 axes.

    Provides longitudinal tracking, radar visualization, and statistical
    comparison between swarm-advisor and self-supervised learning paradigms.
    """

    def __init__(self) -> None:
        """Initialize CapabilityScorecard with 6 capability axes."""
        self.axes = list(AXES)
        self.axis_labels = AXIS_LABELS

    def _validate_vector(self, capability_vector: dict[str, float]) -> bool:
        """Validate capability vector has correct keys and values.

        Args:
            capability_vector: Dictionary of capability values.

        Returns:
            True if valid, False otherwise.
        """
        if not isinstance(capability_vector, dict):
            return False

        for key in self.axes:
            if key not in capability_vector:
                return False
            value = capability_vector[key]
            if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
                return False

        return True

    def generate_radar_chart(self, capability_vector: dict[str, float]) -> Figure:
        """Generate radar chart for capability vector.

        Args:
            capability_vector: Dictionary of 6 capability values (0.0 to 1.0).

        Returns:
            Plotly Figure with radar chart visualization.
        """
        if not self._validate_vector(capability_vector):
            raise ValueError("Invalid capability vector")

        try:
            import plotly.graph_objects as go

            values = [capability_vector[axis] for axis in self.axes]
            labels = [self.axis_labels[axis] for axis in self.axes]

            fig = go.Figure(
                data=go.Scatterpolar(
                    r=[*values, values[0]],
                    theta=[*labels, labels[0]],
                    fill="toself",
                    fillcolor="rgba(31, 119, 180, 0.3)",
                    line_color="rgba(31, 119, 180, 0.8)",
                    marker={"size": 8},
                )
            )

            fig.update_layout(
                polar={"radialaxis": {"visible": True, "range": [0, 1]}},
                showlegend=False,
                title={"text": "EVO Capability Scorecard", "x": 0.5},
            )

            return fig

        except ImportError:
            return self._generate_numpy_radar_fallback(capability_vector)

    def _generate_numpy_radar_fallback(self, capability_vector: dict[str, float]) -> Figure:
        """Generate matplotlib figure when plotly unavailable.

        Args:
            capability_vector: Dictionary of 6 capability values.

        Returns:
            Figure object (matplotlib Figure if plotly unavailable).
        """
        import matplotlib.pyplot as plt

        values = [capability_vector[axis] for axis in self.axes]
        labels = [self.axis_labels[axis] for axis in self.axes]

        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        values_plot = [*values, values[0]]
        angles_plot = [*angles, angles[0]]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
        ax.plot(angles_plot, values_plot, "o-", linewidth=2, color="steelblue")
        ax.fill(angles_plot, values_plot, alpha=0.3, color="steelblue")
        ax.set_xticks(angles)
        ax.set_xticklabels(labels, size=10)
        ax.set_ylim(0, 1)
        ax.set_title("EVO Capability Scorecard", size=14, pad=20)
        plt.close(fig)

        class Figure:
            def __init__(self, mpl_fig):
                self._mpl_fig = mpl_fig
                self.data = [type("obj", (), {"theta": labels, "r": values})()]

        return Figure(fig)

    def track_longitudinal(self, checkpoints: list[dict[str, Any]]) -> pd.DataFrame:
        """Track capability evolution across episodes.

        Args:
            checkpoints: List of checkpoint dicts with episode, capability_vector,
                       checkpoint_path, and timestamp.

        Returns:
            DataFrame with episode, capability vectors, and checkpoint paths.
        """
        import pandas as pd

        if not checkpoints:
            cols = ["episode", *self.axes, "checkpoint_path", "timestamp"]
            return pd.DataFrame(columns=cols)

        rows = []
        for ckpt in checkpoints:
            episode = ckpt.get("episode", 0)
            capability_vector = ckpt.get("capability_vector", {})
            row = {"episode": episode}
            for axis in self.axes:
                row[axis] = capability_vector.get(axis, 0.0)
            row["checkpoint_path"] = ckpt.get("checkpoint_path", "")
            row["timestamp"] = ckpt.get("timestamp", "")
            rows.append(row)

        return pd.DataFrame(rows)

    def compare_swarm_vs_selfsupervised(
        self,
        swarm_results: list[dict[str, Any]],
        self_supervised_results: list[dict[str, Any]],
    ) -> StatisticalComparison:
        """Compare swarm-advisor vs self-supervised learning capabilities.

        Args:
            swarm_results: List of results from swarm advisor runs.
            self_supervised_results: List of results from self-supervised runs.

        Returns:
            StatisticalComparison with delta capability, p-values, and effect sizes.
        """
        delta_capability: dict[str, float] = {}
        p_values: dict[str, float] = {}
        effect_sizes: dict[str, float] = {}

        swarm_vectors = [r["capability_vector"] for r in swarm_results]
        ss_vectors = [r["capability_vector"] for r in self_supervised_results]

        for axis in self.axes:
            swarm_values = [v.get(axis, 0.0) for v in swarm_vectors]
            ss_values = [v.get(axis, 0.0) for v in ss_vectors]

            swarm_mean = np.mean(swarm_values) if swarm_values else 0.0
            ss_mean = np.mean(ss_values) if ss_values else 0.0

            delta_capability[axis] = swarm_mean - ss_mean

            if len(swarm_values) > 1 and len(ss_values) > 1:
                swarm_std = np.std(swarm_values, ddof=1)
                ss_std = np.std(ss_values, ddof=1)

                pooled_std = (
                    np.sqrt(
                        ((len(swarm_values) - 1) * swarm_std**2 + (len(ss_values) - 1) * ss_std**2)
                        / (len(swarm_values) + len(ss_values) - 2)
                    )
                    if (len(swarm_values) + len(ss_values) - 2) > 0
                    else 1e-8
                )

                effect_sizes[axis] = (swarm_mean - ss_mean) / pooled_std if pooled_std > 1e-8 else 0.0

                t_stat = (
                    (swarm_mean - ss_mean) / (pooled_std * np.sqrt(1 / len(swarm_values) + 1 / len(ss_values)))
                    if pooled_std > 1e-8
                    else 0.0
                )

                df = len(swarm_values) + len(ss_values) - 2
                p_values[axis] = self._t_dist_p_value(t_stat, df) if df > 0 else 0.5
            else:
                effect_sizes[axis] = 0.0
                p_values[axis] = 0.5

        return StatisticalComparison(
            delta_capability=delta_capability,
            p_values=p_values,
            effect_sizes=effect_sizes,
            sample_size_swarm=len(swarm_results),
            sample_size_self_supervised=len(self_supervised_results),
        )

    def _t_dist_p_value(self, t_stat: float, df: int) -> float:
        """Calculate two-tailed p-value from t-statistic.

        Args:
            t_stat: T-statistic value.
            df: Degrees of freedom.

        Returns:
            Two-tailed p-value.
        """
        if df <= 0:
            return 0.5

        x = df / (df + t_stat * t_stat)
        p_value = 0.5 * x ** (df / 2)

        return min(1.0, max(0.0, p_value))

    def generate_3d_morphospace_trajectory(self, checkpoints: list[dict[str, Any]]) -> Figure:
        """Generate 3D morphospace trajectory visualization.

        Uses PCA-like projection from 6D capability space to 3D for visualization.

        Args:
            checkpoints: List of checkpoints with capability vectors.

        Returns:
            Plotly Figure with 3D trajectory.
        """
        if not checkpoints:
            raise ValueError("No checkpoints provided")

        df = self.track_longitudinal(checkpoints)

        capability_matrix = df[self.axes].values

        _u, _s, vt = np.linalg.svd(capability_matrix - capability_matrix.mean(axis=0), full_matrices=False)

        projection_3d = capability_matrix @ vt[:3].T

        try:
            import plotly.graph_objects as go

            fig = go.Figure(
                data=[
                    go.Scatter3d(
                        x=projection_3d[:, 0],
                        y=projection_3d[:, 1],
                        z=projection_3d[:, 2],
                        mode="lines+markers",
                        line={"color": df["episode"].values, "colorscale": "Viridis", "width": 4},
                        marker={"size": 8, "color": df["episode"].values, "colorscale": "Viridis"},
                        text=[f"Episode {e}" for e in df["episode"]],
                        hoverinfo="text+x+y+z",
                    )
                ]
            )

            fig.update_layout(
                title={"text": "3D Morphospace Trajectory", "x": 0.5},
                scene={
                    "xaxis_title": "PC1",
                    "yaxis_title": "PC2",
                    "zaxis_title": "PC3",
                },
                showlegend=False,
            )

            return fig

        except ImportError:
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection="3d")

            episodes = df["episode"].values
            colors = plt.cm.viridis((episodes - episodes.min()) / (episodes.max() - episodes.min() + 1e-8))
            for i in range(len(episodes) - 1):
                ax.plot(
                    projection_3d[i : i + 2, 0],
                    projection_3d[i : i + 2, 1],
                    projection_3d[i : i + 2, 2],
                    "-",
                    color=colors[i],
                    linewidth=2,
                )
            ax.scatter(
                projection_3d[:, 0],
                projection_3d[:, 1],
                projection_3d[:, 2],
                c=colors,
                s=50,
                zorder=5,
            )

            ax.set_xlabel("PC1")
            ax.set_ylabel("PC2")
            ax.set_zlabel("PC3")
            ax.set_title("3D Morphospace Trajectory")
            plt.close(fig)

            class Figure:
                def __init__(self, mpl_fig):
                    self._mpl_fig = mpl_fig
                    self.data = [type("obj", (), {"x": projection_3d[:, 0]})()]

            return Figure(fig)
