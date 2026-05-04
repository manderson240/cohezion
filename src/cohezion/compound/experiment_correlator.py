"""Experiment correlator — detects temporal correlations between experiments.

Analyzes autoresearch.jsonl to find if one experiment's positive result
is frequently followed by another's improvement (causal vs coincidental).
Useful for detecting compound effects between experiments.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_temporal_correlation(
    records: list[dict[str, Any]],
    window: int = 3,
) -> dict[str, dict[str, float]]:
    """Compute temporal correlation: P(experiment B succeeds | experiment A recently succeeded).

    Args:
        records: Ordered list of experiment records from autoresearch.jsonl
        window: How many records back to look for preceding events

    Returns:
        Nested dict: {exp_a: {exp_b: correlation_score}} where score in [0,1]
    """
    # Build sequence of (experiment, success) pairs
    events = [
        (r.get("asi", {}).get("experiment", "unknown"), r.get("status") == "keep")
        for r in records
    ]

    # Count co-occurrences within window
    follows: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)

    for i, (exp_b, b_success) in enumerate(events):
        if not b_success:
            continue
        # Look back at window previous events
        for j in range(max(0, i - window), i):
            exp_a, a_success = events[j]
            if a_success and exp_a != exp_b:
                follows[exp_a][exp_b] += 1
                totals[exp_a] += 1

    # Compute probabilities
    correlations: dict[str, dict[str, float]] = {}
    for exp_a, followers in follows.items():
        correlations[exp_a] = {
            exp_b: count / totals[exp_a]
            for exp_b, count in followers.items()
            if count >= 2  # Minimum evidence threshold
        }

    return correlations


def find_strong_correlations(
    correlations: dict[str, dict[str, float]],
    threshold: float = 0.6,
) -> list[dict[str, Any]]:
    """Find experiment pairs with strong temporal correlation."""
    strong = []
    for exp_a, followers in correlations.items():
        for exp_b, score in followers.items():
            if score >= threshold:
                strong.append({
                    "precedes": exp_a,
                    "follows": exp_b,
                    "correlation": round(score, 4),
                })
    return sorted(strong, key=lambda x: -x["correlation"])
