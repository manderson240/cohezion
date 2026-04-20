"""Tests for InflectionDetector - anomaly detection and quality scoring."""

import pytest

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.inflection_detector import (
    AnomalyDetection,
    InflectionDetector,
    InflectionDetectorFactory,
    Severity,
)


@pytest.fixture
def detector():
    """Create default inflection detector."""
    return InflectionDetector()


@pytest.fixture
def successful_result():
    """Create successful execution result."""
    return ExecutionResult(
        success=True,
        output="Generated 10 items",
        metrics={"coherence": 0.8},
        duration_seconds=1.5,
        token_metrics={
            "tokens_used": 500,
            "api_calls_made": 5,
            "cache_hits": 15,
            "cache_misses": 5,
            "cache_hit_rate": 0.75,
        },
    )


@pytest.fixture
def failed_result():
    """Create failed execution result."""
    return ExecutionResult(
        success=False,
        output="Error: Generation failed",
        metrics={"error": "Ollama timeout"},
        duration_seconds=0.5,
    )


class TestAnomalyDetection:
    """Tests for anomaly detection."""

    def test_successful_execution_normal(self, detector, successful_result):
        """Test detection on successful, normal execution."""
        anomaly = detector.detect_anomaly(successful_result)

        assert anomaly.severity == Severity.INFO
        assert len(anomaly.issues) == 0
        assert anomaly.score > 0.8
        assert not anomaly.should_reexecute

    def test_failed_execution_is_critical(self, detector, failed_result):
        """Test detection on failed execution."""
        anomaly = detector.detect_anomaly(failed_result)

        # Single failure is at least WARNING
        assert anomaly.severity in (Severity.WARNING, Severity.CRITICAL)
        assert "failed" in str(anomaly.issues).lower()
        assert len(anomaly.recommendations) > 0

    def test_low_coherence_detected(self, detector):
        """Test detection of low coherence."""
        result = ExecutionResult(
            success=True,
            output="Generated",
            metrics={"coherence": 0.15},  # Below default threshold of 0.3
            duration_seconds=1.0,
        )

        anomaly = detector.detect_anomaly(result)

        assert anomaly.severity != Severity.INFO
        assert "Coherence" in str(anomaly.issues)
        assert anomaly.score < 0.8

    def test_low_cache_hit_rate_detected(self, detector):
        """Test detection of low cache hit rate."""
        result = ExecutionResult(
            success=True,
            output="Generated",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
            token_metrics={
                "tokens_used": 1000,
                "api_calls_made": 8,
                "cache_hits": 2,
                "cache_misses": 8,
                "cache_hit_rate": 0.1,  # Below default threshold of 0.2
            },
        )

        anomaly = detector.detect_anomaly(result)

        assert "Cache hit rate low" in str(anomaly.issues)
        assert anomaly.score < 0.9

    def test_anomalous_token_consumption(self, detector):
        """Test detection of unusually high token consumption."""
        # Build token history first
        for i in range(5):
            result = ExecutionResult(
                success=True,
                output="Test",
                metrics={},
                duration_seconds=1.0,
                token_metrics={
                    "tokens_used": 100 + (i * 10),  # Normal range
                    "cache_hit_rate": 0.5,
                },
            )
            detector.detect_anomaly(result)

        # Now spike
        spike_result = ExecutionResult(
            success=True,
            output="Generated",
            metrics={},
            duration_seconds=1.0,
            token_metrics={
                "tokens_used": 500,  # 2x normal
                "cache_hit_rate": 0.5,
            },
        )

        anomaly = detector.detect_anomaly(spike_result)

        assert "Token consumption high" in str(anomaly.issues)
        assert anomaly.score < 0.95

    def test_failure_streak_detection(self, detector):
        """Test detection of consecutive failures."""
        assert detector.consecutive_failures == 0

        # First failure
        result1 = ExecutionResult(
            success=False,
            output="Error",
            metrics={},
            duration_seconds=0.5,
        )
        detector.detect_anomaly(result1)
        assert detector.consecutive_failures == 1

        # Second failure
        result2 = ExecutionResult(
            success=False,
            output="Error",
            metrics={},
            duration_seconds=0.5,
        )
        detector.detect_anomaly(result2)
        assert detector.consecutive_failures == 2

        # Third failure (critical threshold)
        result3 = ExecutionResult(
            success=False,
            output="Error",
            metrics={},
            duration_seconds=0.5,
        )
        anomaly3 = detector.detect_anomaly(result3)
        assert detector.consecutive_failures == 3
        assert anomaly3.severity == Severity.CRITICAL

    def test_failure_streak_reset_on_success(self, detector):
        """Test that failure streak resets on successful execution."""
        # Build up failure streak
        for _ in range(2):
            result = ExecutionResult(
                success=False,
                output="Error",
                metrics={},
                duration_seconds=0.5,
            )
            detector.detect_anomaly(result)

        assert detector.consecutive_failures == 2

        # Success resets streak
        result = ExecutionResult(
            success=True,
            output="Success",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
        )
        detector.detect_anomaly(result)

        assert detector.consecutive_failures == 0

    def test_coherence_trend_detection(self, detector):
        """Test detection of coherence trend (downward)."""
        # Build history of high coherence (need >= 4 for trend detection)
        for coherence in [0.9, 0.85, 0.88, 0.87]:
            result = ExecutionResult(
                success=True,
                output="Test",
                metrics={"coherence": coherence},
                duration_seconds=1.0,
            )
            detector.detect_anomaly(result)

        # Then drop (20%+ drop from average)
        result_drop = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.65},  # Down from ~0.875 average
            duration_seconds=1.0,
        )
        anomaly = detector.detect_anomaly(result_drop)

        # Should detect trend
        assert any("Coherence trend" in issue for issue in anomaly.issues)

    def test_reexecute_recommendation_on_critical(self, detector):
        """Test that critical severity includes re-execute recommendation."""
        # Trigger critical with multiple consecutive failures
        for _ in range(3):
            result = ExecutionResult(
                success=False,
                output="Error",
                metrics={},
                duration_seconds=0.5,
            )
            detector.detect_anomaly(result)

        result = ExecutionResult(
            success=False,
            output="Error",
            metrics={},
            duration_seconds=0.5,
        )
        anomaly = detector.detect_anomaly(result)

        assert anomaly.should_reexecute
        assert any("re-execution" in r.lower() for r in anomaly.recommendations)


class TestQualityScoring:
    """Tests for quality score computation."""

    def test_perfect_execution_score(self, detector, successful_result):
        """Test quality score on perfect execution."""
        score = detector.compute_quality_score(successful_result)

        assert 0.0 <= score <= 1.0
        assert score > 0.8  # High score for successful execution

    def test_failed_execution_score(self, detector, failed_result):
        """Test quality score on failed execution."""
        score = detector.compute_quality_score(failed_result)

        assert score < 0.5  # Low score for failure

    def test_low_coherence_score(self, detector):
        """Test quality score reflects low coherence."""
        result_low = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.2},
            duration_seconds=1.0,
        )
        result_high = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.9},
            duration_seconds=1.0,
        )

        score_low = detector.compute_quality_score(result_low)
        score_high = detector.compute_quality_score(result_high)

        assert score_low < score_high

    def test_low_cache_efficiency_score(self, detector):
        """Test quality score reflects low cache efficiency."""
        result_low_cache = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
            token_metrics={
                "tokens_used": 1000,
                "cache_hit_rate": 0.1,
            },
        )
        result_high_cache = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
            token_metrics={
                "tokens_used": 500,
                "cache_hit_rate": 0.9,
            },
        )

        score_low = detector.compute_quality_score(result_low_cache)
        score_high = detector.compute_quality_score(result_high_cache)

        assert score_low < score_high

    def test_quality_score_bounds(self, detector, successful_result):
        """Test quality score always in [0, 1]."""
        score = detector.compute_quality_score(successful_result)

        assert 0.0 <= score <= 1.0


class TestDetectCritical:
    """Tests for detect_critical convenience method."""

    def test_critical_detection_convenience(self, detector):
        """Test detect_critical convenience method."""
        # Build failure streak
        for _ in range(3):
            result = ExecutionResult(
                success=False,
                output="Error",
                metrics={},
                duration_seconds=0.5,
            )
            detector.detect_anomaly(result)

        # Final failure
        result = ExecutionResult(
            success=False,
            output="Error",
            metrics={},
            duration_seconds=0.5,
        )

        assert detector.detect_critical(result) is True

    def test_non_critical_execution(self, detector, successful_result):
        """Test detect_critical returns False for normal execution."""
        assert detector.detect_critical(successful_result) is False


class TestStateManagement:
    """Tests for detector state management."""

    def test_reset_state_clears_history(self, detector):
        """Test that reset_state clears internal state."""
        # Build state
        for _ in range(2):
            result = ExecutionResult(
                success=False,
                output="Error",
                metrics={},
                duration_seconds=0.5,
            )
            detector.detect_anomaly(result)

        assert detector.consecutive_failures == 2

        # Reset
        detector.reset_state()

        assert detector.consecutive_failures == 0
        assert len(detector.token_history) == 0
        assert len(detector.coherence_history) == 0

    def test_history_size_limited(self, detector):
        """Test that history doesn't grow unbounded."""
        # Add many results
        for i in range(20):
            result = ExecutionResult(
                success=True,
                output="Test",
                metrics={"coherence": 0.5 + (i * 0.01)},
                duration_seconds=1.0,
                token_metrics={
                    "tokens_used": 100 + i,
                    "cache_hit_rate": 0.5,
                },
            )
            detector.detect_anomaly(result)

        # History should be limited to 10
        assert len(detector.coherence_history) <= 10
        assert len(detector.token_history) <= 10


class TestInflectionDetectorFactory:
    """Tests for detector factory."""

    def test_factory_create_strict(self):
        """Test factory creates strict detector."""
        detector = InflectionDetectorFactory.create_strict()

        assert detector.coherence_threshold == 0.7
        assert detector.cache_hit_threshold == 0.5
        assert detector.failure_streak_limit == 1

    def test_factory_create_moderate(self):
        """Test factory creates moderate detector."""
        detector = InflectionDetectorFactory.create_moderate()

        assert detector.coherence_threshold == 0.4
        assert detector.cache_hit_threshold == 0.3
        assert detector.failure_streak_limit == 2

    def test_factory_create_lenient(self):
        """Test factory creates lenient detector."""
        detector = InflectionDetectorFactory.create_lenient()

        assert detector.coherence_threshold == 0.2
        assert detector.cache_hit_threshold == 0.1
        assert detector.failure_streak_limit == 3

    def test_factory_create_default(self):
        """Test factory creates default detector."""
        detector = InflectionDetectorFactory.create_default()

        assert detector.coherence_threshold == 0.3
        assert detector.cache_hit_threshold == 0.2
        assert detector.failure_streak_limit == 3

    def test_strict_detector_more_critical(self):
        """Test that strict detector is more critical."""
        strict = InflectionDetectorFactory.create_strict()
        lenient = InflectionDetectorFactory.create_lenient()

        result = ExecutionResult(
            success=True,
            output="Test",
            metrics={"coherence": 0.35},  # Between strict and lenient thresholds
            duration_seconds=1.0,
        )

        strict_anomaly = strict.detect_anomaly(result)
        lenient_anomaly = lenient.detect_anomaly(result)

        assert strict_anomaly.score <= lenient_anomaly.score


class TestAnomalyDetectionDataclass:
    """Tests for AnomalyDetection dataclass."""

    def test_anomaly_detection_creation(self):
        """Test creating AnomalyDetection instance."""
        anomaly = AnomalyDetection(
            severity=Severity.CRITICAL,
            score=0.3,
            issues=["Issue 1", "Issue 2"],
            recommendations=["Fix A", "Fix B"],
            should_reexecute=True,
        )

        assert anomaly.severity == Severity.CRITICAL
        assert anomaly.score == 0.3
        assert len(anomaly.issues) == 2
        assert len(anomaly.recommendations) == 2
        assert anomaly.should_reexecute is True

    def test_anomaly_detection_severity_comparison(self):
        """Test Severity enum values."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"
