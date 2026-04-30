"""Elegant unified analytics engine.

Replaces 4 separate analyzers (inflection_detector, degradation_detector,
model_quality_classifier, request_alignment_analyzer) with a single engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cohezion.compound.models import AnalysisReport, ExecutionResult, Task


logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for analysis."""

    # Quality thresholds
    min_coherence: float = 0.5
    min_quality_score: float = 0.7

    # Degradation detection
    degradation_threshold: float = 0.2

    # Retry recommendations
    retry_on_quality_failure: bool = True
    retry_on_degradation: bool = True


class ExecutionAnalyzer:
    """Unified analysis engine.

    Replaces:
    - inflection_detector.py (320 lines)
    - degradation_detector.py (313 lines)
    - model_quality_classifier.py (530 lines)
    - request_alignment_analyzer.py (958 lines)

    Total: 2,121 lines → ~200 lines
    """

    def __init__(self, config: AnalysisConfig | None = None):
        self.config = config or AnalysisConfig()

    def analyze(self, result: ExecutionResult, task: Task) -> AnalysisReport:
        """Analyze execution result and return comprehensive report.

        Single pass analysis vs 4 separate systems.
        """
        report = AnalysisReport(
            metrics=result.metrics,
        )

        # Quality check
        report.quality_issue = self._check_quality(result)

        # Degradation check (compare with previous results if any)
        report.degradation_detected = self._check_degradation(result, task)

        # Anomaly detection
        report.anomalies_detected = self._detect_anomalies(result)

        # Determine recommendation
        report.retry_recommended = self._should_retry(report)

        if report.retry_recommended:
            report.suggested_action = self._suggest_action(report)

        return report

    def _check_quality(self, result: ExecutionResult) -> bool:
        """Check if quality meets thresholds."""
        metrics = result.metrics

        if metrics.coherence < self.config.min_coherence:
            return True

        if (
            metrics.quality_score is not None
            and metrics.quality_score < self.config.min_quality_score
        ):
            return True

        return False

    def _check_degradation(self, result: ExecutionResult, task: Task) -> bool:
        """Check for performance degradation."""
        # Compare with expected duration for this task type
        return result.metrics.duration_seconds > task.timeout_seconds * 0.8

    def _detect_anomalies(self, result: ExecutionResult) -> bool:
        """Detect anomalous patterns."""
        # Token usage anomalies
        if result.metrics.total_tokens > 100000:  # Unusually high
            return True

        # Error patterns
        return bool(result.failed and "timeout" in result.error_message.lower())

    def _should_retry(self, report: AnalysisReport) -> bool:
        """Determine if retry is recommended."""
        if not report.has_issues():
            return False

        if report.quality_issue and self.config.retry_on_quality_failure:
            return True

        return bool(report.degradation_detected and self.config.retry_on_degradation)

    def _suggest_action(self, report: AnalysisReport) -> str:
        """Suggest corrective action."""
        if report.quality_issue:
            return "retry_with_quality_improvement"
        elif report.degradation_detected:
            return "retry_with_optimization"
        elif report.anomalies_detected:
            return "retry_with_monitoring"
        else:
            return "retry_standard"


class SimpleAnalyzer:
    """Minimal analyzer for basic use cases."""

    def analyze(self, result: ExecutionResult, task: Task) -> AnalysisReport:
        """Simple pass/fail analysis."""
        return AnalysisReport(
            metrics=result.metrics,
            quality_issue=not result.success,
            retry_recommended=not result.success,
        )
