"""Compound Engineering Engine — unified entry point.

Integrates all compound engineering subsystems:
- ExperimentAnalytics: track and analyze overnight EVO loop results
- ExperimentScheduler: retire converged, propose next experiments  
- ExperimentRecommender: HIHO-balanced recommendations
- SessionMetricsAggregator: per-session HIHO balance tracking
- CompoundScoreWindow: execution quality trend tracking
- ErrorClassifier: structured error classification
- HealthMonitor: system health verification

Provides a single CompoundEngine class with convenience methods.
"""
from __future__ import annotations

from typing import Any


class CompoundEngine:
    """Unified compound engineering engine.

    Usage:
        engine = CompoundEngine()
        engine.record_execution("E63", delta=0.15, coherence=0.8)
        engine.record_score(0.73)
        summary = engine.get_summary()
    """

    def __init__(
        self,
        min_keeps_for_retirement: int = 10,
        cv_threshold: float = 0.05,
        score_window_size: int = 20,
    ):
        from cohezion.compound.compound_score_tracker import CompoundScoreWindow
        from cohezion.compound.experiment_scheduler import ExperimentScheduler
        from cohezion.compound.session_metrics_aggregator import SessionMetricsAggregator

        self.metrics = SessionMetricsAggregator()
        self.score_window = CompoundScoreWindow(window_size=score_window_size)
        self.scheduler = ExperimentScheduler(
            min_keeps=min_keeps_for_retirement,
            cv_threshold=cv_threshold,
        )

    def record_execution(
        self,
        experiment_label: str,
        delta: float,
        coherence: float = 0.5,
    ) -> None:
        """Record an experiment execution result."""
        self.metrics.record(experiment_label, delta, coherence)

    def record_score(self, compound_score: float) -> None:
        """Record a compound_score from ExecutionResult.metrics."""
        self.score_window.record(compound_score)

    def get_summary(self) -> dict[str, Any]:
        """Get a unified summary of the compound engineering session."""
        session = self.metrics.compute_summary()
        score = self.score_window.summary()
        sched = self.scheduler.get_schedule_summary()

        return {
            "session": session,
            "score_trend": score,
            "scheduler": sched,
            "overall_health": (
                session.get("hiho_balance", 0) >= 0.3
                and not score.get("degrading", False)
            ),
        }

    def check_and_retire(self, jsonl_path=None) -> list[str]:
        """Check for retirement candidates and return new retirees."""
        return self.scheduler.check_retirements(jsonl_path=jsonl_path)

    def get_next_experiments(self, n: int = 3) -> list[dict[str, Any]]:
        """Get recommended next experiments."""
        from cohezion.compound.experiment_recommender import recommend_next_experiments
        return recommend_next_experiments(n=n)

    def get_health(self) -> dict[str, Any]:
        """Run health checks on all compound engineering components."""
        from cohezion.compound.health_monitor import get_health_report
        return get_health_report()
