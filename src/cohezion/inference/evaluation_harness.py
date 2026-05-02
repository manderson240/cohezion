"""
Evaluation Harness - Comprehensive Metrics for Autoresearch

Evaluates experiments across multiple dimensions:
1. Throughput (tokens/sec)
2. Quality (accuracy/coherence)
3. Token efficiency (context usage)
4. Cost (estimated API spend)

Integrates with CompoundEngineeringAutoHarness for feedback loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExperimentMetrics:
    """Standardized experiment metrics."""

    # Throughput
    tokens_per_sec: float = 0.0
    latency_ms: float = 0.0
    tokens_generated: int = 0

    # Quality
    quality_score: float = 0.0  # 0-1 scale
    success_rate: float = 0.0  # % of successful completions
    error_count: int = 0

    # Token Efficiency
    input_tokens: int = 0
    output_tokens: int = 0
    context_tokens: int = 0  # system/prompt overhead
    total_tokens: int = 0

    # Cost (estimated)
    estimated_cost_usd: float = 0.0

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    config: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def efficiency_score(self) -> float:
        """Calculate efficiency: quality per token."""
        if self.total_tokens == 0:
            return 0.0
        return (self.quality_score * self.tokens_per_sec) / (self.total_tokens / 1000)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "throughput": {
                "tokens_per_sec": self.tokens_per_sec,
                "latency_ms": self.latency_ms,
                "tokens_generated": self.tokens_generated,
            },
            "quality": {
                "quality_score": self.quality_score,
                "success_rate": self.success_rate,
                "error_count": self.error_count,
            },
            "efficiency": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "context_tokens": self.context_tokens,
                "total_tokens": self.total_tokens,
                "efficiency_score": self.efficiency_score(),
            },
            "cost": {
                "estimated_usd": self.estimated_cost_usd,
            },
            "metadata": {
                "timestamp": self.timestamp,
                "config": self.config,
                "notes": self.notes,
            },
        }


class EvaluationHarness:
    """
    Comprehensive evaluation framework for autoresearch.

    Measures:
    - Speed: tokens/sec, latency
    - Quality: accuracy, coherence, task completion
    - Efficiency: tokens used per unit of quality
    - Cost: estimated spend
    """

    def __init__(self, model_id: str, workspace: Path | None = None):
        self.model_id = model_id
        self.workspace = workspace or Path.home() / ".autoharness" / "evaluations"
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.experiments: list[ExperimentMetrics] = []
        self._load_history()

    def _load_history(self):
        """Load prior experiment history."""
        history_file = self.workspace / f"{self.model_id}_history.jsonl"
        if history_file.exists():
            for line in history_file.read_text().strip().split("\n"):
                if line:
                    data = json.loads(line)
                    self.experiments.append(ExperimentMetrics(**data))

    def record_experiment(self, metrics: ExperimentMetrics) -> dict:
        """
        Record an experiment and generate evaluation.

        Returns evaluation result with status determination.
        """
        # Add to history
        self.experiments.append(metrics)

        # Persist
        self._persist(metrics)

        # Compare to baseline
        evaluation = self._evaluate(metrics)

        return evaluation

    def _persist(self, metrics: ExperimentMetrics):
        """Persist experiment to history file."""
        history_file = self.workspace / f"{self.model_id}_history.jsonl"
        with open(history_file, "a") as f:
            # Convert to simple dict for serialization
            data = {
                "tokens_per_sec": metrics.tokens_per_sec,
                "latency_ms": metrics.latency_ms,
                "tokens_generated": metrics.tokens_generated,
                "quality_score": metrics.quality_score,
                "success_rate": metrics.success_rate,
                "error_count": metrics.error_count,
                "input_tokens": metrics.input_tokens,
                "output_tokens": metrics.output_tokens,
                "context_tokens": metrics.context_tokens,
                "total_tokens": metrics.total_tokens,
                "estimated_cost_usd": metrics.estimated_cost_usd,
                "timestamp": metrics.timestamp,
                "config": metrics.config,
                "notes": metrics.notes,
            }
            f.write(json.dumps(data) + "\n")

    def _evaluate(self, metrics: ExperimentMetrics) -> dict:
        """
        Evaluate experiment against baselines and prior experiments.

        Determines:
        - status: keep, discard, or crash
        - improvements: relative to baseline
        - confidence: statistical significance
        """
        if not self.experiments:
            # First experiment
            return {
                "status": "keep",  # baseline
                "improvement_pct": 0.0,
                "confidence": None,
                "reason": "First experiment - baseline established",
            }

        # Get baseline (first successful experiment)
        baseline = next((e for e in self.experiments if e.success_rate > 0), None)
        if not baseline:
            return {
                "status": "keep",
                "improvement_pct": 0.0,
                "confidence": None,
                "reason": "No prior successful baseline",
            }

        # Calculate improvement
        throughput_delta = (
            (metrics.tokens_per_sec - baseline.tokens_per_sec) / baseline.tokens_per_sec * 100
        )
        quality_delta = (
            (metrics.quality_score - baseline.quality_score)
            / max(baseline.quality_score, 0.01)
            * 100
        )
        efficiency_delta = (
            (metrics.efficiency_score() - baseline.efficiency_score())
            / max(baseline.efficiency_score(), 0.01)
            * 100
        )

        # Weighted composite
        composite_improvement = (
            throughput_delta * 0.5 + quality_delta * 0.3 + efficiency_delta * 0.2
        )

        # Determine status
        status = "keep" if composite_improvement >= -5 else "discard"
        status = "crash" if metrics.error_count > 0 and metrics.success_rate < 0.5 else status

        # Calculate confidence (simple version)
        confidence = None
        if len(self.experiments) >= 3:
            # Look at variance in recent experiments
            recent = self.experiments[-5:]
            throughputs = [e.tokens_per_sec for e in recent]
            avg = sum(throughputs) / len(throughputs)
            variance = sum((t - avg) ** 2 for t in throughputs) / len(throughputs)
            std = variance**0.5

            if std > 0:
                confidence = abs(metrics.tokens_per_sec - avg) / std

        return {
            "status": status,
            "improvement_pct": composite_improvement,
            "deltas": {
                "throughput": throughput_delta,
                "quality": quality_delta,
                "efficiency": efficiency_delta,
            },
            "confidence": confidence,
            "reason": f"Composite improvement: {composite_improvement:+.1f}%",
        }

    def get_best(self, n: int = 3) -> list[ExperimentMetrics]:
        """Get top N experiments by efficiency score."""
        sorted_exps = sorted(self.experiments, key=lambda e: e.efficiency_score(), reverse=True)
        return sorted_exps[:n]

    def analyze_trends(self) -> dict:
        """Analyze trends across experiments."""
        if len(self.experiments) < 2:
            return {"error": "Need at least 2 experiments for trend analysis"}

        # Calculate trends without calling _generate_recommendations
        trends = self._calculate_trends_simple()

        return {
            "experiment_count": len(self.experiments),
            "throughput_trend": trends.get("throughput_trend"),
            "quality_trend": trends.get("quality_trend"),
            "best_config": self.get_best(1)[0].config if self.get_best(1) else None,
            "recommendations": self._generate_recommendations(trends),
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """Simple trend calculation."""
        if len(values) < 2:
            return "insufficient_data"

        # Compare first half vs second half
        mid = len(values) // 2
        first_avg = sum(values[:mid]) / mid if mid > 0 else 0
        second_avg = sum(values[mid:]) / (len(values) - mid) if mid < len(values) else 0

        if second_avg > first_avg * 1.05:
            return "improving"
        elif second_avg < first_avg * 0.95:
            return "degrading"
        else:
            return "stable"

    def _generate_recommendations(self, trends: dict = None) -> list[str]:
        """Generate recommendations based on history."""
        recs = []

        best = self.get_best(1)
        if best:
            b = best[0]
            recs.append(
                f"Best config: temp={b.config.get('temperature')}, "
                f"max_tokens={b.config.get('max_tokens')}"
            )

        if trends is None:
            trends = self._calculate_trends_simple()

        if trends.get("throughput_trend") == "degrading":
            recs.append("Throughput degrading - consider lower concurrency")
        if trends.get("quality_trend") == "degrading":
            recs.append("Quality degrading - consider higher temperature")

        return recs

    def _calculate_trends_simple(self) -> dict:
        """Calculate trends without calling analyze_trends (avoid recursion)."""
        if len(self.experiments) < 2:
            return {"throughput_trend": "insufficient", "quality_trend": "insufficient"}

        throughputs = [e.tokens_per_sec for e in self.experiments]
        qualities = [e.quality_score for e in self.experiments]

        mid = len(throughputs) // 2
        first_tps = sum(throughputs[:mid]) / max(mid, 1)
        second_tps = sum(throughputs[mid:]) / max(len(throughputs) - mid, 1)

        first_q = sum(qualities[:mid]) / max(mid, 1)
        second_q = sum(qualities[mid:]) / max(len(qualities) - mid, 1)

        tps_trend = (
            "improving"
            if second_tps > first_tps * 1.05
            else "degrading"
            if second_tps < first_tps * 0.95
            else "stable"
        )
        q_trend = (
            "improving"
            if second_q > first_q * 1.05
            else "degrading"
            if second_q < first_q * 0.95
            else "stable"
        )

        return {"throughput_trend": tps_trend, "quality_trend": q_trend}

    def report(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 70,
            "EVALUATION HARNESS REPORT",
            "=" * 70,
            f"Model: {self.model_id}",
            f"Experiments: {len(self.experiments)}",
            "",
            "--- BEST EXPERIMENTS ---",
        ]

        for i, exp in enumerate(self.get_best(3), 1):
            lines.append(
                f"{i}. TPS: {exp.tokens_per_sec:.1f} | "
                f"Quality: {exp.quality_score:.2f} | "
                f"Efficiency: {exp.efficiency_score():.3f}"
            )

        lines.append("")
        lines.append("--- TRENDS ---")
        trends = self.analyze_trends()
        lines.append(f"Throughput: {trends.get('throughput_trend', 'N/A')}")
        lines.append(f"Quality: {trends.get('quality_trend', 'N/A')}")

        lines.append("")
        lines.append("--- RECOMMENDATIONS ---")
        for rec in trends.get("recommendations", []):
            lines.append(f"• {rec}")

        lines.append("=" * 70)

        return "\n".join(lines)


# Utility functions for evaluation
def evaluate_quality_simple(text: str, expected_contains: list[str]) -> float:
    """
    Simple quality evaluation.
    Returns score 0-1 based on presence of expected content.
    """
    if not text:
        return 0.0

    matches = sum(1 for expected in expected_contains if expected.lower() in text.lower())
    return matches / len(expected_contains) if expected_contains else 0.5


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "default") -> float:
    """Estimate API cost in USD."""
    # Rough estimates (per 1K tokens)
    pricing = {
        "default": {"input": 0.002, "output": 0.006},
        "deepseek": {"input": 0.0005, "output": 0.0015},
    }

    p = pricing.get(model, pricing["default"])
    return input_tokens / 1000 * p["input"] + output_tokens / 1000 * p["output"]


if __name__ == "__main__":
    # Demo evaluation
    harness = EvaluationHarness("test-model")

    # Simulate experiments
    for i in range(5):
        metrics = ExperimentMetrics(
            tokens_per_sec=100 + i * 10,
            quality_score=0.7 + i * 0.05,
            total_tokens=2000 + i * 100,
            config={"temperature": 0.7, "max_tokens": 512},
            notes=f"Experiment {i + 1}",
        )
        result = harness.record_experiment(metrics)
        print(f"Experiment {i + 1}: {result['status']} ({result['improvement_pct']:+.1f}%)")

    print("\n" + harness.report())
