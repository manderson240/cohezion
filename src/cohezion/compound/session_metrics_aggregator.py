"""Compound session metrics aggregation with HIHO balance tracking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


__all__ = ["ExperimentRecord", "SessionMetricsAggregator"]


@dataclass
class ExperimentRecord:
    """Single experiment outcome (label, delta, and coherence score)."""

    label: str
    delta: float
    coherence: float


class SessionMetricsAggregator:
    """Track experiment outcomes and compute session-level HIHO balance score.

    Designed to be wired into overnight_evo_loop and autorun_2h to surface
    when the session has shifted from exploration to exploitation territory.
    """

    HIHO_THRESHOLD = 0.5  # Matches AutoresearchEngine.HIHO_THRESHOLD

    def __init__(self) -> None:
        self._records: list[ExperimentRecord] = []

    def record(self, experiment_label: str, delta: float, coherence: float = 0.5) -> None:
        """Record one experiment outcome."""
        self._records.append(ExperimentRecord(
            label=experiment_label, delta=delta, coherence=coherence
        ))

    def compute_summary(self) -> dict[str, Any]:
        """Compute session summary with HIHO balance and suggestions."""
        if not self._records:
            return {
                "n_experiments": 0,
                "hiho_balance": self.HIHO_THRESHOLD,
                "keep_rate": 0.0,
                "mean_delta": 0.0,
                "top_experiments": [],
            }

        n = len(self._records)
        keeps = [r for r in self._records if r.delta > 0]
        keep_rate = len(keeps) / n
        mean_delta = sum(r.delta for r in self._records) / n
        mean_coherence = sum(r.coherence for r in self._records) / n

        # HIHO balance: fraction of positive-delta experiments
        hiho_balance = len(keeps) / n

        # Top experiments by delta
        sorted_by_delta = sorted(self._records, key=lambda x: x.delta, reverse=True)
        top_experiments = [
            {"label": r.label, "delta": round(r.delta, 4), "coherence": round(r.coherence, 4)}
            for r in sorted_by_delta[:5]
        ]

        return {
            "n_experiments": n,
            "hiho_balance": round(hiho_balance, 4),
            "mean_coherence": round(mean_coherence, 4),
            "keep_rate": round(keep_rate, 4),
            "mean_delta": round(mean_delta, 4),
            "top_experiments": top_experiments,
            "mode": "exploit" if mean_coherence >= self.HIHO_THRESHOLD else "explore",
        }

    async def suggest_next(self, n: int = 3) -> list[dict[str, Any]]:
        """Use AutoresearchEngine to suggest next experiments based on session HIHO balance."""
        from cohezion.compound.autoresearch import AutoresearchEngine
        summary = self.compute_summary()
        engine = AutoresearchEngine()
        return await engine.generate_next_experiments(
            n=n,
            session_metrics={"avg_coherence": summary.get("mean_coherence", self.HIHO_THRESHOLD)},
        )
