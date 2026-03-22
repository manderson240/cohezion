"""Comprehensive tests for compound analytics engine.

Tests the unified analysis engine (replaces 4 separate analyzers).
Generated for P0 coverage.
"""

from __future__ import annotations

import pytest

from cohezion.compound.analytics.engine import (
    AnalysisConfig,
    ExecutionAnalyzer,
    SimpleAnalyzer,
)
from cohezion.compound.models import (
    AnalysisReport,
    ExecutionMetrics,
    ExecutionResult,
    Task,
)


class TestAnalysisConfig:
    """[P0] Tests for AnalysisConfig."""

    def test_default_values(self):
        """[P0] Should have sensible defaults."""
        config = AnalysisConfig()

        assert config.min_coherence == 0.5
        assert config.min_quality_score == 0.7
        assert config.degradation_threshold == 0.2
        assert config.retry_on_quality_failure is True
        assert config.retry_on_degradation is True

    def test_custom_thresholds(self):
        """[P0] Should accept custom thresholds."""
        config = AnalysisConfig(
            min_coherence=0.8,
            min_quality_score=0.9,
            degradation_threshold=0.3,
        )

        assert config.min_coherence == 0.8
        assert config.min_quality_score == 0.9
        assert config.degradation_threshold == 0.3

    def test_retry_settings(self):
        """[P0] Should configure retry behavior."""
        config = AnalysisConfig(
            retry_on_quality_failure=False,
            retry_on_degradation=False,
        )

        assert config.retry_on_quality_failure is False
        assert config.retry_on_degradation is False


class TestExecutionAnalyzerInitialization:
    """[P0] Tests for analyzer initialization."""

    def test_initializes_with_defaults(self):
        """[P0] Should initialize with default config."""
        analyzer = ExecutionAnalyzer()

        assert analyzer.config is not None
        assert analyzer.config.min_coherence == 0.5

    def test_initializes_with_custom_config(self):
        """[P0] Should accept custom config."""
        config = AnalysisConfig(min_coherence=0.8)
        analyzer = ExecutionAnalyzer(config=config)

        assert analyzer.config.min_coherence == 0.8


class TestExecutionAnalyzerQualityCheck:
    """[P0] Tests for quality checking."""

    @pytest.fixture()
    def analyzer(self):
        return ExecutionAnalyzer()

    @pytest.fixture()
    def task(self):
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_high_coherence_passes(self, analyzer, task):
        """[P0] Should pass high coherence results."""
        result = ExecutionResult(
            success=True,
            output="good output",
            metrics=ExecutionMetrics(coherence=0.9),
        )

        report = analyzer.analyze(result, task)

        assert report.quality_issue is False
        assert report.has_issues() is False

    def test_low_coherence_fails(self, analyzer, task):
        """[P0] Should detect low coherence."""
        result = ExecutionResult(
            success=True,
            output="poor output",
            metrics=ExecutionMetrics(coherence=0.3),
        )

        report = analyzer.analyze(result, task)

        assert report.quality_issue is True
        assert report.has_issues() is True

    def test_coherence_at_threshold(self, analyzer, task):
        """[P0] Should handle coherence at threshold."""
        result = ExecutionResult(
            success=True,
            output="borderline",
            metrics=ExecutionMetrics(coherence=0.5),  # At threshold
        )

        report = analyzer.analyze(result, task)

        # Should NOT flag quality issue at exact threshold
        assert report.quality_issue is False

    def test_low_quality_score_fails(self, analyzer, task):
        """[P0] Should detect low quality score."""
        result = ExecutionResult(
            success=True,
            output="low quality",
            metrics=ExecutionMetrics(
                coherence=0.8,  # Good coherence
                quality_score=0.5,  # But low quality
            ),
        )

        report = analyzer.analyze(result, task)

        assert report.quality_issue is True

    def test_high_quality_score_passes(self, analyzer, task):
        """[P0] Should pass high quality score."""
        result = ExecutionResult(
            success=True,
            output="high quality",
            metrics=ExecutionMetrics(
                coherence=0.8,
                quality_score=0.9,
            ),
        )

        report = analyzer.analyze(result, task)

        assert report.quality_issue is False

    def test_no_quality_score_skips_check(self, analyzer, task):
        """[P0] Should skip quality check when None."""
        result = ExecutionResult(
            success=True,
            output="no quality score",
            metrics=ExecutionMetrics(
                coherence=0.8,
                quality_score=None,
            ),
        )

        report = analyzer.analyze(result, task)

        # Only coherence check applies
        assert report.quality_issue is False


class TestExecutionAnalyzerDegradation:
    """[P0] Tests for degradation detection."""

    @pytest.fixture()
    def task(self):
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
            timeout_seconds=10.0,
        )

    def test_normal_duration_passes(self):
        """[P0] Should pass normal duration."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="done",
            metrics=ExecutionMetrics(duration_seconds=2.0),
        )
        task = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task)

        assert report.degradation_detected is False

    def test_high_duration_detected(self):
        """[P0] Should detect high duration."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="slow",
            metrics=ExecutionMetrics(duration_seconds=8.5),  # 85% of timeout
        )
        task = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task)

        assert report.degradation_detected is True

    def test_duration_at_threshold(self):
        """[P0] Should handle duration above 80% threshold."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="above threshold",
            metrics=ExecutionMetrics(duration_seconds=8.1),  # 81% of timeout
        )
        task = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task)

        # Above 80% should trigger degradation
        assert report.degradation_detected is True


class TestExecutionAnalyzerAnomalies:
    """[P0] Tests for anomaly detection."""

    @pytest.fixture()
    def analyzer(self):
        return ExecutionAnalyzer()

    @pytest.fixture()
    def task(self):
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_normal_tokens_pass(self, analyzer, task):
        """[P0] Should pass normal token count."""
        result = ExecutionResult(
            success=True,
            output="normal",
            metrics=ExecutionMetrics(total_tokens=1000),
        )

        report = analyzer.analyze(result, task)

        assert report.anomalies_detected is False

    def test_excessive_tokens_detected(self, analyzer, task):
        """[P0] Should detect excessive token usage."""
        result = ExecutionResult(
            success=True,
            output="too many tokens",
            metrics=ExecutionMetrics(total_tokens=150000),  # Very high
        )

        report = analyzer.analyze(result, task)

        assert report.anomalies_detected is True

    def test_timeout_error_detected(self, analyzer, task):
        """[P0] Should detect timeout errors."""
        result = ExecutionResult(
            success=False,
            output="Request timeout after 30s",
            error_type="TimeoutError",
            error_message="Request timeout after 30s",
            metrics=ExecutionMetrics(),
        )

        report = analyzer.analyze(result, task)

        assert report.anomalies_detected is True

    def test_success_no_anomalies(self, analyzer, task):
        """[P0] Should not flag anomalies on success."""
        result = ExecutionResult(
            success=True,
            output="success",
            metrics=ExecutionMetrics(total_tokens=500),
        )

        report = analyzer.analyze(result, task)

        assert report.anomalies_detected is False


class TestExecutionAnalyzerRetryRecommendation:
    """[P0] Tests for retry recommendations."""

    @pytest.fixture()
    def task(self):
        return Task(
            id="test-1",
            description="Test task",
            skill_name="test-skill",
            operation_type="generate",
        )

    def test_retry_on_quality_failure(self, task):
        """[P0] Should recommend retry on quality failure."""
        analyzer = ExecutionAnalyzer(config=AnalysisConfig(retry_on_quality_failure=True))
        result = ExecutionResult(
            success=True,
            output="low quality",
            metrics=ExecutionMetrics(coherence=0.3),
        )

        report = analyzer.analyze(result, task)

        assert report.retry_recommended is True

    def test_no_retry_when_disabled(self, task):
        """[P0] Should not recommend retry when disabled."""
        analyzer = ExecutionAnalyzer(config=AnalysisConfig(retry_on_quality_failure=False))
        result = ExecutionResult(
            success=True,
            output="low quality",
            metrics=ExecutionMetrics(coherence=0.3),
        )

        report = analyzer.analyze(result, task)

        assert report.retry_recommended is False

    def test_retry_on_degradation(self, task):
        """[P0] Should recommend retry on degradation."""
        analyzer = ExecutionAnalyzer(config=AnalysisConfig(retry_on_degradation=True))
        result = ExecutionResult(
            success=True,
            output="slow",
            metrics=ExecutionMetrics(duration_seconds=9.0),
        )
        task_with_timeout = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task_with_timeout)

        assert report.retry_recommended is True

    def test_no_retry_when_no_issues(self, task):
        """[P0] Should not recommend retry when no issues."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="good",
            metrics=ExecutionMetrics(
                coherence=0.9,
                duration_seconds=1.0,
            ),
        )
        task_with_timeout = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task_with_timeout)

        assert report.retry_recommended is False

    def test_suggested_action_on_quality(self, task):
        """[P0] Should suggest action for quality issues."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="low quality",
            metrics=ExecutionMetrics(coherence=0.3),
        )

        report = analyzer.analyze(result, task)

        assert report.suggested_action == "retry_with_quality_improvement"

    def test_suggested_action_on_degradation(self, task):
        """[P0] Should suggest action for degradation (with quality passing)."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="slow",
            metrics=ExecutionMetrics(
                coherence=0.8,  # Good quality
                quality_score=0.9,  # Good quality
                duration_seconds=8.5,
            ),
        )
        task_with_timeout = Task(
            id="t1",
            description="",
            skill_name="",
            operation_type="",
            timeout_seconds=10.0,
        )

        report = analyzer.analyze(result, task_with_timeout)

        # Only degradation detected (no quality issue)
        assert report.degradation_detected is True
        assert report.quality_issue is False
        assert report.suggested_action == "retry_with_optimization"


class TestExecutionAnalyzerReport:
    """[P0] Tests for analysis report generation."""

    def test_report_includes_metrics(self):
        """[P0] Should include metrics in report."""
        analyzer = ExecutionAnalyzer()
        result = ExecutionResult(
            success=True,
            output="test",
            metrics=ExecutionMetrics(
                coherence=0.8,
                duration_seconds=1.5,
                total_tokens=1000,
            ),
        )
        task = Task(id="t1", description="", skill_name="", operation_type="")

        report = analyzer.analyze(result, task)

        assert report.metrics.coherence == 0.8
        assert report.metrics.duration_seconds == 1.5
        assert report.metrics.total_tokens == 1000

    def test_has_issues_true_when_any_issue(self):
        """[P0] Should detect any issue."""
        report = AnalysisReport(
            anomalies_detected=True,
            degradation_detected=False,
            quality_issue=False,
        )

        assert report.has_issues() is True

    def test_has_issues_false_when_none(self):
        """[P0] Should report no issues when clean."""
        report = AnalysisReport(
            anomalies_detected=False,
            degradation_detected=False,
            quality_issue=False,
        )

        assert report.has_issues() is False


class TestSimpleAnalyzer:
    """[P1] Tests for SimpleAnalyzer."""

    def test_simple_pass_analysis(self):
        """[P1] Should analyze successful result."""
        analyzer = SimpleAnalyzer()
        result = ExecutionResult(
            success=True,
            output="success",
            metrics=ExecutionMetrics(),
        )
        task = Task(id="t1", description="", skill_name="", operation_type="")

        report = analyzer.analyze(result, task)

        assert report.quality_issue is False
        assert report.retry_recommended is False

    def test_simple_fail_analysis(self):
        """[P1] Should analyze failed result."""
        analyzer = SimpleAnalyzer()
        result = ExecutionResult(
            success=False,
            output="error",
            metrics=ExecutionMetrics(),
        )
        task = Task(id="t1", description="", skill_name="", operation_type="")

        report = analyzer.analyze(result, task)

        assert report.quality_issue is True
        assert report.retry_recommended is True
