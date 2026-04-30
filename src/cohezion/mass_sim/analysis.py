"""Anthropic-style analysis of mass simulation results.

Computes safety alignment, convergence, diversity, anomaly, and scaling metrics.
All computation is numpy-based (no heavy dependencies).
"""

from __future__ import annotations

import logging
import math

import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cohezion.mass_sim.config import UniverseResult


logger = logging.getLogger(__name__)


class SimulationAnalyzer:
    """Compute Anthropic-style insights from mass simulation results."""

    def analyze_all(
        self,
        results: list[UniverseResult],
        coherence_bounds: tuple[float, float] = (0.3, 0.7),
    ) -> dict:
        """Produce comprehensive insights across all universes.

        Returns
        -------
        dict
            Nested dict with safety, convergence, diversity, anomaly, scaling sections.
        """
        if not results:
            return {"error": "No results to analyze"}

        insights: dict = {}

        # 1. Safety Alignment
        insights["safety"] = self._safety_metrics(results, coherence_bounds)

        # 2. Convergence Analysis
        insights["convergence"] = self._convergence_metrics(results)

        # 3. Diversity Analysis
        insights["diversity"] = self._diversity_metrics(results)

        # 4. Universe Stability Ranking
        insights["universe_ranking"] = self._universe_ranking(results)

        # 5. Anomaly Detection
        insights["anomalies"] = self._anomaly_detection(results)

        # 6. Performance
        insights["performance"] = self._performance_metrics(results)

        return insights

    def _safety_metrics(
        self,
        results: list[UniverseResult],
        bounds: tuple[float, float],
    ) -> dict:
        """Safety alignment: what fraction of agents stay within HIHO bounds."""
        final_within = []
        coherence_violations = 0
        total_checkpoints = 0

        for r in results:
            final_pct = r.final_stats.get("pct_within_bounds", 0)
            final_within.append(final_pct)

            # Check checkpoint history for violations
            for ckpt in r.checkpoints:
                total_checkpoints += 1
                if ckpt.stats.get("pct_within_bounds", 1.0) < bounds[0]:
                    coherence_violations += 1

        return {
            "mean_final_within_bounds": float(np.mean(final_within)) if final_within else 0,
            "min_final_within_bounds": float(np.min(final_within)) if final_within else 0,
            "checkpoint_violation_rate": (coherence_violations / max(total_checkpoints, 1)),
            "bounds": list(bounds),
        }

    def _convergence_metrics(self, results: list[UniverseResult]) -> dict:
        """How fast do universes converge toward HIHO 0.5 stability."""
        convergence_rates = []

        for r in results:
            if len(r.checkpoints) < 2:
                continue

            # Extract coherence trajectory
            epochs = [c.epoch for c in r.checkpoints]
            coherences = [c.stats.get("mean_coherence", 0.5) for c in r.checkpoints]

            # Simple convergence metric: final - initial normalized by epochs
            initial_c = coherences[0]
            final_c = coherences[-1]
            total_e = epochs[-1] if epochs else 1

            # Rate: how much closer to 0.5 per 1000 epochs
            initial_dist = abs(initial_c - 0.5)
            final_dist = abs(final_c - 0.5)
            if initial_dist > 0.01 and total_e > 0:
                rate = (initial_dist - final_dist) / (total_e / 1000)
            else:
                rate = 0.0

            convergence_rates.append(
                {
                    "universe": r.universe_id,
                    "rate_per_1k_epochs": round(rate, 6),
                    "initial_coherence": round(initial_c, 4),
                    "final_coherence": round(final_c, 4),
                }
            )

        # Sort by rate descending
        convergence_rates.sort(key=lambda x: x["rate_per_1k_epochs"], reverse=True)

        rates_only = [c["rate_per_1k_epochs"] for c in convergence_rates]
        return {
            "mean_rate": float(np.mean(rates_only)) if rates_only else 0,
            "fastest_universe": convergence_rates[0] if convergence_rates else None,
            "slowest_universe": convergence_rates[-1] if convergence_rates else None,
            "all_rates": convergence_rates[:10],  # Top 10
        }

    def _diversity_metrics(self, results: list[UniverseResult]) -> dict:
        """Measure population diversity in final states."""
        norm_stds = []
        mean_coherences = []

        for r in results:
            stats = r.final_stats
            dim_stds = stats.get("dim_stds", [])
            if dim_stds:
                norm_stds.append(float(np.mean(dim_stds)))
            mean_coherences.append(stats.get("mean_coherence", 0))

        # Effective dimensionality approximation from dim_stds
        # Dimensions with high std carry more information
        effective_dims = []
        for r in results:
            stds = r.final_stats.get("dim_stds", [])
            if stds:
                stds_arr = np.array(stds)
                total_var = np.sum(stds_arr**2)
                if total_var > 0:
                    # Shannon entropy of normalized variance distribution
                    probs = (stds_arr**2) / total_var
                    probs = probs[probs > 1e-10]
                    eff_dim = math.exp(-np.sum(probs * np.log(probs)))
                    effective_dims.append(eff_dim)

        return {
            "mean_dim_std": float(np.mean(norm_stds)) if norm_stds else 0,
            "coherence_spread": float(np.std(mean_coherences)) if mean_coherences else 0,
            "mean_effective_dimensionality": (
                float(np.mean(effective_dims)) if effective_dims else 0
            ),
        }

    def _universe_ranking(self, results: list[UniverseResult]) -> list[dict]:
        """Rank universes by stability (mean final coherence near 0.5)."""
        ranking = []
        for r in results:
            final_c = r.final_stats.get("mean_coherence", 0)
            stability = 1.0 - abs(final_c - 0.5) * 2  # 1.0 at 0.5, 0.0 at 0 or 1
            ranking.append(
                {
                    "universe": r.universe_id,
                    "seed": r.seed,
                    "stability_score": round(stability, 4),
                    "mean_coherence": round(final_c, 4),
                    "within_bounds_pct": round(r.final_stats.get("pct_within_bounds", 0), 4),
                    "elapsed_s": round(r.elapsed_seconds, 2),
                }
            )

        ranking.sort(key=lambda x: x["stability_score"], reverse=True)
        return ranking

    def _anomaly_detection(self, results: list[UniverseResult]) -> dict:
        """Detect anomalous universes (outliers in final metrics)."""
        coherences = [r.final_stats.get("mean_coherence", 0.5) for r in results]
        if len(coherences) < 3:
            return {"anomalies": [], "threshold": "insufficient data"}

        mean_c = float(np.mean(coherences))
        std_c = float(np.std(coherences))

        anomalies = []
        for r, c in zip(results, coherences, strict=True):
            if std_c > 0 and abs(c - mean_c) > 2 * std_c:
                anomalies.append(
                    {
                        "universe": r.universe_id,
                        "coherence": round(c, 4),
                        "z_score": round((c - mean_c) / std_c, 2),
                    }
                )

        return {
            "anomaly_count": len(anomalies),
            "population_mean": round(mean_c, 4),
            "population_std": round(std_c, 4),
            "anomalies": anomalies,
        }

    def _performance_metrics(self, results: list[UniverseResult]) -> dict:
        """Throughput and timing statistics."""
        total_agent_epochs = sum(r.n_agents * r.n_epochs for r in results)
        total_time = sum(r.elapsed_seconds for r in results)
        throughput = total_agent_epochs / max(total_time, 0.001)

        return {
            "total_agent_epochs": total_agent_epochs,
            "total_wall_time_s": round(total_time, 2),
            "throughput_agent_epochs_per_sec": round(throughput, 0),
            "universes_completed": len(results),
            "mean_universe_time_s": round(total_time / max(len(results), 1), 2),
        }
