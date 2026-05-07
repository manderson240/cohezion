"""Experiment analytics for overnight EVO loop results.

Reads autoresearch.jsonl and computes:
- Per-experiment keep rates and mean metrics
- Session HIHO balance
- Retirement candidates (CV < threshold)
- Top-performing experiments
"""
from __future__ import annotations

import contextlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


JSONL_PATH = Path(__file__).parent.parent.parent.parent / "autoresearch.jsonl"


def load_experiment_records(
    n: int = 1000,
    jsonl_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Load last n experiment records from autoresearch.jsonl."""
    path = jsonl_path or JSONL_PATH
    if not path.exists():
        return []

    lines = path.read_text().splitlines()[-n:]
    records = []
    for line in lines:
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            records.append(json.loads(line))
    return records


def compute_experiment_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute per-experiment statistics."""
    experiments: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "keeps": 0, "metrics": []}
    )

    for r in records:
        exp = r.get("asi", {}).get("experiment", "unknown")
        metric = float(r.get("metric", 0))
        status = r.get("status", "")
        experiments[exp]["total"] += 1
        if status == "keep":
            experiments[exp]["keeps"] += 1
            experiments[exp]["metrics"].append(metric)

    stats = {}
    for exp, data in experiments.items():
        keeps = data["metrics"]
        total = data["total"]
        keep_rate = data["keeps"] / total if total > 0 else 0.0
        mean_metric = sum(keeps) / len(keeps) if keeps else 0.0
        cv = 0.0
        if len(keeps) >= 2 and mean_metric > 0:
            cv = statistics.stdev(keeps) / mean_metric
        stats[exp] = {
            "total": total,
            "keep_rate": round(keep_rate, 4),
            "mean_metric": round(mean_metric, 4),
            "cv": round(cv, 4),
            "n_keeps": len(keeps),
        }

    return stats


def find_retirement_candidates(
    stats: dict[str, dict[str, Any]],
    min_keeps: int = 10,
    cv_threshold: float = 0.05,
) -> list[str]:
    """Identify experiments that have converged (CV < threshold after min_keeps)."""
    candidates = []
    for exp, data in stats.items():
        if data["n_keeps"] >= min_keeps and data["cv"] < cv_threshold and data["mean_metric"] > 0:
            candidates.append(exp)
    return candidates


def compute_hiho_balance(records: list[dict[str, Any]]) -> float:
    """Compute HIHO balance: fraction of keep-status records."""
    if not records:
        return 0.5
    keeps = sum(1 for r in records if r.get("status") == "keep")
    return round(keeps / len(records), 4)


def get_analytics_report(n: int = 1000) -> dict[str, Any]:
    """Generate a complete analytics report from the last n records."""
    records = load_experiment_records(n)
    stats = compute_experiment_stats(records)
    retirement_candidates = find_retirement_candidates(stats)
    hiho = compute_hiho_balance(records)

    top = sorted(
        [(exp, d["mean_metric"]) for exp, d in stats.items() if d["n_keeps"] >= 5],
        key=lambda x: -x[1],
    )[:5]

    return {
        "n_records": len(records),
        "hiho_balance": hiho,
        "n_experiments": len(stats),
        "retirement_candidates": retirement_candidates,
        "top_experiments": [{"experiment": exp, "mean_metric": m} for exp, m in top],
        "per_experiment": stats,
    }


def compute_experiment_velocity(
    records: list[dict[str, Any]],
    experiment: str,
    time_window_ms: int = 300000,  # 5 minutes
) -> float:
    """Compute experiment improvement velocity (metric units per second).

    Velocity = mean metric gain in recent window / time window duration.
    """
    now_ms = max((r.get("timestamp", 0) for r in records), default=0)
    if now_ms == 0:
        return 0.0

    cutoff_ms = now_ms - time_window_ms
    recent = [
        r for r in records
        if r.get("asi", {}).get("experiment") == experiment
        and r.get("timestamp", 0) >= cutoff_ms
        and r.get("status") == "keep"
    ]

    if not recent:
        return 0.0

    metrics = [float(r.get("metric", 0)) for r in recent]
    mean_metric = sum(metrics) / len(metrics)

    # Velocity = mean improvement / time elapsed in seconds
    duration_s = time_window_ms / 1000.0
    return round(mean_metric / duration_s, 6)  # metric/s
