"""Tests for divergence detection."""

from cohezion.universe.divergence import (
    HIHO_MAX_DRIFT,
    HIHO_TARGET,
    DivergenceDetector,
    DivergenceStatus,
)


class TestDivergenceStatus:
    def test_not_diverged(self):
        status = DivergenceStatus(diverged=False, reason="", coherence=0.5)
        assert not status.diverged
        assert status.reason == ""

    def test_diverged_with_reason(self):
        status = DivergenceStatus(diverged=True, reason="NaN detected", coherence=0.0)
        assert status.diverged
        assert "NaN" in status.reason


class TestDivergenceDetectorNaN:
    def test_nan_detection(self):
        detector = DivergenceDetector()
        result = detector.check(float("nan"))
        assert result.diverged
        assert "Non-finite" in result.reason

    def test_inf_detection(self):
        detector = DivergenceDetector()
        result = detector.check(float("inf"))
        assert result.diverged
        assert "Non-finite" in result.reason

    def test_negative_inf_detection(self):
        detector = DivergenceDetector()
        result = detector.check(float("-inf"))
        assert result.diverged
        assert "Non-finite" in result.reason


class TestDivergenceDetectorStatistical:
    def test_normal_values_no_divergence(self):
        detector = DivergenceDetector(max_sigma=3.0)
        # Pass coherence=0.5 to isolate statistical check from HIHO drift
        for v in [1.0, 1.1, 0.9, 1.05, 0.95]:
            result = detector.check(v, coherence=HIHO_TARGET)
        assert not result.diverged

    def test_outlier_detected(self):
        detector = DivergenceDetector(max_sigma=2.0)
        # Feed many stable values (pass coherence to bypass HIHO drift check)
        for _ in range(20):
            detector.check(1.0, coherence=HIHO_TARGET)
        # Then a huge outlier — should trigger statistical check before coherence
        result = detector.check(100.0, coherence=HIHO_TARGET)
        assert result.diverged
        assert "outlier" in result.reason.lower()

    def test_single_value_no_false_positive(self):
        detector = DivergenceDetector()
        result = detector.check(42.0, coherence=HIHO_TARGET)
        assert not result.diverged

    def test_two_values_no_false_positive(self):
        detector = DivergenceDetector()
        detector.check(1.0, coherence=HIHO_TARGET)
        result = detector.check(1.0, coherence=HIHO_TARGET)
        assert not result.diverged


class TestDivergenceDetectorCoherence:
    def test_coherence_at_target_ok(self):
        detector = DivergenceDetector()
        result = detector.check(1.0, coherence=HIHO_TARGET)
        assert not result.diverged

    def test_coherence_drift_detected(self):
        detector = DivergenceDetector()
        # Coherence far from 0.5 target
        drifted_coherence = HIHO_TARGET + HIHO_MAX_DRIFT + 0.01
        result = detector.check(1.0, coherence=drifted_coherence)
        assert result.diverged
        assert "coherence drift" in result.reason.lower()

    def test_coherence_at_boundary_ok(self):
        detector = DivergenceDetector()
        # Exactly at boundary should NOT diverge
        boundary_coherence = HIHO_TARGET + HIHO_MAX_DRIFT
        result = detector.check(1.0, coherence=boundary_coherence)
        assert not result.diverged

    def test_low_coherence_drift(self):
        detector = DivergenceDetector()
        low_coherence = HIHO_TARGET - HIHO_MAX_DRIFT - 0.05
        result = detector.check(1.0, coherence=low_coherence)
        assert result.diverged


class TestDivergenceDetectorReset:
    def test_reset_clears_state(self):
        detector = DivergenceDetector()
        for _ in range(10):
            detector.check(1.0)
        stats_before = detector.get_stats()
        assert stats_before["count"] == 10

        detector.reset()
        stats_after = detector.get_stats()
        assert stats_after["count"] == 0

    def test_get_stats(self):
        detector = DivergenceDetector(max_sigma=3.0, window_size=50)
        for v in [1.0, 2.0, 3.0]:
            detector.check(v)
        stats = detector.get_stats()
        assert stats["count"] == 3
        assert stats["window_size"] == 50
        assert stats["max_sigma"] == 3.0
        assert abs(stats["mean"] - 2.0) < 0.01
