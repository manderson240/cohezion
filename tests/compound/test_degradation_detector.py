"""Tests for degradation detection module - Phase 5A.6."""

import pytest

from cohezion.compound.degradation_detector import (
    AlertSeverity,
    DegradationAlert,
    DegradationDetector,
    MetricBaseline,
    SkillDriftDetector,
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
        assert len(jepa_alerts) > 0, (
            "low jepa_coherence must emit an alert (not be silently dropped)"
        )
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


class TestSkillDriftDetector:
    """SD1–SD8: per-skill quality drift detection with two-level severity.

    SkillDriftDetector is a standalone class inside DegradationDetector that tracks
    per-skill rolling quality baselines. Unlike the aggregate MetricBaseline which watches
    system-wide metrics, this gives each skill its own drift signal — enabling the compound
    loop to distinguish "system is degrading" from "this specific skill is regressing."
    """

    def test_sd1_structural_interface(self):
        """SD1: class has expected thresholds and internal structure."""
        sdd = SkillDriftDetector()
        assert pytest.approx(0.03) == sdd.WARN_THRESHOLD
        assert pytest.approx(0.05) == sdd.BLOCK_THRESHOLD
        assert isinstance(sdd._baselines, dict)

    def test_sd1_custom_window_and_min_samples(self):
        """SD1b: constructor params are respected, not hardcoded."""
        sdd = SkillDriftDetector(window_size=5, min_samples=2)
        # Fill 6 samples — window should cap at 5
        for _ in range(6):
            sdd.record("s", 0.9)
        assert len(sdd._baselines["s"]) == 5

    def test_sd2_warn_at_3_5_pct_drop(self):
        """SD2: 3.5% drop below baseline triggers WARNING, not None.

        Discriminating: a broken impl returning None always would fail here.
        An impl that only returns CRITICAL would also fail.
        """
        sdd = SkillDriftDetector(min_samples=5)
        # Baseline: 5 samples at 0.85 → mean = 0.85
        for _ in range(5):
            sdd.record("gen", 0.85)
        # 3.5% drop: 0.85 * (1 - 0.035) = 0.82025
        alert = sdd.check("gen", 0.82)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert "WARN" in alert.message

    def test_sd3_block_at_7_pct_drop(self):
        """SD3 (discriminating): 7.1% drop triggers CRITICAL, not WARNING.

        The most plausible wrong impl returns WARNING for all alerts regardless of
        severity. This test would FAIL that implementation.
        """
        sdd = SkillDriftDetector(min_samples=5)
        for _ in range(5):
            sdd.record("gen", 0.85)
        # 7.1% drop: 0.85 * (1 - 0.071) ≈ 0.790
        alert = sdd.check("gen", 0.79)
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert "BLOCK" in alert.message

    def test_sd3_severity_discrimination(self):
        """SD3b: warning-severity score must NOT trigger CRITICAL.

        A simple threshold impl that fires CRITICAL at any alert would fail this.
        """
        sdd = SkillDriftDetector(min_samples=5)
        for _ in range(5):
            sdd.record("s", 0.80)
        # 3.75% drop = WARN territory, not CRITICAL
        alert = sdd.check("s", 0.77)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.severity != AlertSeverity.CRITICAL

    def test_sd4_mild_variation_returns_none(self):
        """SD4: improvement or <3% variation returns None — no false positives."""
        sdd = SkillDriftDetector(min_samples=5)
        for _ in range(5):
            sdd.record("s", 0.80)
        # 1% drop — well below 3% WARN threshold
        assert sdd.check("s", 0.792) is None
        # Improvement: no alert ever for quality going up
        assert sdd.check("s", 0.90) is None

    def test_sd5_fail_open_with_fewer_than_min_samples(self):
        """SD5: with < min_samples records, check() returns None (fail-open).

        Fail-open is critical so new skills don't trigger spurious alerts on their
        first few executions before a real baseline is established.
        """
        sdd = SkillDriftDetector(min_samples=5)
        for _ in range(4):  # one short of min_samples
            sdd.record("new_skill", 0.90)
        # Even a large drop should produce None — baseline not yet reliable
        assert sdd.check("new_skill", 0.50) is None

    def test_sd5_fail_open_unknown_skill(self):
        """SD5b: unknown skill (no records at all) returns None."""
        sdd = SkillDriftDetector()
        assert sdd.check("never_seen", 0.01) is None

    def test_sd6_improvements_never_blocked(self):
        """SD6 (discriminating): quality ABOVE baseline never triggers an alert.

        This tests that the detector is directional — it catches regressions, not
        improvements. The wrong impl (absolute deviation instead of signed drop)
        would fire an alert for 0.95 vs 0.80 baseline.
        """
        sdd = SkillDriftDetector(min_samples=5)
        for _ in range(5):
            sdd.record("s", 0.80)
        # Strong improvement — 18.75% ABOVE baseline
        alert = sdd.check("s", 0.95)
        assert alert is None, "Improvements must never be blocked by drift detector"

    def test_sd7_degradation_detector_has_skill_drift_attribute(self):
        """SD7: DegradationDetector exposes _skill_drift as a SkillDriftDetector instance.

        This is the declaration half of the wiring invariant. The consumption half
        is tested in SD8 (check_skill_drift updates history).
        """
        dd = DegradationDetector()
        assert hasattr(dd, "_skill_drift")
        assert isinstance(dd._skill_drift, SkillDriftDetector)

    def test_sd8_check_skill_drift_records_and_gates(self):
        """SD8 (discriminating): check_skill_drift() records quality AND gates on BLOCK.

        This is the consumption invariant: calling check_skill_drift() must feed the
        rolling baseline (record) AND surface CRITICAL alerts through DegradationDetector's
        alert history. A stub that calls check() but not record() would make the baseline
        static; a stub that calls record() but doesn't append to _alert_history would
        produce a silent DORMANT capability.

        The wrong impl (calling record() before check()) would self-validate the current
        sample — this test catches that by verifying the final history reflects the drop.
        """
        dd = DegradationDetector()
        # Build a baseline: 5 calls at quality=0.85
        for _ in range(5):
            dd.check_skill_drift("my_skill", 0.85)
        # Now a CRITICAL drop (7%+ below 0.85)
        alert = dd.check_skill_drift("my_skill", 0.78)
        # Alert must be returned AND in history
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        history_metrics = [a.metric for a in dd._alert_history]
        assert any("my_skill" in m for m in history_metrics)
        # Baseline must have grown (record was called)
        assert len(dd._skill_drift._baselines.get("my_skill", [])) == 6


# ──────────────────────────────────────────────────────────────────────────────
# LT1: EMA threshold adaptation (MTF 2-competitiveness backing)
# ──────────────────────────────────────────────────────────────────────────────


class TestEMAThresholds:
    """LT1: _ema_thresholds adapts toward observed values; fast-path α=0.4 on >2σ burst.

    Invariants:
      T1: EMA seeded from constructor threshold (structural)
      T2: slow α (0.1) applied for stable observations
      T3: fast α (0.4) applied when observation deviates >2σ — DISCRIMINATING
      T4: get_learned_threshold() applies drop_band below EMA
      T5: use_ema_thresholds=False leaves EMA dormant (not updated)
      T6: EMA bounded to [0.0, 1.0] even for extreme observations
      T7: unknown metric falls back gracefully in get_learned_threshold()
      T8: EMA converges toward observed values over multiple stable calls
    """

    def test_t1_ema_seeded_from_constructor(self) -> None:
        """EMA initialized to constructor threshold value."""
        dd = DegradationDetector(cache_hit_rate_threshold=0.65)
        assert dd._ema_thresholds["cache_hit_rate"] == pytest.approx(0.65)
        assert dd._ema_thresholds["coherence"] == pytest.approx(0.60)
        assert dd._ema_thresholds["token_efficiency_drop"] == pytest.approx(0.10)

    def test_t2_stable_observations_use_slow_alpha(self) -> None:
        """Stable sequence → EMA moves by slow α≈0.1 fraction per step."""
        dd = DegradationDetector(
            cache_hit_rate_threshold=0.50,
            use_ema_thresholds=True,
        )
        # The metrics key for cache hit rate is "combined_hit_rate"
        for _ in range(8):
            dd.check_degradation({"combined_hit_rate": 0.70})
        ema_after = dd._ema_thresholds["cache_hit_rate"]
        # EMA should be between original (0.50) and observation (0.70), moved by slow α
        # After ~8 steps with α=0.1: ema ≈ 0.50*(0.9^8) + 0.70*(1-0.9^8) ≈ 0.61
        assert 0.50 < ema_after < 0.70, f"Expected EMA between 0.50 and 0.70, got {ema_after:.4f}"

    def test_t3_burst_observation_uses_fast_alpha(self) -> None:
        """Burst (>2σ deviation) → fast α (0.4) applied, NOT slow α (0.1).

        Wrong impl (always α=0.1): after seeding near 0.70 and then a burst to 0.10,
        the EMA moves much less than with α=0.4, so the test fails if fast-path is absent.
        """
        dd = DegradationDetector(
            cache_hit_rate_threshold=0.70,
            use_ema_thresholds=True,
        )
        # Seed history: 8 stable observations near 0.70 (small σ)
        for _ in range(8):
            dd.check_degradation({"combined_hit_rate": 0.70})
        ema_before_burst = dd._ema_thresholds["cache_hit_rate"]

        # Burst: a sudden observation at 0.10 (far below the stable mean, >2σ)
        dd.check_degradation({"combined_hit_rate": 0.10})
        ema_after_burst = dd._ema_thresholds["cache_hit_rate"]

        # With slow α=0.1: drop ≈ 0.9*(ema_before) + 0.1*0.10
        slow_prediction = 0.9 * ema_before_burst + 0.1 * 0.10
        # With fast α=0.4: drop ≈ 0.6*(ema_before) + 0.4*0.10
        fast_prediction = 0.6 * ema_before_burst + 0.4 * 0.10

        # The actual EMA must be closer to fast_prediction than slow_prediction
        diff_from_fast = abs(ema_after_burst - fast_prediction)
        diff_from_slow = abs(ema_after_burst - slow_prediction)
        assert diff_from_fast < diff_from_slow, (
            f"Burst must use fast α=0.4 (diff={diff_from_fast:.4f}) not slow α=0.1 "
            f"(diff={diff_from_slow:.4f}). EMA after burst={ema_after_burst:.4f}"
        )

    def test_t4_get_learned_threshold_applies_drop_band(self) -> None:
        """get_learned_threshold() returns ema*(1-drop_band), always < ema."""
        dd = DegradationDetector(cache_hit_rate_threshold=0.60)
        ema = dd._ema_thresholds["cache_hit_rate"]
        learned = dd.get_learned_threshold("cache_hit_rate", drop_band=0.05)
        assert learned == pytest.approx(ema * 0.95)
        # Must be strictly below the EMA
        assert learned < ema

    def test_t5_use_ema_thresholds_false_leaves_ema_dormant(self) -> None:
        """When use_ema_thresholds=False (default), EMA is NOT updated by check_degradation."""
        dd = DegradationDetector(cache_hit_rate_threshold=0.50)  # use_ema_thresholds=False
        initial_ema = dd._ema_thresholds["cache_hit_rate"]
        # Drive many observations far from the initial threshold
        for _ in range(20):
            dd.check_degradation({"combined_hit_rate": 0.90})
        # EMA must remain at seeded value (not updated when flag is False)
        assert dd._ema_thresholds["cache_hit_rate"] == pytest.approx(initial_ema)

    def test_t6_ema_bounded_to_zero_one(self) -> None:
        """EMA updates clamp to [0.0, 1.0] even for extreme observations."""
        dd = DegradationDetector(
            cache_hit_rate_threshold=0.50,
            use_ema_thresholds=True,
        )
        for _ in range(15):
            dd.check_degradation({"combined_hit_rate": 1.5})  # above 1.0
        assert dd._ema_thresholds["cache_hit_rate"] <= 1.0

        dd2 = DegradationDetector(
            cache_hit_rate_threshold=0.50,
            use_ema_thresholds=True,
        )
        for _ in range(15):
            dd2.check_degradation({"combined_hit_rate": -0.5})  # below 0.0
        assert dd2._ema_thresholds["cache_hit_rate"] >= 0.0

    def test_t7_unknown_metric_returns_gracefully(self) -> None:
        """get_learned_threshold() on unknown metric returns a float (fallback, no crash)."""
        dd = DegradationDetector()
        result = dd.get_learned_threshold("nonexistent_metric")
        assert isinstance(result, float)

    def test_t8_ema_converges_toward_observations(self) -> None:
        """After many stable calls at 0.80, EMA moves closer to 0.80 than initial 0.50."""
        dd = DegradationDetector(
            cache_hit_rate_threshold=0.50,
            use_ema_thresholds=True,
        )
        for _ in range(40):
            dd.check_degradation({"combined_hit_rate": 0.80})
        ema = dd._ema_thresholds["cache_hit_rate"]
        # EMA must have moved: distance to 0.80 < initial distance to 0.80 (=0.30)
        assert abs(ema - 0.80) < abs(0.50 - 0.80), (
            f"EMA={ema:.4f} should be closer to 0.80 than initial 0.50"
        )


# ──────────────────────────────────────────────────────────────────────────────
# CB7: DegradationDetector serialization (to_dict / from_dict)
# SkillDriftDetector serialization (SD-PERSIST series)
# ──────────────────────────────────────────────────────────────────────────────


class TestCB7Serialization:
    """CB7: DegradationDetector.to_dict()/from_dict() round-trips baselines + call_count.

    Also covers SkillDriftDetector persistence (SD-PERSIST1-3) as a nested sub-state.

    Invariants:
      CB7-1 (structural): to_dict() returns required JSON-safe keys
      CB7-2 (discriminating): from_dict() restores non-default call_count (not always 0)
      CB7-3: SkillDriftDetector._baselines survive round-trip
      CB7-4 (fail-open): missing keys in from_dict() fall back to empty/zero state
    """

    def test_cb7_1_to_dict_returns_required_keys(self) -> None:
        """CB7-1 (structural): to_dict() must include 'call_count', 'baselines', 'skill_drift'."""
        dd = DegradationDetector()
        # Add some baseline samples so we have non-empty state
        for _ in range(3):
            dd.check_degradation({"combined_hit_rate": 0.8, "quality_score": 0.9})
        state = dd.to_dict()
        assert isinstance(state, dict)
        assert "call_count" in state, "Missing call_count"
        assert "baselines" in state, "Missing baselines"
        assert "skill_drift" in state, "Missing skill_drift (SkillDriftDetector state)"
        # JSON-safe: no non-serializable objects
        import json

        json.dumps(state)  # must not raise

    def test_cb7_2_from_dict_restores_call_count(self) -> None:
        """CB7-2 (discriminating): from_dict() restores call_count; wrong impl leaves it at 0."""
        dd = DegradationDetector()
        for _ in range(7):
            dd.check_degradation({"combined_hit_rate": 0.8})
        original_count = dd._call_count
        assert original_count == 7

        state = dd.to_dict()
        dd2 = DegradationDetector.from_dict(state)
        # Discriminating: a wrong impl that ignores 'call_count' would give 0 here
        assert dd2._call_count == 7, f"call_count should be 7 but got {dd2._call_count}"

    def test_cb7_3_skill_drift_baselines_survive_roundtrip(self) -> None:
        """CB7-3: SkillDriftDetector per-skill baselines round-trip through to/from_dict."""
        dd = DegradationDetector()
        # Build skill baselines
        for _ in range(5):
            dd.check_skill_drift("alpha_skill", 0.85)
        for _ in range(3):
            dd.check_skill_drift("beta_skill", 0.70)

        state = dd.to_dict()
        dd2 = DegradationDetector.from_dict(state)

        # Per-skill windows must survive
        alpha = dd2._skill_drift._baselines.get("alpha_skill", [])
        beta = dd2._skill_drift._baselines.get("beta_skill", [])
        assert len(alpha) == 5, f"alpha_skill should have 5 samples, got {len(alpha)}"
        assert len(beta) == 3, f"beta_skill should have 3 samples, got {len(beta)}"
        assert abs(alpha[0] - 0.85) < 1e-9

    def test_cb7_4_fail_open_on_missing_keys(self) -> None:
        """CB7-4: from_dict() with partial/empty dict falls back gracefully, no crash."""
        # Empty dict → default state
        dd = DegradationDetector.from_dict({})
        assert dd._call_count == 0
        assert isinstance(dd._skill_drift._baselines, dict)

        # Missing skill_drift → fresh SkillDriftDetector
        dd2 = DegradationDetector.from_dict({"call_count": 5, "baselines": {}})
        assert dd2._call_count == 5
        assert len(dd2._skill_drift._baselines) == 0

    def test_cb7_kwargs_forwarded_to_init(self) -> None:
        """CB7: from_dict() forwards kwargs to __init__ for threshold overrides."""
        state = {"call_count": 3, "baselines": {}, "skill_drift": {}}
        dd = DegradationDetector.from_dict(state, cache_hit_rate_threshold=0.99)
        assert dd._call_count == 3
        # The threshold kwarg must reach __init__ (attribute is public, no underscore)
        assert dd.cache_hit_rate_threshold == pytest.approx(0.99)


class TestSkillDriftPersistence:
    """SD-PERSIST: SkillDriftDetector.to_dict()/from_dict() — standalone persistence.

    Invariants:
      SD-P1 (structural): to_dict() returns JSON-safe {'window_size', 'min_samples', 'baselines'}
      SD-P2 (discriminating): from_dict() restores non-empty baselines
      SD-P3 (fail-open): missing keys fall back to empty state
    """

    def test_sdp1_to_dict_required_keys(self) -> None:
        """SD-P1 (structural): to_dict() returns the three required keys."""
        sdd = SkillDriftDetector(window_size=15, min_samples=3)
        sdd.record("skill_x", 0.9)
        state = sdd.to_dict()
        assert set(state.keys()) >= {"window_size", "min_samples", "baselines"}
        assert state["window_size"] == 15
        assert state["min_samples"] == 3
        assert isinstance(state["baselines"], dict)

    def test_sdp2_from_dict_restores_baselines(self) -> None:
        """SD-P2 (discriminating): from_dict() restores per-skill history; wrong impl gives empty."""
        sdd = SkillDriftDetector()
        for _ in range(6):
            sdd.record("my_skill", 0.80)
        state = sdd.to_dict()
        sdd2 = SkillDriftDetector.from_dict(state)
        # Discriminating: wrong impl that ignores 'baselines' would give len == 0
        restored = sdd2._baselines.get("my_skill", [])
        assert len(restored) == 6, f"Expected 6 samples, got {len(restored)}"
        assert all(abs(v - 0.80) < 1e-9 for v in restored)

    def test_sdp3_fail_open_missing_keys(self) -> None:
        """SD-P3 (fail-open): from_dict({}) returns a usable SkillDriftDetector."""
        sdd = SkillDriftDetector.from_dict({})
        assert isinstance(sdd._baselines, dict)
        assert len(sdd._baselines) == 0
        # Default window/min_samples preserved
        assert sdd._window_size == 20
        assert sdd._min_samples == 5
