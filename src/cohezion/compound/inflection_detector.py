"""Detect critical inflection points in compound execution quality.

Monitors execution metrics and detects anomalies that indicate quality issues:
- Coherence drops (quality metric falls below threshold)
- Token efficiency drops (cache hit rate falls)
- Consecutive failures (error streak detection)
- Anomalous token consumption (unexpectedly high tokens)

Severity levels:
  INFO: Normal execution, metrics within bounds
  WARNING: Metrics slightly outside bounds, execution continues
  CRITICAL: Severe anomaly detected, re-execution recommended
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.compound.executor import ExecutionResult


logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for detected anomalies."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyDetection:
    """Result of anomaly detection analysis."""

    severity: Severity
    score: float  # Quality score (0.0-1.0)
    issues: list[str]  # List of detected issues
    recommendations: list[str]  # Recommended actions
    should_reexecute: bool  # Whether re-execution is recommended


class InflectionDetector:
    """Detect critical execution inflection points.

    Monitors execution quality and efficiency, recommending re-execution
    when anomalies indicate potential quality issues.
    """

    def __init__(
        self,
        coherence_threshold: float = 0.3,
        cache_hit_threshold: float = 0.2,
        token_limit_percentile: float = 0.9,
        failure_streak_limit: int = 3,
    ):
        """Initialize inflection detector.

        Args:
            coherence_threshold: Minimum acceptable coherence score (0.0-1.0)
            cache_hit_threshold: Minimum acceptable cache hit rate
            token_limit_percentile: Percentile for anomalous token consumption
            failure_streak_limit: Max consecutive failures before critical
        """
        self.coherence_threshold = coherence_threshold
        self.cache_hit_threshold = cache_hit_threshold
        self.token_limit_percentile = token_limit_percentile
        self.failure_streak_limit = failure_streak_limit

        # Track state for streak detection
        self.consecutive_failures = 0
        self.token_history: list[int] = []  # Recent token consumption
        self.coherence_history: list[float] = []  # Recent coherence scores

    def detect_anomaly(self, result: "ExecutionResult") -> AnomalyDetection:
        """Detect anomalies in execution result.

        Args:
            result: ExecutionResult from compound execution

        Returns:
            AnomalyDetection with severity, score, issues, recommendations
        """
        issues: list[str] = []
        score = 1.0
        severity = Severity.INFO

        # Check for execution failure
        if not result.success:
            self.consecutive_failures += 1
            issues.append(f"Execution failed (streak: {self.consecutive_failures})")
            score *= 0.5  # Penalize failure
        else:
            self.consecutive_failures = 0

        # Check coherence (if provided in metrics)
        if "coherence" in result.metrics:
            coherence = result.metrics["coherence"]
            if coherence < self.coherence_threshold:
                issues.append(f"Coherence low: {coherence:.2f} < {self.coherence_threshold}")
                score *= 0.6

            # Track coherence history
            self.coherence_history.append(coherence)
            if len(self.coherence_history) > 10:
                self.coherence_history.pop(0)

            # Detect coherence drop (trend analysis)
            if len(self.coherence_history) >= 4:
                # Compare last value to average of previous values
                current = self.coherence_history[-1]
                previous_avg = sum(self.coherence_history[:-1]) / (len(self.coherence_history) - 1)
                if previous_avg > 0 and current < previous_avg * 0.8:  # 20% drop
                    issues.append(f"Coherence trend down: {current:.2f} < {previous_avg:.2f}")
                    score *= 0.7

        # Check token efficiency (if token_metrics available)
        if result.token_metrics:
            cache_hit_rate = result.token_metrics.get("cache_hit_rate", 0.0)
            if cache_hit_rate < self.cache_hit_threshold:
                issues.append(
                    f"Cache hit rate low: {cache_hit_rate:.2f} < {self.cache_hit_threshold}"
                )
                score *= 0.7

            # Track token history
            tokens_used = result.token_metrics.get("tokens_used", 0)
            self.token_history.append(tokens_used)
            if len(self.token_history) > 10:
                self.token_history.pop(0)

            # Detect anomalous token consumption
            if len(self.token_history) > 3:
                avg_tokens = sum(self.token_history[:-1]) / len(self.token_history[:-1])
                if tokens_used > avg_tokens * 2:  # 2x normal consumption
                    issues.append(
                        f"Token consumption high: {tokens_used} > 2x avg ({avg_tokens:.0f})"
                    )
                    score *= 0.7

        # Determine severity based on issues and score
        if self.consecutive_failures >= self.failure_streak_limit:
            severity = Severity.CRITICAL
            if f"Failure streak: {self.consecutive_failures}" not in str(issues):
                issues.append(
                    f"Failure streak: {self.consecutive_failures} >= {self.failure_streak_limit}"
                )
            score = min(score, 0.2)  # Very low score
        elif len(issues) > 0 and score < 0.6:
            # Multiple issues or low score → critical
            severity = Severity.CRITICAL
        elif len(issues) > 0 and score < 0.75:
            # Some issues → warning
            severity = Severity.WARNING
        elif not result.success:
            # Any failure is at least warning
            severity = Severity.WARNING
        else:
            severity = Severity.INFO

        # Generate recommendations
        recommendations = self._generate_recommendations(result, issues, severity)

        return AnomalyDetection(
            severity=severity,
            score=score,
            issues=issues,
            recommendations=recommendations,
            should_reexecute=severity == Severity.CRITICAL,
        )

    def _generate_recommendations(
        self, result: "ExecutionResult", issues: list[str], severity: Severity
    ) -> list[str]:
        """Generate recommendations based on detected issues.

        Args:
            result: ExecutionResult
            issues: List of detected issues
            severity: Severity level of anomalies

        Returns:
            List of recommended actions
        """
        recommendations = []

        if not result.success:
            recommendations.append("Check error message for failure cause")
            recommendations.append("Verify task dependencies and inputs")

        if "Coherence" in str(issues):
            recommendations.append("Consider using more specific task description")
            recommendations.append("Review experience guidance for similar tasks")

        if "Cache hit rate low" in str(issues):
            recommendations.append("Task may be using diverse/unique prompts")
            recommendations.append("Caching less effective for this task type")

        if "Token consumption high" in str(issues):
            recommendations.append("Reduce context size or use summary")
            recommendations.append("Consider chunking large inputs")

        if severity == Severity.CRITICAL:
            recommendations.append("Re-execution recommended with adjusted parameters")
            recommendations.append("Log as critical inflection point for analysis")

        return recommendations

    def compute_quality_score(self, result: "ExecutionResult") -> float:
        """Compute overall quality score (0.0-1.0).

        Combines:
        - Success: execution success/failure
        - Coherence: quality metric (if provided)
        - Efficiency: token efficiency (if provided)

        Args:
            result: ExecutionResult

        Returns:
            Quality score (0.0-1.0, higher is better)
        """
        score = 1.0

        # Success component (50% weight)
        success_score = 1.0 if result.success else 0.0
        score *= success_score**0.5

        # Coherence component (30% weight)
        if "coherence" in result.metrics:
            coherence = result.metrics["coherence"]
            coherence_score = max(0.0, min(1.0, coherence))
            score *= coherence_score**0.3

        # Efficiency component (20% weight)
        if result.token_metrics:
            cache_hit_rate = result.token_metrics.get("cache_hit_rate", 0.0)
            # Normalize: 0 hits = 0.0, 100% hits = 1.0
            efficiency_score = max(0.0, min(1.0, cache_hit_rate))
            score *= efficiency_score**0.2

        return round(score, 4)

    def detect_critical(self, result: "ExecutionResult") -> bool:
        """Quick check for critical severity (convenience method).

        Args:
            result: ExecutionResult

        Returns:
            True if critical severity detected
        """
        anomaly = self.detect_anomaly(result)
        return anomaly.severity == Severity.CRITICAL

    def reset_state(self) -> None:
        """Reset internal state (failure streak, history).

        Call after re-execution or successful recovery.
        """
        self.consecutive_failures = 0
        self.token_history.clear()
        self.coherence_history.clear()
        logger.debug("InflectionDetector state reset")


class InflectionDetectorFactory:
    """Factory for creating inflection detectors with sensible defaults."""

    @staticmethod
    def create_strict() -> InflectionDetector:
        """Create detector with strict thresholds (high quality demands).

        Returns:
            InflectionDetector with strict settings
        """
        return InflectionDetector(
            coherence_threshold=0.7,  # High coherence requirement
            cache_hit_threshold=0.5,  # High cache efficiency requirement
            failure_streak_limit=1,  # Intolerant of failures
        )

    @staticmethod
    def create_moderate() -> InflectionDetector:
        """Create detector with moderate thresholds (balanced).

        Returns:
            InflectionDetector with moderate settings
        """
        return InflectionDetector(
            coherence_threshold=0.4,  # Moderate coherence
            cache_hit_threshold=0.3,  # Some caching expected
            failure_streak_limit=2,  # Allow 1 failure
        )

    @staticmethod
    def create_lenient() -> InflectionDetector:
        """Create detector with lenient thresholds (high tolerance).

        Returns:
            InflectionDetector with lenient settings
        """
        return InflectionDetector(
            coherence_threshold=0.2,  # Low coherence threshold
            cache_hit_threshold=0.1,  # Low cache requirement
            failure_streak_limit=3,  # Allow 2 failures
        )

    @staticmethod
    def create_default() -> InflectionDetector:
        """Create detector with default thresholds.

        Returns:
            InflectionDetector with default settings
        """
        return InflectionDetector()
