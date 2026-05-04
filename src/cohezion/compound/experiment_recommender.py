"""Compound experiment recommendation engine.

Combines ExperimentAnalytics and AutoresearchEngine to recommend
next experiments based on current session state (HIHO balance,
retirement candidates, and performance trends).
"""
from __future__ import annotations

import asyncio
from typing import Any


def recommend_next_experiments(
    n: int = 3,
    jsonl_path=None,
) -> list[dict[str, Any]]:
    """Recommend n next experiments based on session analytics.

    Algorithm:
    1. Load experiment analytics from autoresearch.jsonl
    2. Identify retirement candidates (converged experiments)
    3. Use HIHO balance to determine exploitation vs exploration mode
    4. Call AutoresearchEngine.generate_next_experiments with context

    Returns:
        List of recommendation dicts with:
        - experiment_name: suggested label (e.g. "E77_adaptive_lr")
        - hypothesis: what to test
        - replaces: experiment label being replaced (if any)
        - priority: "high", "medium", or "low"
        - mode: "exploit" or "explore"
    """
    from cohezion.compound.autoresearch import AutoresearchEngine
    from cohezion.compound.experiment_analytics import (
        compute_experiment_stats,
        compute_hiho_balance,
        find_retirement_candidates,
        load_experiment_records,
    )

    records = load_experiment_records(n=500, jsonl_path=jsonl_path)
    stats = compute_experiment_stats(records)
    retired = find_retirement_candidates(stats, min_keeps=10)
    hiho = compute_hiho_balance(records)

    engine = AutoresearchEngine()
    proposals = asyncio.run(engine.generate_next_experiments(
        n=n,
        session_metrics={"avg_coherence": hiho},
        retired_labels=retired[:n],
    ))

    recommendations = []
    for i, p in enumerate(proposals):
        recommendations.append({
            "experiment_name": f"E{77 + i}_{p.get('parameter', p['hypothesis'].split()[0].lower()[:15])}",
            "hypothesis": p["hypothesis"],
            "replaces": p.get("replaces"),
            "priority": p.get("priority", "medium"),
            "mode": p["mode"],
        })

    return recommendations


def get_session_recommendation_summary() -> dict[str, Any]:
    """Get a full recommendation summary for the current session."""
    from cohezion.compound.experiment_analytics import get_analytics_report

    analytics = get_analytics_report(n=2000)
    recommendations = recommend_next_experiments(n=3)

    return {
        "hiho_balance": analytics["hiho_balance"],
        "retirement_candidates": analytics["retirement_candidates"],
        "recommendations": recommendations,
        "mode": "exploit" if analytics["hiho_balance"] >= 0.5 else "explore",
    }
