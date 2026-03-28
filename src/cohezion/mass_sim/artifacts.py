"""Multimodal artifact generation from simulation results.

Generates matplotlib visualizations and stores references.
Designed for headless operation (Agg backend).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from cohezion.mass_sim.config import SimulationReport, UniverseResult


logger = logging.getLogger(__name__)


def _ensure_matplotlib():
    """Import matplotlib with Agg backend for headless operation."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


class ArtifactGenerator:
    """Generate visual artifacts from simulation results."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generated: list[str] = []

    def generate_universe_artifacts(self, result: UniverseResult) -> list[Path]:
        """Generate per-universe visualizations."""
        artifacts = []
        try:
            artifacts.append(self._coherence_timeline(result))
            artifacts.append(self._norm_evolution(result))
        except Exception as e:
            logger.warning(f"Artifact generation failed for {result.universe_id}: {e}")
        return [a for a in artifacts if a is not None]

    def generate_report_artifacts(self, report: SimulationReport) -> list[Path]:
        """Generate cross-universe visualizations."""
        artifacts = []
        try:
            if report.universe_results:
                artifacts.append(self._stability_ranking(report))
                artifacts.append(self._convergence_overview(report))
                artifacts.append(self._summary_json(report))
        except Exception as e:
            logger.warning(f"Report artifact generation failed: {e}")
        return [a for a in artifacts if a is not None]

    def _coherence_timeline(self, result: UniverseResult) -> Path | None:
        """Plot coherence evolution over epochs for one universe."""
        if not result.checkpoints:
            return None

        plt = _ensure_matplotlib()

        epochs = [c.epoch for c in result.checkpoints]
        coherences = [c.stats.get("mean_coherence", 0) for c in result.checkpoints]
        within_bounds = [c.stats.get("pct_within_bounds", 0) for c in result.checkpoints]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

        ax1.plot(epochs, coherences, "b-", linewidth=1.5, label="Mean Coherence")
        ax1.axhline(y=0.5, color="g", linestyle="--", alpha=0.5, label="HIHO Target")
        ax1.fill_between(epochs, 0.3, 0.7, alpha=0.1, color="green", label="Bounds")
        ax1.set_ylabel("Coherence")
        ax1.set_title(f"Universe {result.universe_id} (seed={result.seed})")
        ax1.legend(fontsize=8)
        ax1.set_ylim(0, 1)

        ax2.plot(epochs, within_bounds, "r-", linewidth=1.5)
        ax2.set_ylabel("% Within Bounds")
        ax2.set_xlabel("Epoch")
        ax2.set_ylim(0, 1)

        plt.tight_layout()
        path = self.output_dir / f"{result.universe_id}_coherence.png"
        fig.savefig(path, dpi=100)
        plt.close(fig)
        self.generated.append(str(path))
        return path

    def _norm_evolution(self, result: UniverseResult) -> Path | None:
        """Plot latent norm evolution."""
        if not result.checkpoints:
            return None

        plt = _ensure_matplotlib()

        epochs = [c.epoch for c in result.checkpoints]
        norms = [c.stats.get("mean_norm", 0) for c in result.checkpoints]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(epochs, norms, "m-", linewidth=1.5)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Mean L2 Norm")
        ax.set_title(f"Latent Norm - {result.universe_id}")
        plt.tight_layout()

        path = self.output_dir / f"{result.universe_id}_norm.png"
        fig.savefig(path, dpi=100)
        plt.close(fig)
        self.generated.append(str(path))
        return path

    def _stability_ranking(self, report: SimulationReport) -> Path | None:
        """Bar chart of universe stability scores."""
        ranking = report.insights.get("universe_ranking", [])
        if not ranking:
            return None

        plt = _ensure_matplotlib()

        # Top 20 for readability
        top = ranking[:20]
        names = [r["universe"].replace("universe_", "U") for r in top]
        scores = [r["stability_score"] for r in top]

        fig, ax = plt.subplots(figsize=(12, 5))
        colors = ["green" if s > 0.8 else "orange" if s > 0.5 else "red" for s in scores]
        ax.barh(names, scores, color=colors)
        ax.set_xlabel("Stability Score (1.0 = perfect HIHO)")
        ax.set_title(f"Universe Stability Ranking ({report.run_id})")
        ax.set_xlim(0, 1)
        ax.invert_yaxis()
        plt.tight_layout()

        path = self.output_dir / f"{report.run_id}_stability_ranking.png"
        fig.savefig(path, dpi=100)
        plt.close(fig)
        self.generated.append(str(path))
        return path

    def _convergence_overview(self, report: SimulationReport) -> Path | None:
        """Scatter: initial coherence vs final coherence per universe."""
        results = report.universe_results
        if not results:
            return None

        plt = _ensure_matplotlib()

        initial = [r.initial_stats.get("mean_coherence", 0.5) for r in results]
        final = [r.final_stats.get("mean_coherence", 0.5) for r in results]

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(initial, final, alpha=0.6, s=30)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.3, label="No change")
        ax.axhline(y=0.5, color="g", linestyle=":", alpha=0.5, label="HIHO target")
        ax.axvline(x=0.5, color="g", linestyle=":", alpha=0.5)
        ax.set_xlabel("Initial Mean Coherence")
        ax.set_ylabel("Final Mean Coherence")
        ax.set_title(f"Convergence Overview ({len(results)} universes)")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend()
        plt.tight_layout()

        path = self.output_dir / f"{report.run_id}_convergence.png"
        fig.savefig(path, dpi=100)
        plt.close(fig)
        self.generated.append(str(path))
        return path

    def _summary_json(self, report: SimulationReport) -> Path | None:
        """Write JSON summary of the full report."""
        path = self.output_dir / f"{report.run_id}_summary.json"
        summary = report.summary_dict()
        with open(path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        self.generated.append(str(path))
        return path
