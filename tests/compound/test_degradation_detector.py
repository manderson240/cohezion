"""Tests for degradation detection module - Phase 5A.6."""

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


class TestJepaCoherenceSignal:
    """H2: JepaGate.last_coherence written into degradation_metrics must be tracked, not dropped."""

    def test_jepa_coherence_low_value_emits_warning_alert(self, detector):
        """Discriminating: a low pre-execution JEPA coherence must produce a jepa_coherence WARNING.

        A regression that drops the key (the original bug — DegradationDetector read a fixed key
        set omitting jepa_coherence) produces NO jepa_coherence alert, failing this assertion.
        """
        # Establish a healthy jepa_coherence baseline (need >= min_samples to be established).
        for _ in range(5):
            detector.check_degradation({"jepa_coherence": 0.90})

        alerts = detector.check_degradation({"jepa_coherence": 0.20})  # below 0.60 threshold
        jepa_alerts = [a for a in alerts if a.metric == "jepa_coherence"]
        assert len(jepa_alerts) > 0, "low jepa_coherence must emit an alert (not be silently dropped)"
        assert jepa_alerts[0].severity == AlertSeverity.WARNING
        assert jepa_alerts[0].current_value == pytest.approx(0.20)

    def test_jepa_coherence_healthy_value_no_alert(self, detector):
        """A healthy predicted coherence must NOT alert (proves the check is selective)."""
        for _ in range(5):
            detector.check_degradation({"jepa_coherence": 0.90})
        alerts = detector.check_degradation({"jepa_coherence": 0.85})
        assert [a for a in alerts if a.metric == "jepa_coherence"] == []


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

    def test_alert_resumes_after_cooldown(self, detector, monkeypatch):
        """Test that alerts resume after cooldown period."""
        detector._alert_cooldown_seconds = 0.1  # 100ms for testing

        # Use a controllable virtual clock instead of time.sleep
        clock = {"t": 1000.0}
        monkeypatch.setattr(
            "cohezion.compound.degradation_detector.time.time",
            lambda: clock["t"],
        )

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

        # Advance virtual clock past cooldown window
        clock["t"] += 0.15

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


class TestLogSynthesisScore:
    """Tests for Task #99 — Sazabi log synthesis score (geometric-mean health proxy)."""

    def test_returns_none_when_no_baselines_established(self):
        """Discriminating: fresh detector returns None, not 0 or 1.

        A stub that always returns 0 or always returns None would satisfy one case
        but not both. The discriminating pair is this test + the next.
        """
        d = DegradationDetector()
        assert d.get_log_synthesis_score() is None

    def test_geometric_mean_not_arithmetic_mean(self):
        """Discriminating: log-space computation gives geometric mean, not arithmetic.

        geometric([0.8, 0.2]) = sqrt(0.16) ≈ 0.4000
        arithmetic([0.8, 0.2]) = 0.5

        A wrong implementation using arithmetic mean returns 0.5 and fails here.
        """
        import math

        d = DegradationDetector()
        # Seed only two 0-1 baselines so the expected value is analytically known
        for _ in range(5):
            d._baselines["cache_hit_rate"].add_sample(0.8)
        for _ in range(5):
            d._baselines["coherence"].add_sample(0.2)
        # All other baselines remain unestablished → excluded from computation

        score = d.get_log_synthesis_score()
        assert score is not None

        expected_geom = math.exp((math.log(0.8) + math.log(0.2)) / 2)  # ≈ 0.4
        wrong_arith = (0.8 + 0.2) / 2  # = 0.5 — what an arithmetic-mean impl returns
        assert score == pytest.approx(expected_geom, rel=1e-3)
        assert score != pytest.approx(wrong_arith, rel=1e-2)


class TestEmbeddingPSI:
    """Tests for Task #112 — PSI embedding drift detection."""

    def test_identical_distributions_yield_near_zero_psi(self):
        """Discriminating: stable embedding norms produce PSI < 0.1 (no spurious alert).

        A broken implementation that always returns a large PSI would fail here.
        A stub returning None fails because we have ≥ 20 samples.
        """
        d = DegradationDetector()
        # 20 identical unit vectors — both histogram halves are in the same bin
        for _ in range(20):
            d.update_embedding_distribution([1.0, 0.0, 0.0])  # norm = 1.0

        psi = d.get_embedding_psi()
        assert psi is not None
        assert psi < 0.1  # identical distributions → no drift

    def test_distribution_shift_triggers_check_degradation_alert(self, detector):
        """Discriminating: shifted embedding norms must produce a CRITICAL embedding_drift
        alert through the production check_degradation() path.

        Tests the end-to-end wiring (update_embedding_distribution →
        get_embedding_psi → check_degradation alert list), not just the PSI math.
        A stub that short-circuits either leg would fail because we assert on
        the alert object returned by check_degradation().
        """
        # First 10 norms: tight cluster at 0.3 (baseline distribution)
        for _ in range(10):
            detector.update_embedding_distribution([0.3, 0.0, 0.0])  # norm ≈ 0.3
        # Last 10 norms: tight cluster at 3.2 (completely non-overlapping bins)
        for _ in range(10):
            detector.update_embedding_distribution([3.2, 0.0, 0.0])  # norm ≈ 3.2

        psi = detector.get_embedding_psi()
        assert psi is not None and psi > 0.2  # non-overlapping → CRITICAL territory

        # Production path: check_degradation() must surface the alert
        alerts = detector.check_degradation({})
        drift_alerts = [a for a in alerts if a.metric == "embedding_drift"]
        assert len(drift_alerts) == 1
        assert drift_alerts[0].severity == AlertSeverity.CRITICAL  # psi > 0.2
        assert drift_alerts[0].current_value == pytest.approx(psi)
