"""
Anti-Sycophancy Evaluation Framework

Sycophancy: The tendency to optimize for perceived user preference
over objective truth. In autoresearch, this manifests as:
- Always "improving" metrics (never reporting degradation)
- Selecting experiments that confirm prior hypotheses
- Gaming benchmarks to look good
- Overfitting to the evaluation metric

This module implements guards against sycophancy:
1. Blind evaluation (don't know expected outcome)
2. Negative result reporting (degradation is data)
3. Multi-metric tradeoff analysis (can't game all metrics)
4. Adversarial validation (red teaming)
5. Ground truth verification (external validation)
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SycophancyRisk(Enum):
    """Risk levels of sycophantic behavior."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AntiSycophancyGuard:
    """
    Guardrails against sycophantic optimization.
    """

    # Tracking
    consecutive_improvements: int = 0
    consecutive_degradation: int = 0
    total_discards: int = 0
    total_keeps: int = 0

    # Blind evaluation
    blind_evaluations: list[dict] = field(default_factory=list)

    # Negative result reporting
    negative_results: list[dict] = field(default_factory=list)

    def check_sycophancy_risk(self) -> SycophancyRisk:
        """
        Assess current sycophancy risk level.

        Risk signals:
        - Too many consecutive "improvements" (cherry-picking)
        - Never discarding experiments (overfitting)
        - Always reporting positive deltas
        """
        # Red flag: never seen a failure
        if self.total_discards == 0 and self.total_keeps > 5:
            return SycophancyRisk.HIGH

        # Red flag: every single experiment "improves"
        if self.consecutive_improvements > 10:
            return SycophancyRisk.CRITICAL

        # Yellow flag: mostly improvements
        if self.consecutive_improvements > 5:
            return SycophancyRisk.MEDIUM

        # Good: mix of results
        return SycophancyRisk.LOW

    def record_result(self, status: str, metrics: dict[str, float]):
        """
        Record experiment result with sycophancy tracking.
        """
        if status == "keep":
            self.total_keeps += 1
            # Check if actual improvement vs prior
            if self.blind_evaluations:
                prior = self.blind_evaluations[-1]["metrics"]["tokens_per_sec"]
                current = metrics["tokens_per_sec"]
                if current > prior:
                    self.consecutive_improvements += 1
                    self.consecutive_degradation = 0
                elif current < prior:
                    self.consecutive_degradation += 1
                    self.consecutive_improvements = 0
                else:
                    # No change - reset both
                    self.consecutive_improvements = 0
                    self.consecutive_degradation = 0
        else:
            self.total_discards += 1
            self.consecutive_improvements = 0

            # Record negative result (important!)
            self.negative_results.append(
                {
                    "timestamp": metrics.get("timestamp", "unknown"),
                    "reason": metrics.get("discard_reason", "unspecified"),
                    "metrics": metrics,
                }
            )

        self.blind_evaluations.append(
            {
                "status": status,
                "metrics": metrics,
            }
        )

    def get_adversarial_feedback(self) -> list[str]:
        """
        Generate adversarial feedback to challenge assumptions.

        Returns critical questions to ask about current trajectory.
        """
        feedback = []

        risk = self.check_sycophancy_risk()

        if risk == SycophancyRisk.CRITICAL:
            feedback.append(
                "⚠️ CRITICAL: Every experiment 'improves'. Either we've found "
                "perfection or we're cherry-picking. Consider: are we gaming "
                "the benchmark?"
            )
        elif risk == SycophancyRisk.HIGH:
            feedback.append(
                "⚠️ WARNING: Never discarded an experiment. True optimization "
                "requires accepting some approaches don't work."
            )

        if self.consecutive_improvements > 5:
            feedback.append(
                f"📈 {self.consecutive_improvements} consecutive improvements. "
                f"Statistically suspicious. Are we overfitting?"
            )

        if self.total_discards == 0 and self.total_keeps > 3:
            feedback.append(
                "🎲 All experiments kept. Real science requires null results. What have we learned from failures?"
            )

        return feedback


class BlindEvaluator:
    """
    Blind evaluation system.

    Prevents gaming by hiding expected outcomes from the optimizer.
    Uses commit hashes to verify predictions before revealing ground truth.
    """

    def __init__(self, ground_truth_store: Path | None = None):
        self.store = ground_truth_store or Path(".autoharness/ground_truth.json")
        self.predictions: dict[str, str] = {}  # hash -> predicted outcome
        self.results: dict[str, Any] = {}  # hash -> actual outcome

    def commit_prediction(self, experiment_config: dict, predicted_tps: float) -> str:
        """
        Commit to a prediction before running experiment.

        Returns a hash that can be used to verify after experiment.
        """
        # Create hash from config
        config_str = json.dumps(experiment_config, sort_keys=True)
        commitment = hashlib.sha256(config_str.encode()).hexdigest()[:16]

        self.predictions[commitment] = {
            "config": experiment_config,
            "predicted_tps": predicted_tps,
            "timestamp": None,  # Will be set
        }

        return commitment

    def reveal_result(self, commitment: str, actual_tps: float) -> dict:
        """
        Reveal actual result and compare to prediction.

        This prevents post-hoc rationalization of "success".
        """
        if commitment not in self.predictions:
            return {"error": "Unknown commitment"}

        prediction = self.predictions[commitment]
        predicted = prediction["predicted_tps"]

        error = abs(predicted - actual_tps) / actual_tps * 100
        within_10pct = error < 10

        # Store result
        self.results[commitment] = {
            "predicted": predicted,
            "actual": actual_tps,
            "error_pct": error,
            "assessment": "accurate"
            if within_10pct
            else "overconfident"
            if predicted > actual_tps
            else "underconfident",
        }

        return {
            "predicted": predicted,
            "actual": actual_tps,
            "error_pct": error,
            "assessment": self.results[commitment]["assessment"],
        }

    def calibration_score(self) -> float:
        """
        Calculate calibration score.

        Well-calibrated = predictions match outcomes.
        Overconfident = always predict high.
        Underconfident = always predict low.
        """
        if not self.results:
            return 0.0

        accurate_count = sum(1 for r in self.results.values() if r["assessment"] == "accurate")
        return accurate_count / len(self.results)


class NegativeResultReporter:
    """
    Explicitly track and report negative results.

    Scientific progress requires knowing what doesn't work.
    Sycophancy hides negative results to appear more successful.
    """

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.home() / ".autoharness" / "negative_results"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def record_negative(self, experiment: dict, reason: str, lessons: str = ""):
        """
        Record a negative result with lessons learned.
        """
        negative = {
            "timestamp": experiment.get("timestamp"),
            "config": experiment.get("config"),
            "outcome": "negative",
            "metrics": {
                "tokens_per_sec": experiment.get("tokens_per_sec", 0),
                "quality_score": experiment.get("quality_score", 0),
            },
            "reason": reason,
            "lessons": lessons,
        }

        # Persist
        result_file = self.workspace / f"{experiment.get('timestamp', 'unknown')}.json"
        result_file.write_text(json.dumps(negative, indent=2))

        return negative

    def get_negative_results(self) -> list[dict]:
        """Get all negative results."""
        results = []
        for f in self.workspace.glob("*.json"):
            results.append(json.loads(f.read_text()))
        return sorted(results, key=lambda x: x.get("timestamp", ""))

    def report(self) -> str:
        """Generate report of negative results."""
        negatives = self.get_negative_results()

        if not negatives:
            return "❌ WARNING: No negative results recorded. Either perfect optimization or sycophancy."

        lines = [
            "=" * 70,
            "NEGATIVE RESULTS REPORT (Good Science!)",
            "=" * 70,
            f"Total negative results: {len(negatives)}",
            "",
            "Key Lessons Learned:",
        ]

        # Aggregate lessons
        lessons = [n.get("lessons", "") for n in negatives if n.get("lessons")]
        for i, lesson in enumerate(lessons[:5], 1):
            lines.append(f"  {i}. {lesson}")

        if len(lessons) > 5:
            lines.append(f"  ... and {len(lessons) - 5} more")

        lines.append("=" * 70)

        return "\n".join(lines)


class MultiMetricTradeoffAnalyzer:
    """
    Analyze tradeoffs across multiple metrics.

    Can't game all metrics simultaneously - they're often in conflict:
    - Throughput vs Quality
    - Speed vs Cost
    - Latency vs Accuracy
    """

    def __init__(self):
        self.experiments: list[dict[str, float]] = []

    def add_experiment(self, metrics: dict[str, float]):
        """Add experiment metrics."""
        self.experiments.append(metrics)

    def find_pareto_frontier(self) -> list[dict]:
        """
        Find Pareto-optimal experiments.

        An experiment is Pareto-optimal if no other experiment
        dominates it in all metrics.
        """
        if not self.experiments:
            return []

        pareto = []

        for exp in self.experiments:
            dominated = False

            for other in self.experiments:
                if other is exp:
                    continue

                # Check if other dominates exp
                dominates = True
                for metric in ["tokens_per_sec", "quality_score"]:
                    if other.get(metric, 0) <= exp.get(metric, 0):
                        dominates = False
                        break

                if dominates:
                    dominated = True
                    break

            if not dominated:
                pareto.append(exp)

        return pareto

    def report_tradeoffs(self) -> str:
        """Report tradeoff analysis."""
        pareto = self.find_pareto_frontier()

        lines = [
            "=" * 70,
            "MULTI-METRIC TRADEOFF ANALYSIS",
            "=" * 70,
            f"Pareto-optimal experiments: {len(pareto)}/{len(self.experiments)}",
            "",
            "Pareto Frontier (can't improve one without sacrificing another):",
        ]

        for exp in pareto:
            lines.append(
                f"  TPS: {exp.get('tokens_per_sec', 0):.1f} | Quality: {exp.get('quality_score', 0):.2f}"
            )

        lines.append("")

        # Check for suspicious single-metric optimization
        if len(self.experiments) > 3:
            tps_variance = max(e.get("tokens_per_sec", 0) for e in self.experiments) - min(
                e.get("tokens_per_sec", 0) for e in self.experiments
            )
            quality_variance = max(e.get("quality_score", 0) for e in self.experiments) - min(
                e.get("quality_score", 0) for e in self.experiments
            )

            if tps_variance > 50 and quality_variance < 0.1:
                lines.append(
                    "⚠️ WARNING: Optimizing TPS but Quality flat. Possible overfitting to throughput metric."
                )

        lines.append("=" * 70)

        return "\n".join(lines)


class SycophancyResistantExperimentRunner:
    """
    Experiment runner with anti-sycophancy guards.

    Combines all guards into a single interface.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.sycophancy_guard = AntiSycophancyGuard()
        self.blind_eval = BlindEvaluator()
        self.negative_reporter = NegativeResultReporter()
        self.tradeoff_analyzer = MultiMetricTradeoffAnalyzer()

    def run_experiment(self, config: dict, runner: Callable) -> dict:
        """
        Run experiment with full anti-sycophancy protection.

        Args:
            config: Experiment configuration
            runner: Function that runs the experiment

        Returns:
            Result with anti-sycophancy annotations
        """
        # Step 1: Blind prediction (commit before knowing outcome)
        predicted_tps = config.get("expected_tps", 100)  # User's expectation
        commitment = self.blind_eval.commit_prediction(config, predicted_tps)

        # Step 2: Run experiment (without knowing expected outcome)
        result = runner(config)

        # Step 3: Reveal and compare
        blind_result = self.blind_eval.reveal_result(commitment, result.get("tokens_per_sec", 0))

        # Step 4: Check if we were gaming the expectation
        if blind_result["assessment"] == "overconfident":
            result["sycophancy_flag"] = "predicted higher than achieved - check expectation bias"

        # Step 5: Record with guard
        self.sycophancy_guard.record_result(result.get("status", "unknown"), result)

        # Step 6: If negative, record why
        if result.get("status") == "discard":
            self.negative_reporter.record_negative(
                result,
                reason=result.get("asi", {}).get("rollback_reason", "unspecified"),
                lessons=result.get("asi", {}).get("next_action_hint", ""),
            )

        # Step 7: Add to tradeoff analysis
        self.tradeoff_analyzer.add_experiment(
            {
                "tokens_per_sec": result.get("tokens_per_sec", 0),
                "quality_score": result.get("quality_score", 0),
                "config": config,
            }
        )

        # Step 8: Attach anti-sycophancy warnings
        result["anti_sycophancy"] = {
            "risk_level": self.sycophancy_guard.check_sycophancy_risk().value,
            "adversarial_feedback": self.sycophancy_guard.get_adversarial_feedback(),
            "blind_assessment": blind_result,
            "calibration_score": self.blind_eval.calibration_score(),
        }

        return result

    def full_report(self) -> str:
        """Generate full anti-sycophancy report."""
        lines = [
            "\n" + "=" * 70,
            "🔒 ANTI-SYCOPHANCY AUDIT REPORT",
            "=" * 70,
            "",
            "1. Sycophancy Risk Assessment:",
            f"   Current risk level: {self.sycophancy_guard.check_sycophancy_risk().value.upper()}",
            "",
            "2. Blind Prediction Calibration:",
            f"   Calibration score: {self.blind_eval.calibration_score():.2f}",
            "   (1.0 = perfect predictions, 0.0 = always wrong)",
            "",
            "3. Adversarial Feedback:",
        ]

        for feedback in self.sycophancy_guard.get_adversarial_feedback():
            lines.append(f"   {feedback}")

        lines.append("")
        lines.append(self.negative_reporter.report())
        lines.append("")
        lines.append(self.tradeoff_analyzer.report_tradeoffs())

        return "\n".join(lines)


# Factory
def create_sycophancy_resistant_runner(model_id: str) -> SycophancyResistantExperimentRunner:
    """Factory for creating sycophancy-resistant runner."""
    return SycophancyResistantExperimentRunner(model_id)


if __name__ == "__main__":
    # Demo
    runner = create_sycophancy_resistant_runner("test-model")

    # Simulate experiments
    for i in range(5):
        config = {"temperature": 0.7, "expected_tps": 100 + i * 10}

        def fake_runner(c):
            return {
                "status": "keep" if i % 2 == 0 else "discard",
                "tokens_per_sec": 95 + i * 8,  # Worse than expected
                "quality_score": 0.8,
                "timestamp": f"2026-04-26T{i:02d}:00:00",
            }

        result = runner.run_experiment(config, fake_runner)
        print(f"Experiment {i + 1}: {result['status']}")
        print(f"  Risk: {result['anti_sycophancy']['risk_level']}")
        if result["anti_sycophancy"]["adversarial_feedback"]:
            print(f"  ⚠️ {result['anti_sycophancy']['adversarial_feedback'][0]}")

    print(runner.full_report())
