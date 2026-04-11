"""Tests for physics invariant checker — deterministic proof obligation runner."""

import numpy as np
import pytest

from cohezion.physics.invariant_checker import (
    InvariantChecker,
    InvariantReport,
    ObligationResult,
    ObligationStatus,
)


@pytest.fixture
def checker():
    return InvariantChecker()


class TestEnergyObligation:
    @pytest.mark.unit
    def test_first_call_records_initial(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, energy=1.0)
        r = next(r for r in report.results if r.name == "energy_conservation")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_conserved_energy_passes(self, checker):
        state = np.full(12, 0.5)
        checker.check_all(state, energy=1.0)
        report = checker.check_all(state, energy=1.01)
        r = next(r for r in report.results if r.name == "energy_conservation")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_drifted_energy_fails(self, checker):
        state = np.full(12, 0.5)
        checker.check_all(state, energy=1.0)
        report = checker.check_all(state, energy=2.0)  # 100% drift
        r = next(r for r in report.results if r.name == "energy_conservation")
        assert r.status == ObligationStatus.FAIL

    @pytest.mark.unit
    def test_reset_clears_initial(self, checker):
        state = np.full(12, 0.5)
        checker.check_all(state, energy=1.0)
        checker.reset()
        report = checker.check_all(state, energy=5.0)
        r = next(r for r in report.results if r.name == "energy_conservation")
        assert r.status == ObligationStatus.PASS  # First call after reset


class TestUnitarityObligation:
    @pytest.mark.unit
    def test_perfect_norm_passes(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, spinor_norm_sq=1.0)
        r = next(r for r in report.results if r.name == "unitarity")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_violated_norm_fails(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, spinor_norm_sq=0.5)
        r = next(r for r in report.results if r.name == "unitarity")
        assert r.status == ObligationStatus.FAIL


class TestCoherenceObligation:
    @pytest.mark.unit
    def test_hiho_in_band(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state)
        r = next(r for r in report.results if r.name == "coherence_band")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_extreme_state_outside_band(self, checker):
        state = np.zeros(12)  # coherence = 0.0
        report = checker.check_all(state)
        r = next(r for r in report.results if r.name == "coherence_band")
        assert r.status == ObligationStatus.FAIL


class TestMetricObligation:
    @pytest.mark.unit
    def test_positive_det_passes(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, metric_det=1.0)
        r = next(r for r in report.results if r.name == "metric_positive_definite")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_zero_det_fails(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, metric_det=0.0)
        r = next(r for r in report.results if r.name == "metric_positive_definite")
        assert r.status == ObligationStatus.FAIL


class TestGaugeObligation:
    @pytest.mark.unit
    def test_nonneg_action_passes(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, yang_mills_action=0.0)
        r = next(r for r in report.results if r.name == "gauge_action_nonneg")
        assert r.status == ObligationStatus.PASS

    @pytest.mark.unit
    def test_negative_action_fails(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, yang_mills_action=-1.0)
        r = next(r for r in report.results if r.name == "gauge_action_nonneg")
        assert r.status == ObligationStatus.FAIL


class TestInvariantReport:
    @pytest.mark.unit
    def test_all_pass_report(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state, energy=1.0, spinor_norm_sq=1.0, metric_det=1.0)
        assert report.passed is True
        assert report.failed_count == 0

    @pytest.mark.unit
    def test_report_summary_contains_status(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state)
        assert "PASS" in report.summary or "FAIL" in report.summary

    @pytest.mark.unit
    def test_optional_checks_skipped_when_none(self, checker):
        state = np.full(12, 0.5)
        report = checker.check_all(state)
        names = [r.name for r in report.results]
        assert "coherence_band" in names
        assert "energy_conservation" not in names  # Not provided
        assert "unitarity" not in names  # Not provided
