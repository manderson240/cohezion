"""Tests for degradation detection module - Phase 5A.6."""

import time

import pytest

from cohezion.compound.degradation_detector import (
    AlertSeverity,
    DegradationAlert,
    DegradationDetector,
    MetricBaseline,
)


@pytest.fixture
def detector():
    """Create degradation detector for testing."""
    return DegradationDetector(
        cache_hit_rate_threshold=0.50,
        token_efficiency_drop_threshold=0.10,
        coherence_threshold=0.60,
        duration_slowdown_threshold=0.25,
    )


@pytest.fixture
def baseline():
    """Create metric baseline for testing."""
    return MetricBaseline("test_metric", window_size=10, min_samples=3)


class TestMetricBaseline:
    """Test MetricBaseline statistics tracking."""

    def test_initialization(self, baseline):
        """Test baseline initialization."""
        assert baseline.metric_name == "test_metric"
        assert len(baseline.samples) == 0
        assert baseline.is_established is False

    def test_add_sample(self, baseline):
        """Test adding samples."""
        baseline.add_sample(100.0)
        assert len(baseline.samples) == 1
        assert baseline.samples[0] == 100.0

    def test_mean_calculation(self, baseline):
        """Test mean calculation."""
        baseline.add_sample(100.0)
        baseline.add_sample(200.0)
        baseline.add_sample(300.0)

        assert baseline.mean == pytest.approx(200.0)
        assert baseline.is_established is True

    def test_std_dev_calculation(self, baseline):
        """Test standard deviation calculation."""
        baseline.add_sample(100.0)
        baseline.add_sample(100.0)
        baseline.add_sample(100.0)

        assert baseline.std_dev == pytest.approx(0.0)

    def test_lower_bound(self, baseline):
        """Test lower bound calculation."""
        baseline.add_sample(100.0)
        baseline.add_sample(120.0)
        baseline.add_sample(100.0)

        lower = baseline.lower_bound(std_devs=1.0)
        # Mean ≈ 106.67, std ≈ 11.55, lower = mean - std
        assert lower < baseline.mean

    def test_window_size_enforcement(self):
        """Test that window size is enforced."""
        baseline = MetricBaseline("test", window_size=3, min_samples=1)

        # Add 5 samples
        for i in range(5):
            baseline.add_sample(float(i))

        # Should keep only last 3
        recent_mean = baseline.mean
        # Last 3 samples: 2, 3, 4 → mean = 3
        assert recent_mean == pytest.approx(3.0)


class TestDegradationDetector:
    """Test DegradationDetector core functionality."""

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.cache_hit_rate_threshold == 0.50
        assert detector.token_efficiency_drop_threshold == 0.10
        assert detector.coherence_threshold == 0.60

    def test_no_alerts_when_healthy(self, detector):
        """Test no alerts when metrics are healthy."""
        metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        # Need to establish baseline first (5 samples)
        for _ in range(5):
            alerts = detector.check_degradation(metrics)
        assert len(alerts) == 0

    def test_alert_on_low_cache_hit_rate(self, detector):
        """Test alert when cache hit rate drops below threshold."""
        # Establish baseline with healthy metrics
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Now drop cache hit rate
        degraded_metrics = {
            "combined_hit_rate": 0.30,  # Below threshold 0.50
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        alerts = detector.check_degradation(degraded_metrics)
        assert len(alerts) > 0
        assert alerts[0].metric == "cache_hit_rate"
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_alert_on_token_efficiency_drop(self, detector):
        """Test alert when token efficiency drops."""
        # Establish baseline with 1000 tok/sec
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Drop to 850 tok/sec (15% drop, above 10% threshold)
        degraded_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 850.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        alerts = detector.check_degradation(degraded_metrics)
        efficiency_alerts = [a for a in alerts if a.metric == "token_efficiency"]
        assert len(efficiency_alerts) > 0
        assert efficiency_alerts[0].severity == AlertSeverity.WARNING

    def test_alert_on_low_coherence(self, detector):
        """Test critical alert when coherence drops below threshold."""
        # Establish baseline with high coherence
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Drop coherence below threshold
        degraded_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.50,  # Below threshold 0.60
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        alerts = detector.check_degradation(degraded_metrics)
        coherence_alerts = [a for a in alerts if a.metric == "coherence"]
        assert len(coherence_alerts) > 0
        assert coherence_alerts[0].severity == AlertSeverity.CRITICAL

    def test_alert_on_duration_slowdown(self, detector):
        """Test alert when execution duration increases."""
        # Establish baseline with 1.0s duration
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Increase duration by 30% (above 25% threshold)
        degraded_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.3,  # 30% slowdown
            "success_rate": 1.0,
        }

        alerts = detector.check_degradation(degraded_metrics)
        duration_alerts = [a for a in alerts if a.metric == "duration"]
        assert len(duration_alerts) > 0
        assert duration_alerts[0].severity == AlertSeverity.WARNING

    def test_alert_on_success_rate_drop(self, detector):
        """Test critical alert when success rate drops."""
        # Establish baseline with 100% success
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Drop success rate by 25% (above 20% threshold)
        degraded_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 0.75,  # 25% drop
        }

        alerts = detector.check_degradation(degraded_metrics)
        success_alerts = [a for a in alerts if a.metric == "success_rate"]
        assert len(success_alerts) > 0
        assert success_alerts[0].severity == AlertSeverity.CRITICAL

    def test_multiple_simultaneous_alerts(self, detector):
        """Test multiple degradation alerts simultaneously."""
        # Establish healthy baseline
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # Degrade multiple metrics
        degraded_metrics = {
            "combined_hit_rate": 0.30,  # Low cache
            "tokens_per_second": 800.0,  # Low efficiency
            "mean_coherence": 0.50,  # Low coherence
            "elapsed_seconds": 1.5,  # Slow
            "success_rate": 0.70,  # Low success
        }

        alerts = detector.check_degradation(degraded_metrics)
        # Should have multiple alerts
        assert len(alerts) >= 3
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) >= 2


class TestAlertCooldown:
    """Test alert cooldown enforcement."""

    def test_alert_cooldown_prevents_duplicates(self, detector):
        """Test that same alert doesn't repeat within cooldown period."""
        # Establish baseline
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # First degradation
        degraded_metrics = {
            "combined_hit_rate": 0.30,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        alerts1 = detector.check_degradation(degraded_metrics)
        assert len(alerts1) > 0

        # Immediate second check should not alert (cooldown active)
        alerts2 = detector.check_degradation(degraded_metrics)
        assert len(alerts2) == 0

    def test_alert_resumes_after_cooldown(self, detector):
        """Test that alerts resume after cooldown period."""
        detector._alert_cooldown_seconds = 0.1  # 100ms for testing

        # Establish baseline
        healthy_metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(healthy_metrics)

        # First degradation
        degraded_metrics = {
            "combined_hit_rate": 0.30,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }

        alerts1 = detector.check_degradation(degraded_metrics)
        assert len(alerts1) > 0

        # Wait for cooldown
        time.sleep(0.15)

        # Should alert again after cooldown
        alerts2 = detector.check_degradation(degraded_metrics)
        assert len(alerts2) > 0


class TestDegradationAlert:
    """Test DegradationAlert dataclass."""

    def test_alert_creation(self):
        """Test creating a degradation alert."""
        alert = DegradationAlert(
            metric="cache_hit_rate",
            severity=AlertSeverity.WARNING,
            message="Cache hit rate too low",
            current_value=0.30,
            baseline_value=0.75,
            threshold=0.50,
        )

        assert alert.metric == "cache_hit_rate"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 0.30
        assert alert.baseline_value == 0.75

    def test_critical_alert(self):
        """Test creating a critical alert."""
        alert = DegradationAlert(
            metric="coherence",
            severity=AlertSeverity.CRITICAL,
            message="Coherence critical",
            current_value=0.50,
            baseline_value=0.85,
            threshold=0.60,
        )

        assert alert.severity == AlertSeverity.CRITICAL


class TestBaselineStatistics:
    """Test baseline statistics reporting."""

    def test_get_baseline_stats(self, detector):
        """Test retrieving baseline statistics."""
        # Establish baselines
        metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(metrics)

        stats = detector.get_baseline_stats()

        assert "cache_hit_rate" in stats
        assert stats["cache_hit_rate"]["is_established"] is True
        assert stats["cache_hit_rate"]["num_samples"] == 5
        assert "mean" in stats["cache_hit_rate"]
        assert "std_dev" in stats["cache_hit_rate"]

    def test_reset_baselines(self, detector):
        """Test resetting all baselines."""
        # Establish baselines
        metrics = {
            "combined_hit_rate": 0.75,
            "tokens_per_second": 1000.0,
            "mean_coherence": 0.85,
            "elapsed_seconds": 1.0,
            "success_rate": 1.0,
        }
        for _ in range(5):
            detector.check_degradation(metrics)

        stats_before = detector.get_baseline_stats()
        assert stats_before["cache_hit_rate"]["num_samples"] == 5

        # Reset
        detector.reset_baselines()

        stats_after = detector.get_baseline_stats()
        assert stats_after["cache_hit_rate"]["num_samples"] == 0
        assert stats_after["cache_hit_rate"]["is_established"] is False
