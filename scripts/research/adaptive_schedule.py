"""
adaptive_schedule.py — compound engineering core.

Analyzes autoresearch history and dynamically generates the optimal next
experiment schedule. Implements the Strategy Pivot Protocol automatically:
- Retire experiments with <5% keep rate after N>=10 runs
- Upsample experiments with high mean_delta
- Introduce novelty experiments when ceiling is detected (stdev=0)

Integrates: timeit (measurement), autodata (history analysis),
            autoharness (template validation), autoresearch (logging)

Usage:
    from scripts.research.adaptive_schedule import AdaptiveSchedule
    schedule = AdaptiveSchedule.from_jsonl('autoresearch_overnight.jsonl')
    next_exps = schedule.recommend(n=4)
"""

from __future__ import annotations

import json
import timeit
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import Any


@dataclass
class ExperimentStats:
    name: str
    n: int = 0
    keep_count: int = 0
    deltas: list[float] = field(default_factory=list)

    @property
    def keep_frac(self) -> float:
        return self.keep_count / self.n if self.n > 0 else 0.0

    @property
    def mean_delta(self) -> float:
        return mean(self.deltas) if self.deltas else 0.0

    @property
    def max_delta(self) -> float:
        return max(self.deltas) if self.deltas else 0.0

    @property
    def delta_stdev(self) -> float:
        return stdev(self.deltas) if len(self.deltas) > 1 else 0.0

    @property
    def expected_value(self) -> float:
        """keep_frac * mean_delta — primary ranking metric."""
        return self.keep_frac * self.mean_delta

    @property
    def is_at_ceiling(self) -> bool:
        """True if delta is deterministic (stdev=0) and n>=5."""
        return self.n >= 5 and self.delta_stdev < 1e-6 and self.mean_delta > 0

    @property
    def should_retire(self) -> bool:
        """True if keep_frac < 5% with enough samples to be confident."""
        return self.n >= 10 and self.keep_frac < 0.05

    def novelty_bonus(self, global_max_delta: float) -> float:
        """Bonus for experiments that haven't been explored much."""
        if self.n < 3:
            return 0.5
        if self.is_at_ceiling:
            return -0.1
        if self.n < 10:
            return 0.1
        return 0.0


class AdaptiveSchedule:
    """Builds optimal experiment schedule from autoresearch history."""

    def __init__(self, stats: dict[str, ExperimentStats]):
        self.stats = stats
        self._analysis_ms: float = 0.0

    @classmethod
    def from_jsonl(cls, jsonl_path: Path | str) -> AdaptiveSchedule:
        """Load experiment history from JSONL and compute stats."""
        t0 = timeit.default_timer()
        path = Path(jsonl_path)
        by_exp: dict[str, ExperimentStats] = defaultdict(lambda: ExperimentStats(name=""))

        if not path.exists():
            return cls({})

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                exp = rec.get("experiment", rec.get("label", ""))
                if not exp or exp.startswith("FINDING_"):
                    continue
                delta = float(rec.get("delta", rec.get("metric", 0.0)))
                keep = rec.get("keep", rec.get("status", "discard"))
                if exp not in by_exp:
                    by_exp[exp] = ExperimentStats(name=exp)
                s = by_exp[exp]
                s.n += 1
                s.deltas.append(delta)
                if keep in ("keep", "KEEP"):
                    s.keep_count += 1

        result = cls(dict(by_exp))
        result._analysis_ms = (timeit.default_timer() - t0) * 1000
        return result

    def recommend(self, n: int = 4) -> list[tuple[str, dict[str, Any]]]:
        """Return top-N recommended experiments with reasoning."""
        t0 = timeit.default_timer()
        active = {k: v for k, v in self.stats.items() if not v.should_retire}

        if not active:
            return []

        global_max = max((s.max_delta for s in active.values()), default=1.0)

        scored = []
        for name, s in active.items():
            bonus = s.novelty_bonus(global_max)
            score = s.expected_value + bonus
            scored.append((score, name, s))

        scored.sort(reverse=True)

        recommendations = []
        for score, name, s in scored[:n]:
            reasoning = {
                "n": s.n,
                "keep_frac": round(s.keep_frac, 3),
                "mean_delta": round(s.mean_delta, 5),
                "expected_value": round(s.expected_value, 5),
                "is_at_ceiling": s.is_at_ceiling,
                "score": round(score, 5),
                "reason": (
                    "ceiling reached — minimal runs needed"
                    if s.is_at_ceiling
                    else "high expected value"
                    if s.expected_value > 0.1
                    else "underexplored — novelty bonus"
                    if s.n < 3
                    else "moderate performer"
                ),
            }
            recommendations.append((name, reasoning))

        return recommendations

    def summary(self) -> dict:
        """Return analysis summary for logging."""
        active = [s for s in self.stats.values() if not s.should_retire]
        retired = [s for s in self.stats.values() if s.should_retire]
        at_ceiling = [s for s in active if s.is_at_ceiling]
        return {
            "total_experiments": len(self.stats),
            "active": len(active),
            "retired": len(retired),
            "at_ceiling": len(at_ceiling),
            "total_runs": sum(s.n for s in self.stats.values()),
            "total_keeps": sum(s.keep_count for s in self.stats.values()),
            "analysis_ms": round(self._analysis_ms, 2),
            "top_3": [
                {"name": s.name, "ev": round(s.expected_value, 4)}
                for s in sorted(active, key=lambda x: -x.expected_value)[:3]
            ],
            "retired_experiments": [s.name for s in retired],
        }

    def pivot_check(self) -> dict:
        """Check if a strategy pivot is needed."""
        at_ceiling = [s for s in self.stats.values() if s.is_at_ceiling]
        if len(at_ceiling) < 3:
            return {"pivot_needed": False, "reason": "not enough ceiling experiments"}

        deltas = [s.max_delta for s in at_ceiling]
        if max(deltas) - min(deltas) < 0.001:
            return {
                "pivot_needed": True,
                "reason": f"{len(at_ceiling)} experiments at same ceiling {max(deltas):.4f}",
                "recommendation": "Try serial composition or fundamentally different approach",
                "ceiling_value": round(max(deltas), 4),
            }
        return {"pivot_needed": False, "reason": "ceiling experiments have different values"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Adaptive experiment schedule recommender")
    parser.add_argument("jsonl", nargs="?", default="autoresearch_overnight.jsonl")
    parser.add_argument("--n", type=int, default=4, help="Number of recommendations")
    args = parser.parse_args()

    ROOT = Path(__file__).parent.parent.parent
    jsonl_path = ROOT / args.jsonl

    t_total = timeit.default_timer()
    schedule = AdaptiveSchedule.from_jsonl(jsonl_path)

    print(f"Loaded {jsonl_path.name} in {schedule._analysis_ms:.1f}ms")
    summary = schedule.summary()
    print(
        f"  Total runs: {summary['total_runs']}, Active: {summary['active']}, Retired: {summary['retired']}"
    )
    print(
        f"  Keep rate: {summary['total_keeps']}/{summary['total_runs']} "
        f"({summary['total_keeps'] / max(1, summary['total_runs']):.1%})"
    )
    if summary["retired_experiments"]:
        print(f"  Retired: {', '.join(summary['retired_experiments'][:5])}")

    pivot = schedule.pivot_check()
    if pivot["pivot_needed"]:
        print(f"\n⚠  PIVOT NEEDED: {pivot['reason']}")
        print(f"   Recommendation: {pivot['recommendation']}")

    print(f"\nTop {args.n} recommended experiments:")
    for name, r in schedule.recommend(n=args.n):
        print(
            f"  {name:<25} ev={r['expected_value']:>+.4f} keep={r['keep_frac']:.0%} "
            f"n={r['n']:>4}  [{r['reason']}]"
        )

    total_ms = (timeit.default_timer() - t_total) * 1000
    print(f"\nAnalysis: {total_ms:.1f}ms total")
