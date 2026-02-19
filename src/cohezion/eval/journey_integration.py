"""Benchmark-Journey Integration: Connect FLUME to benchmark feedback loop.

This module connects benchmark results to FLUME journey tracking,
enabling data-driven improvement of code generation.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkJourney:
    """A single benchmark attempt with journey tracking."""

    benchmark: str
    task_id: str
    model: str
    success: bool
    phi_score: float | None = None
    coherence: float | None = None
    journey_12d: list[float] = field(default_factory=list)
    completion: str = ""
    error: str | None = None
    duration: float = 0.0
    timestamp: str = ""


class BenchmarkJourneyTracker:
    """Tracks journeys from benchmark attempts.

    Collects FLUME journey data alongside benchmark results
    to identify patterns that lead to success vs failure.
    """

    def __init__(self, data_dir: str = "data/eval/journeys"):
        """Initialize tracker.

        Args:
            data_dir: Directory to store journey data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.journeys: list[BenchmarkJourney] = []

    def record_attempt(
        self,
        benchmark: str,
        task_id: str,
        model: str,
        success: bool,
        completion: str,
        phi_score: float | None = None,
        coherence: float | None = None,
        journey_12d: list[float] | None = None,
        duration: float = 0.0,
    ) -> BenchmarkJourney:
        """Record a benchmark attempt with journey data.

        Args:
            benchmark: Benchmark name (humaneval, swebench, etc.)
            task_id: Task identifier
            model: Model used
            success: Whether the attempt succeeded
            completion: Generated code
            phi_score: FLUME phi score if available
            coherence: FLUME coherence if available
            journey_12d: 12D journey state if available
            duration: Time taken

        Returns:
            Recorded journey
        """
        journey = BenchmarkJourney(
            benchmark=benchmark,
            task_id=task_id,
            model=model,
            success=success,
            phi_score=phi_score,
            coherence=coherence,
            journey_12d=journey_12d or [],
            completion=completion[:500],  # Truncate for storage
            duration=duration,
            timestamp=datetime.now().isoformat(),
        )

        self.journeys.append(journey)

        # Save incrementally
        self._save()

        logger.info(
            f"Benchmark journey: {benchmark}/{task_id} - "
            f"{'SUCCESS' if success else 'FAIL'} "
            f"(phi={phi_score:.2f}, coherence={coherence:.2f})"
        )

        return journey

    def analyze_patterns(self) -> dict[str, Any]:
        """Analyze patterns in benchmark journeys.

        Identifies what distinguishes successful from failed attempts.

        Returns:
            Analysis results
        """
        if not self.journeys:
            return {"error": "No journeys recorded"}

        successful = [j for j in self.journeys if j.success]
        failed = [j for j in self.journeys if not j.success]

        analysis = {
            "total_attempts": len(self.journeys),
            "success_count": len(successful),
            "fail_count": len(failed),
            "success_rate": len(successful) / len(self.journeys)
            if self.journeys
            else 0,
        }

        # Analyze phi_score patterns
        successful_phi = [j.phi_score for j in successful if j.phi_score is not None]
        failed_phi = [j.phi_score for j in failed if j.phi_score is not None]

        if successful_phi:
            analysis["phi_score"] = {
                "successful_mean": sum(successful_phi) / len(successful_phi),
                "successful_min": min(successful_phi),
                "successful_max": max(successful_phi),
            }

        if failed_phi:
            analysis["phi_score"]["failed_mean"] = (
                sum(failed_phi) / len(failed_phi) if failed_phi else 0
            )

        # Analyze coherence patterns
        successful_coherence = [
            j.coherence for j in successful if j.coherence is not None
        ]
        failed_coherence = [j.coherence for j in failed if j.coherence is not None]

        if successful_coherence:
            analysis["coherence"] = {
                "successful_mean": sum(successful_coherence)
                / len(successful_coherence),
            }

        if failed_coherence:
            analysis["coherence"]["failed_mean"] = (
                sum(failed_coherence) / len(failed_coherence) if failed_coherence else 0
            )

        # Model comparison
        model_stats: dict[str, dict[str, int]] = {}
        for journey in self.journeys:
            if journey.model not in model_stats:
                model_stats[journey.model] = {"success": 0, "fail": 0}
            if journey.success:
                model_stats[journey.model]["success"] += 1
            else:
                model_stats[journey.model]["fail"] += 1

        analysis["model_performance"] = model_stats

        return analysis

    def get_successful_patterns(self) -> list[dict[str, Any]]:
        """Get patterns from successful attempts for imitation.

        Returns:
            List of successful patterns
        """
        successful = [j for j in self.journeys if j.success]

        return [
            {
                "task_id": j.task_id,
                "phi_score": j.phi_score,
                "coherence": j.coherence,
                "journey_12d": j.journey_12d,
                "completion": j.completion,
            }
            for j in successful
        ]

    def _save(self) -> None:
        """Save journeys to disk."""
        output_path = self.data_dir / "benchmark_journeys.jsonl"

        with open(output_path, "a") as f:
            for journey in self.journeys[-1:]:
                f.write(json.dumps(journey.__dict__) + "\n")


def compute_journey_from_completion(completion: str) -> dict[str, Any]:
    """Compute FLUME journey metrics from a completion.

    Args:
        completion: Generated code completion

    Returns:
        Dict with phi_score, coherence, journey_12d
    """
    # This is a simplified version - in production, we'd use the actual
    # JourneyTracker from cohezion.compound.journey_tracker

    # Simple heuristics based on code characteristics
    lines = completion.split("\n")
    num_lines = len([l for l in lines if l.strip()])

    # Compute simple coherence based on code structure
    has_loops = any("for " in l or "while " in l for l in lines)
    has_conditionals = any("if " in l for l in lines)
    has_returns = any("return" in l for l in lines)

    structure_score = has_loops * 0.3 + has_conditionals * 0.3 + has_returns * 0.4

    # Simple phi approximation (would use actual FLUME in production)
    phi_score = min(structure_score * 1.5, 1.0)
    coherence = structure_score

    # Generate simple 12D state
    import random

    journey_12d = [random.uniform(0.3, 0.7) for _ in range(12)]

    return {
        "phi_score": phi_score,
        "coherence": coherence,
        "journey_12d": journey_12d,
    }


class BenchmarkFeedbackLoop:
    """Closed-loop benchmark improvement using FLUME.

    This is the key differentiator: using journey data to improve
    benchmark performance over time.
    """

    def __init__(self):
        """Initialize feedback loop."""
        self.journey_tracker = BenchmarkJourneyTracker()

    def record_result(
        self,
        benchmark: str,
        task_id: str,
        model: str,
        success: bool,
        completion: str,
        duration: float = 0.0,
    ) -> None:
        """Record a benchmark result with journey tracking.

        Args:
            benchmark: Benchmark name
            task_id: Task identifier
            model: Model used
            success: Whether attempt succeeded
            completion: Generated code
            duration: Time taken
        """
        # Compute journey metrics
        journey_metrics = compute_journey_from_completion(completion)

        # Record with journey data
        self.journey_tracker.record_attempt(
            benchmark=benchmark,
            task_id=task_id,
            model=model,
            success=success,
            completion=completion,
            **journey_metrics,
            duration=duration,
        )

    def get_improvement_suggestions(self) -> dict[str, Any]:
        """Get suggestions for improvement based on journey analysis.

        Returns:
            Improvement suggestions
        """
        analysis = self.journey_tracker.analyze_patterns()

        suggestions = {
            "insights": [],
            "recommended_actions": [],
        }

        # Generate insights
        if "phi_score" in analysis:
            ps = analysis["phi_score"]
            if "successful_mean" in ps and "failed_mean" in ps:
                diff = ps["successful_mean"] - ps["failed_mean"]
                if diff > 0.1:
                    suggestions["insights"].append(
                        f"Successful attempts have higher phi_score "
                        f"(+{diff:.2f}). Focus on code structure."
                    )

        if "coherence" in analysis:
            cs = analysis["coherence"]
            if "successful_mean" in cs and "failed_mean" in cs:
                diff = cs["successful_mean"] - cs["failed_mean"]
                if diff > 0.1:
                    suggestions["insights"].append(
                        f"Successful attempts have higher coherence (+{diff:.2f})."
                    )

        # Generate actions
        if analysis.get("success_rate", 0) < 0.3:
            suggestions["recommended_actions"].append(
                "Consider using a code-specialized model or fine-tuning"
            )

        model_perf = analysis.get("model_performance", {})
        if model_perf:
            best_model = max(
                model_perf.items(),
                key=lambda x: (
                    x[1]["success"] / (x[1]["success"] + x[1]["fail"])
                    if (x[1]["success"] + x[1]["fail"]) > 0
                    else 0
                ),
            )
            suggestions["recommended_actions"].append(
                f"Best performing model: {best_model[0]}"
            )

        return suggestions
