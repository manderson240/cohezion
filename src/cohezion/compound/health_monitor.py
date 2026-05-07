"""Compound engineering health monitor.

Wraps the key compound invariants as health checks to surface
component availability without requiring full integration tests.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger(__name__)


def test_autoresearch_available() -> dict[str, Any]:
    """Check AutoresearchEngine is importable and generate_next_experiments works."""
    try:
        from cohezion.compound.autoresearch import AutoresearchEngine

        engine = AutoresearchEngine()
        exps = asyncio.run(engine.generate_next_experiments(n=1, session_metrics={}))
        return {"ok": True, "experiments": len(exps)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_error_classifier_available() -> dict[str, Any]:
    """Check error_classifier module is importable and functional."""
    try:
        from cohezion.compound.error_classifier import classify_error

        result = classify_error(ValueError("test"))
        return {"ok": "error_category" in result, "sample": result.get("error_category")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_session_metrics_available() -> dict[str, Any]:
    """Check SessionMetricsAggregator is importable and functional."""
    try:
        from cohezion.compound.session_metrics_aggregator import SessionMetricsAggregator

        agg = SessionMetricsAggregator()
        agg.record("test", 0.1, 0.8)
        summary = agg.compute_summary()
        return {"ok": summary.get("n_experiments") == 1}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_health_report() -> dict[str, Any]:
    """Run all health checks and return a summary report."""
    checks = {
        "autoresearch": test_autoresearch_available(),
        "error_classifier": test_error_classifier_available(),
        "session_metrics": test_session_metrics_available(),
    }
    all_ok = all(c.get("ok") for c in checks.values())
    return {
        "healthy": all_ok,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


def test_loop_visualizer_available() -> dict[str, Any]:
    """Check loop_visualizer is importable and functional."""
    try:
        from cohezion.compound.loop_visualizer import render_hiho_bar

        bar = render_hiho_bar(0.75)
        return {"ok": True, "sample": bar[:20]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_compound_engine_available() -> dict[str, Any]:
    """Check CompoundEngine is importable and functional."""
    try:
        from cohezion.compound.compound_engine import CompoundEngine

        engine = CompoundEngine()
        # Run a simple summary check (not health check to avoid circular calls)
        engine.record_execution("test", 0.1, 0.5)
        summary = engine.get_summary()
        return {"ok": summary["overall_health"] is True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_experiment_scheduler_available() -> dict[str, Any]:
    """Check ExperimentScheduler is importable and functional."""
    try:
        from cohezion.compound.experiment_scheduler import ExperimentScheduler

        sched = ExperimentScheduler()
        summary = sched.get_schedule_summary()
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_experiment_recommender_available() -> dict[str, Any]:
    """Check ExperimentRecommender is importable and functional."""
    try:
        from cohezion.compound.experiment_recommender import recommend_next_experiments

        recs = recommend_next_experiments(n=2)
        return {"ok": True, "n_recommendations": len(recs)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Re-export get_health_report to include new check
_orig_get_health_report = get_health_report


def get_health_report() -> dict[str, Any]:
    """Run all health checks and return a summary report."""
    report = _orig_get_health_report()
    report["checks"]["experiment_recommender"] = test_experiment_recommender_available()
    report["checks"]["experiment_scheduler"] = test_experiment_scheduler_available()
    report["checks"]["compound_engine"] = test_compound_engine_available()
    report["checks"]["loop_visualizer"] = test_loop_visualizer_available()
    report["healthy"] = all(c.get("ok") for c in report["checks"].values())
    return report
