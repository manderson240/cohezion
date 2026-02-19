"""Pattern analysis for benchmark journey data.

Analyzes journey data from benchmark attempts to identify patterns
that correlate with success or failure, computes statistical correlations,
and generates recommendations for improvement.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cohezion.compound.journey_tracker import JourneyTracker


logger = logging.getLogger(__name__)


@dataclass
class JourneyAttempt:
    """A single benchmark attempt with journey metrics."""

    task_id: str
    benchmark: str
    model: str
    success: bool
    phi_score: float | None = None
    coherence: float | None = None
    journey_12d: list[float] = field(default_factory=list)
    completion: str = ""
    error: str | None = None
    duration: float = 0.0
    num_tokens: int = 0
    timestamp: str = ""


@dataclass
class PatternStats:
    """Statistical summary of a metric."""

    mean: float
    variance: float
    std_dev: float
    min_val: float
    max_val: float
    median: float


@dataclass
class CorrelationResult:
    """Correlation between a metric and success."""

    metric: str
    phi_coefficient: float
    p_value: float
    interpretation: str


@dataclass
class SuccessPattern:
    """A pattern associated with successful attempts."""

    phi_score_range: tuple[float, float]
    coherence_range: tuple[float, float]
    journey_12d_mean: list[float]
    completion_prefix: str
    frequency: float


@dataclass
class FailurePattern:
    """A pattern associated with failed attempts."""

    phi_score_range: tuple[float, float]
    coherence_range: tuple[float, float]
    common_errors: list[str]
    journey_12d_mean: list[float]


@dataclass
class Recommendation:
    """A recommendation for improvement."""

    priority: int
    category: str
    description: str
    evidence: list[str]


class PatternAnalyzer:
    """Analyze journey patterns from benchmark attempts.

    Features:
    - Statistical analysis (mean, variance, correlation)
    - Success pattern extraction
    - Failure pattern identification
    - Recommendation generation based on patterns

    Example:
        ```python
        analyzer = PatternAnalyzer()

        # Add attempts
        analyzer.add_attempt(JourneyAttempt(
            task_id="task-1",
            benchmark="humaneval",
            model="claude-3",
            success=True,
            phi_score=0.85,
            coherence=0.78,
            completion="def solution():\\n    pass"
        ))

        # Analyze patterns
        analysis = analyzer.analyze()
        recommendations = analyzer.generate_recommendations()
        patterns = analyzer.extract_success_patterns()
        ```
    """

    def __init__(self, journey_tracker: JourneyTracker | None = None):
        """Initialize pattern analyzer.

        Args:
            journey_tracker: Optional JourneyTracker for trajectory analysis
        """
        self.journey_tracker = journey_tracker
        self.attempts: list[JourneyAttempt] = []

    def add_attempt(self, attempt: JourneyAttempt) -> None:
        """Add a journey attempt for analysis.

        Args:
            attempt: The journey attempt to add
        """
        self.attempts.append(attempt)
        logger.debug(f"Added attempt: {attempt.task_id} success={attempt.success}")

    def add_attempts(self, attempts: list[JourneyAttempt]) -> None:
        """Add multiple journey attempts.

        Args:
            attempts: List of journey attempts to add
        """
        self.attempts.extend(attempts)

    def analyze(self) -> dict[str, Any]:
        """Analyze all recorded journey attempts.

        Returns:
            Dictionary containing statistical analysis results
        """
        if not self.attempts:
            return {"error": "No attempts recorded"}

        successful = [a for a in self.attempts if a.success]
        failed = [a for a in self.attempts if not a.success]

        analysis: dict[str, Any] = {
            "total_attempts": len(self.attempts),
            "success_count": len(successful),
            "fail_count": len(failed),
            "success_rate": len(successful) / len(self.attempts)
            if self.attempts
            else 0,
        }

        analysis["phi_score"] = self._analyze_metric(
            [a.phi_score for a in self.attempts if a.phi_score is not None],
            successful=[a.phi_score for a in successful if a.phi_score is not None],
            failed=[a.phi_score for a in failed if a.phi_score is not None],
        )

        analysis["coherence"] = self._analyze_metric(
            [a.coherence for a in self.attempts if a.coherence is not None],
            successful=[a.coherence for a in successful if a.coherence is not None],
            failed=[a.coherence for a in failed if a.coherence is not None],
        )

        analysis["duration"] = self._analyze_metric(
            [a.duration for a in self.attempts],
            successful=[a.duration for a in successful],
            failed=[a.duration for a in failed],
        )

        analysis["num_tokens"] = self._analyze_metric(
            [a.num_tokens for a in self.attempts if a.num_tokens > 0],
            successful=[a.num_tokens for a in successful if a.num_tokens > 0],
            failed=[a.num_tokens for a in failed if a.num_tokens > 0],
        )

        analysis["correlations"] = self._compute_correlations()

        analysis["model_performance"] = self._analyze_model_performance()

        if self.journey_tracker and self.attempts:
            analysis["trajectory_analysis"] = self._analyze_trajectories()

        return analysis

    def _analyze_metric(
        self,
        values: list[float],
        successful: list[float],
        failed: list[float],
    ) -> dict[str, Any]:
        """Analyze a single metric.

        Args:
            values: All values
            successful: Values from successful attempts
            failed: Values from failed attempts

        Returns:
            Statistical analysis of the metric
        """
        result: dict[str, Any] = {}

        if values:
            arr = np.array(values)
            result["overall"] = {
                "mean": float(np.mean(arr)),
                "variance": float(np.var(arr)),
                "std_dev": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "median": float(np.median(arr)),
            }

        if successful:
            arr = np.array(successful)
            result["successful"] = {
                "mean": float(np.mean(arr)),
                "variance": float(np.var(arr)),
                "std_dev": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "count": len(successful),
            }

        if failed:
            arr = np.array(failed)
            result["failed"] = {
                "mean": float(np.mean(arr)),
                "variance": float(np.var(arr)),
                "std_dev": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "count": len(failed),
            }

        return result

    def _compute_correlations(self) -> list[CorrelationResult]:
        """Compute correlations between metrics and success.

        Returns:
            List of correlation results
        """
        results: list[CorrelationResult] = []

        success_binary = np.array([1.0 if a.success else 0.0 for a in self.attempts])

        metrics = [
            (
                "phi_score",
                [a.phi_score for a in self.attempts if a.phi_score is not None],
            ),
            (
                "coherence",
                [a.coherence for a in self.attempts if a.coherence is not None],
            ),
            ("duration", [a.duration for a in self.attempts]),
            ("num_tokens", [a.num_tokens for a in self.attempts if a.num_tokens > 0]),
        ]

        for metric_name, values in metrics:
            if len(values) < 3:
                continue

            metric_values = np.array(values)
            if len(metric_values) != len(success_binary):
                continue

            phi, p_value = self._point_biserial_correlation(
                metric_values, success_binary
            )

            interpretation = self._interpret_correlation(phi)

            results.append(
                CorrelationResult(
                    metric=metric_name,
                    phi_coefficient=phi,
                    p_value=p_value,
                    interpretation=interpretation,
                )
            )

        return results

    def _point_biserial_correlation(
        self,
        continuous: np.ndarray,
        binary: np.ndarray,
    ) -> tuple[float, float]:
        """Compute point-biserial correlation coefficient.

        Args:
            continuous: Continuous variable values
            binary: Binary (0/1) variable values

        Returns:
            Tuple of (phi_coefficient, p_value)
        """
        n = len(continuous)
        if n < 3:
            return 0.0, 1.0

        std_all = np.std(continuous, ddof=1)

        if std_all == 0:
            return 0.0, 1.0

        group1 = continuous[binary == 1]
        group0 = continuous[binary == 0]

        if len(group1) == 0 or len(group0) == 0:
            return 0.0, 1.0

        mean1 = np.mean(group1)
        mean0 = np.mean(group0)

        n1 = len(group1)
        n0 = len(group0)

        phi = (mean1 - mean0) / std_all * np.sqrt(n1 * n0 / (n * n))

        t_stat = phi * np.sqrt((n - 2) / (1 - phi**2)) if abs(phi) < 1 else 0.0
        p_value = self._approximate_p_value(t_stat, n - 2)

        return float(phi), float(p_value)

    def _approximate_p_value(self, t: float, df: float) -> float:
        """Approximate p-value from t-statistic.

        Args:
            t: T-statistic
            df: Degrees of freedom

        Returns:
            Approximate p-value
        """
        x = df / (df + t * t)
        return 0.5 * x ** (df / 2)

    def _interpret_correlation(self, phi: float) -> str:
        """Interpret correlation coefficient strength.

        Args:
            phi: Phi coefficient

        Returns:
            Interpretation string
        """
        abs_phi = abs(phi)
        if abs_phi >= 0.7:
            strength = "strong"
        elif abs_phi >= 0.4:
            strength = "moderate"
        elif abs_phi >= 0.2:
            strength = "weak"
        else:
            strength = "negligible"

        direction = "positive" if phi > 0 else "negative"

        return f"{strength} {direction} correlation"

    def _analyze_model_performance(self) -> dict[str, dict[str, Any]]:
        """Analyze performance by model.

        Returns:
            Model performance statistics
        """
        model_stats: dict[str, dict[str, Any]] = {}

        for attempt in self.attempts:
            if attempt.model not in model_stats:
                model_stats[attempt.model] = {
                    "success": 0,
                    "fail": 0,
                    "total": 0,
                    "phi_scores": [],
                    "coherence_values": [],
                }

            model_stats[attempt.model]["total"] += 1
            if attempt.success:
                model_stats[attempt.model]["success"] += 1
            else:
                model_stats[attempt.model]["fail"] += 1

            if attempt.phi_score is not None:
                model_stats[attempt.model]["phi_scores"].append(attempt.phi_score)
            if attempt.coherence is not None:
                model_stats[attempt.model]["coherence_values"].append(attempt.coherence)

        for _model, stats in model_stats.items():
            stats["success_rate"] = (
                stats["success"] / stats["total"] if stats["total"] > 0 else 0
            )
            if stats["phi_scores"]:
                stats["avg_phi_score"] = sum(stats["phi_scores"]) / len(
                    stats["phi_scores"]
                )
            if stats["coherence_values"]:
                stats["avg_coherence"] = sum(stats["coherence_values"]) / len(
                    stats["coherence_values"]
                )

        return model_stats

    def _analyze_trajectories(self) -> dict[str, Any]:
        """Analyze 12D journey trajectories.

        Returns:
            Trajectory analysis results
        """
        successful = [a for a in self.attempts if a.success and a.journey_12d]
        failed = [a for a in self.attempts if not a.success and a.journey_12d]

        result: dict[str, Any] = {}

        if successful:
            successful_arr = np.array([a.journey_12d for a in successful])
            result["successful_mean_trajectory"] = np.mean(
                successful_arr, axis=0
            ).tolist()
            result["successful_std_trajectory"] = np.std(
                successful_arr, axis=0
            ).tolist()

        if failed:
            failed_arr = np.array([a.journey_12d for a in failed])
            result["failed_mean_trajectory"] = np.mean(failed_arr, axis=0).tolist()
            result["failed_std_trajectory"] = np.std(failed_arr, axis=0).tolist()

        return result

    def extract_success_patterns(
        self, min_frequency: float = 0.1
    ) -> list[SuccessPattern]:
        """Extract patterns from successful attempts.

        Args:
            min_frequency: Minimum frequency threshold for patterns

        Returns:
            List of success patterns
        """
        successful = [a for a in self.attempts if a.success]

        if not successful:
            return []

        phi_scores = [a.phi_score for a in successful if a.phi_score is not None]
        coherence_values = [a.coherence for a in successful if a.coherence is not None]
        journeys = [a.journey_12d for a in successful if a.journey_12d]

        patterns: list[SuccessPattern] = []

        if phi_scores and coherence_values:
            phi_mean = np.mean(phi_scores)
            phi_std = np.std(phi_scores)
            coherence_mean = np.mean(coherence_values)
            coherence_std = np.std(coherence_values)

            patterns.append(
                SuccessPattern(
                    phi_score_range=(
                        max(0, phi_mean - phi_std),
                        min(1, phi_mean + phi_std),
                    ),
                    coherence_range=(
                        max(0, coherence_mean - coherence_std),
                        min(1, coherence_mean + coherence_std),
                    ),
                    journey_12d_mean=np.mean(journeys, axis=0).tolist()
                    if journeys
                    else [],
                    completion_prefix=self._extract_common_prefix(
                        [a.completion for a in successful if a.completion]
                    ),
                    frequency=1.0,
                )
            )

        return patterns

    def identify_failure_patterns(self) -> list[FailurePattern]:
        """Identify patterns from failed attempts.

        Returns:
            List of failure patterns
        """
        failed = [a for a in self.attempts if not a.success]

        if not failed:
            return []

        phi_scores = [a.phi_score for a in failed if a.phi_score is not None]
        coherence_values = [a.coherence for a in failed if a.coherence is not None]
        journeys = [a.journey_12d for a in failed if a.journey_12d]
        errors = [a.error for a in failed if a.error]

        patterns: list[FailurePattern] = []

        if phi_scores and coherence_values:
            phi_mean = np.mean(phi_scores)
            phi_std = np.std(phi_scores)
            coherence_mean = np.mean(coherence_values)
            coherence_std = np.std(coherence_values)

            common_errors: list[str] = []
            if errors:
                error_counts: dict[str, int] = {}
                for err in errors:
                    error_counts[err] = error_counts.get(err, 0) + 1
                common_errors = sorted(
                    error_counts.keys(), key=lambda x: error_counts[x], reverse=True
                )[:5]

            patterns.append(
                FailurePattern(
                    phi_score_range=(
                        max(0, phi_mean - phi_std),
                        min(1, phi_mean + phi_std),
                    ),
                    coherence_range=(
                        max(0, coherence_mean - coherence_std),
                        min(1, coherence_mean + coherence_std),
                    ),
                    common_errors=common_errors,
                    journey_12d_mean=np.mean(journeys, axis=0).tolist()
                    if journeys
                    else [],
                )
            )

        return patterns

    def _extract_common_prefix(self, strings: list[str]) -> str:
        """Extract common prefix from strings.

        Args:
            strings: List of strings

        Returns:
            Common prefix
        """
        if not strings:
            return ""

        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""

        return prefix

    def generate_recommendations(self) -> list[Recommendation]:
        """Generate recommendations based on pattern analysis.

        Returns:
            List of recommendations
        """
        recommendations: list[Recommendation] = []

        if not self.attempts:
            return recommendations

        analysis = self.analyze()
        correlations = analysis.get("correlations", [])

        phi_corr = next((c for c in correlations if c.metric == "phi_score"), None)
        coherence_corr = next(
            (c for c in correlations if c.metric == "coherence"), None
        )

        if phi_corr and phi_corr.phi_coefficient > 0.3:
            recommendations.append(
                Recommendation(
                    priority=1,
                    category="phi_score",
                    description="Focus on improving code structure (phi_score)",
                    evidence=[
                        f"phi_score has {phi_corr.interpretation}",
                        f"correlation with success: {phi_corr.phi_coefficient:.3f}",
                    ],
                )
            )

        if coherence_corr and coherence_corr.phi_coefficient > 0.3:
            recommendations.append(
                Recommendation(
                    priority=2,
                    category="coherence",
                    description="Improve code coherence and logical flow",
                    evidence=[
                        f"coherence has {coherence_corr.interpretation}",
                        f"correlation: {coherence_corr.phi_coefficient:.3f}",
                    ],
                )
            )

        phi_analysis = analysis.get("phi_score", {})
        if "successful" in phi_analysis and "failed" in phi_analysis:
            phi_diff = (
                phi_analysis["successful"]["mean"] - phi_analysis["failed"]["mean"]
            )
            if phi_diff > 0.1:
                recommendations.append(
                    Recommendation(
                        priority=3,
                        category="code_structure",
                        description="Adopt code patterns from successful attempts",
                        evidence=[
                            f"Success attempts have higher phi (+{phi_diff:.2f})",
                        ],
                    )
                )

        success_rate = analysis.get("success_rate", 0)
        if success_rate < 0.3:
            recommendations.append(
                Recommendation(
                    priority=1,
                    category="model",
                    description="Consider using a different or fine-tuned model",
                    evidence=[
                        f"Current success rate is only {success_rate:.1%}",
                    ],
                )
            )
        elif success_rate < 0.5:
            recommendations.append(
                Recommendation(
                    priority=2,
                    category="model",
                    description="Model may benefit from fine-tuning",
                    evidence=[
                        f"Current success rate is {success_rate:.1%}",
                    ],
                )
            )

        model_perf = analysis.get("model_performance", {})
        if model_perf:
            best_model = max(
                model_perf.items(),
                key=lambda x: x[1].get("success_rate", 0),
            )
            worst_model = min(
                model_perf.items(),
                key=lambda x: x[1].get("success_rate", 0),
            )

            if (
                best_model[1].get("success_rate", 0)
                > worst_model[1].get("success_rate", 0) + 0.2
            ):
                best_rate = best_model[1].get("success_rate", 0)
                worst_rate = worst_model[1].get("success_rate", 0)
                recommendations.append(
                    Recommendation(
                        priority=2,
                        category="model_selection",
                        description=f"Prefer {best_model[0]} over {worst_model[0]}",
                        evidence=[
                            f"best: {best_rate:.0f}, worst: {worst_rate:.0f}",
                        ],
                    )
                )

        duration_analysis = analysis.get("duration", {})
        if "successful" in duration_analysis and "failed" in duration_analysis:
            successful_duration = duration_analysis["successful"]["mean"]
            failed_duration = duration_analysis["failed"]["mean"]
            if failed_duration > successful_duration * 1.5:
                msg = (
                    f"Failed: {failed_duration:.0f}s vs ok: {successful_duration:.0f}s"
                )
                rec = Recommendation(
                    priority=3,
                    category="efficiency",
                    description="Failed attempts take longer - consider timeout",
                    evidence=[msg],
                )
                recommendations.append(rec)

        failure_patterns = self.identify_failure_patterns()
        if failure_patterns and failure_patterns[0].common_errors:
            recommendations.append(
                Recommendation(
                    priority=2,
                    category="error_handling",
                    description="Address common error patterns",
                    evidence=failure_patterns[0].common_errors[:3],
                )
            )

        recommendations.sort(key=lambda r: r.priority)

        return recommendations

    def get_successful_completions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get successful completions for pattern imitation.

        Args:
            limit: Maximum number of completions to return

        Returns:
            List of successful completions with metadata
        """
        successful = [a for a in self.attempts if a.success]

        sorted_successes = sorted(
            successful,
            key=lambda a: (a.phi_score or 0) + (a.coherence or 0),
            reverse=True,
        )

        return [
            {
                "task_id": a.task_id,
                "benchmark": a.benchmark,
                "model": a.model,
                "phi_score": a.phi_score,
                "coherence": a.coherence,
                "completion": a.completion,
                "journey_12d": a.journey_12d,
                "duration": a.duration,
            }
            for a in sorted_successes[:limit]
        ]

    def clear(self) -> None:
        """Clear all recorded attempts."""
        self.attempts.clear()
        logger.debug("Cleared all attempts from PatternAnalyzer")
