"""Offline skill bench evaluation (Qubot-inspired).

Runs a fixed set of prompt fixtures through FailureAttributor to classify
failure patterns by skill and difficulty, producing a metrics table before
any context-layer changes are deployed.

Modelled after Qubot's offline evaluation that ran before deploying vault
context changes — catching regressions in attribution accuracy.

Usage:
    uv run python scripts/eval/bench_skills.py
    uv run python scripts/eval/bench_skills.py --fixture path/to/bench.json
    uv run python scripts/eval/bench_skills.py --json   # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Default fixture (embedded — no external file needed to run)
# ---------------------------------------------------------------------------

_DEFAULT_FIXTURES: list[dict[str, Any]] = [
    # format failures
    {
        "id": "fmt-001",
        "skill": "COMPOUND_EXECUTOR",
        "difficulty": "easy",
        "output": '{"role": "PRODUCER"',
        "metrics": {"anomaly_score": 0.8, "output_validation_failed": True,
                    "output_validation_error": "JSON parse error at position 18: Expecting ','"},
        "decision_paths": ["vault/patterns/domains/compound/executor_pattern.md"],
        "expected_category": "format",
    },
    {
        "id": "fmt-002",
        "skill": "SYSTEM_GUARDRAILS",
        "difficulty": "easy",
        "output": "[{broken json",
        "metrics": {"anomaly_score": 0.9, "output_validation_failed": True,
                    "output_validation_error": "JSON parse error at position 1: Expecting value"},
        "decision_paths": [],
        "expected_category": "format",
    },
    # cascading failures
    {
        "id": "cas-001",
        "skill": "TRAJECTORY_SEARCH",
        "difficulty": "medium",
        "output": "",
        "metrics": {"anomaly_score": 0.95},
        "decision_paths": ["vault/patterns/domains/search/trajectory.md"],
        "expected_category": "cascading",
    },
    {
        "id": "cas-002",
        "skill": "FLUME_VAE",
        "difficulty": "medium",
        "output": "err",
        "metrics": {"anomaly_score": 0.85},
        "decision_paths": [],
        "expected_category": "cascading",
    },
    # retrieval failures
    {
        "id": "ret-001",
        "skill": "KNOWLEDGE_BRIDGE",
        "difficulty": "medium",
        "output": "No relevant context was found for the provided query.",
        "metrics": {"anomaly_score": 0.75},
        "decision_paths": [],
        "expected_category": "retrieval",
    },
    {
        "id": "ret-002",
        "skill": "SKILL_REFINER",
        "difficulty": "hard",
        "output": "Could not locate matching vault patterns for this task type.",
        "metrics": {"anomaly_score": 0.7},
        "decision_paths": [],
        "expected_category": "retrieval",
    },
    # reasoning failures
    {
        "id": "rea-001",
        "skill": "COMPOUND_EXECUTOR",
        "difficulty": "hard",
        "output": '{"result": "42", "confidence": 0.1, "reasoning": "insufficient context"}',
        "metrics": {"anomaly_score": 0.75},
        "decision_paths": ["vault/patterns/domains/compound/guidance.md"],
        "expected_category": "reasoning",
    },
    {
        "id": "rea-002",
        "skill": "REQUEST_ALIGNMENT",
        "difficulty": "hard",
        "output": "The request appears to be related to data processing but I cannot determine the specific intent.",
        "metrics": {"anomaly_score": 0.6},
        "decision_paths": ["vault/decisions/cohezion/inflection_001.md"],
        "expected_category": "reasoning",
    },
    # healthy executions (should produce no attribution)
    {
        "id": "ok-001",
        "skill": "COMPOUND_EXECUTOR",
        "difficulty": "easy",
        "output": '{"result": "success", "confidence": 0.95}',
        "metrics": {"anomaly_score": 0.05},
        "decision_paths": ["vault/patterns/domains/compound/executor_pattern.md"],
        "expected_category": None,
    },
    {
        "id": "ok-002",
        "skill": "SKILL_REFINER",
        "difficulty": "easy",
        "output": "Skill refinement completed. Appended learning signal to PRIME file.",
        "metrics": {"anomaly_score": 0.1},
        "decision_paths": ["vault/decisions/cohezion/inflection_999.md"],
        "expected_category": None,
    },
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class BenchResult:
    fixture_id: str
    skill: str
    difficulty: str
    expected_category: str | None
    actual_category: str | None
    escalation_level: str | None
    correct: bool
    latency_ms: float
    evidence: str = ""


@dataclass
class BenchSummary:
    total: int = 0
    correct: int = 0
    by_difficulty: dict[str, dict[str, int]] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    results: list[BenchResult] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_bench(fixtures: list[dict[str, Any]]) -> BenchSummary:
    """Run all fixtures through FailureAttributor and collect results."""
    from cohezion.compound.failure_attributor import FailureAttributor

    fa = FailureAttributor()
    summary = BenchSummary()
    latencies: list[float] = []

    for fx in fixtures:
        t0 = time.perf_counter()
        attribution = fa.classify(
            output=fx["output"],
            metrics=fx["metrics"],
            decision_paths=fx.get("decision_paths"),
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        actual_cat = attribution.category if attribution else None
        actual_level = attribution.escalation_level if attribution else None
        expected_cat = fx.get("expected_category")
        correct = actual_cat == expected_cat

        result = BenchResult(
            fixture_id=fx["id"],
            skill=fx["skill"],
            difficulty=fx["difficulty"],
            expected_category=expected_cat,
            actual_category=actual_cat,
            escalation_level=actual_level,
            correct=correct,
            latency_ms=latency_ms,
            evidence=(attribution.evidence[:80] if attribution else ""),
        )
        summary.results.append(result)
        summary.total += 1
        if correct:
            summary.correct += 1
        latencies.append(latency_ms)

        diff = fx["difficulty"]
        summary.by_difficulty.setdefault(diff, {"total": 0, "correct": 0})
        summary.by_difficulty[diff]["total"] += 1
        if correct:
            summary.by_difficulty[diff]["correct"] += 1

        cat = actual_cat or "none"
        summary.by_category[cat] = summary.by_category.get(cat, 0) + 1

    summary.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
    return summary


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------


def print_table(summary: BenchSummary) -> None:
    """Print human-readable bench report."""
    print("\n" + "=" * 72)
    print("  COHEZION SKILL BENCH — FAPO Failure Attribution Evaluation")
    print("=" * 72)
    print(f"  Accuracy : {summary.accuracy:.0%}  ({summary.correct}/{summary.total})")
    print(f"  Avg latency: {summary.avg_latency_ms:.2f}ms per attribution")
    print()

    # Per-difficulty breakdown
    print("  By difficulty:")
    for diff in ["easy", "medium", "hard"]:
        if diff in summary.by_difficulty:
            d = summary.by_difficulty[diff]
            acc = d["correct"] / d["total"] if d["total"] else 0
            bar = "█" * d["correct"] + "░" * (d["total"] - d["correct"])
            print(f"    {diff:8s}  {bar}  {d['correct']}/{d['total']} ({acc:.0%})")
    print()

    # Category distribution
    print("  Attribution breakdown:")
    for cat, count in sorted(summary.by_category.items()):
        print(f"    {cat:12s}  {count:3d}")
    print()

    # Per-case table
    print(f"  {'ID':<10} {'SKILL':<22} {'DIFF':<8} {'EXPECTED':<12} {'ACTUAL':<12} {'OK'}")
    print("  " + "-" * 68)
    for r in summary.results:
        ok = "✓" if r.correct else "✗"
        exp = r.expected_category or "none"
        act = r.actual_category or "none"
        print(f"  {r.fixture_id:<10} {r.skill:<22} {r.difficulty:<8} {exp:<12} {act:<12} {ok}")

    # Failures detail
    failures = [r for r in summary.results if not r.correct]
    if failures:
        print()
        print("  Failures:")
        for r in failures:
            print(f"    [{r.fixture_id}] expected={r.expected_category} got={r.actual_category}")
            if r.evidence:
                print(f"      evidence: {r.evidence}")

    print("=" * 72 + "\n")


def print_json(summary: BenchSummary) -> None:
    """Print machine-readable JSON output."""
    data = {
        "accuracy": summary.accuracy,
        "total": summary.total,
        "correct": summary.correct,
        "avg_latency_ms": summary.avg_latency_ms,
        "by_difficulty": {
            d: {"total": v["total"], "correct": v["correct"],
                "accuracy": v["correct"] / v["total"] if v["total"] else 0}
            for d, v in summary.by_difficulty.items()
        },
        "by_category": summary.by_category,
        "results": [
            {
                "id": r.fixture_id, "skill": r.skill, "difficulty": r.difficulty,
                "expected": r.expected_category, "actual": r.actual_category,
                "escalation_level": r.escalation_level, "correct": r.correct,
                "latency_ms": round(r.latency_ms, 3),
            }
            for r in summary.results
        ],
    }
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Cohezion skill bench evaluation")
    parser.add_argument("--fixture", type=Path, help="JSON fixture file (default: embedded)")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=0.0,
        metavar="ACCURACY",
        help="Exit 1 if accuracy below this threshold (e.g. 0.8 for 80%%)",
    )
    args = parser.parse_args()

    fixtures = _DEFAULT_FIXTURES
    if args.fixture:
        fixtures = json.loads(args.fixture.read_text())

    summary = run_bench(fixtures)

    if args.json:
        print_json(summary)
    else:
        print_table(summary)

    if args.fail_under and summary.accuracy < args.fail_under:
        print(f"FAIL: accuracy {summary.accuracy:.0%} below threshold {args.fail_under:.0%}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
