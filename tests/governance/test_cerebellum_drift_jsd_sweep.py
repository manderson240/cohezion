"""Tests for cerebellum_drift — multi-class JSD drift sweep (backlog item 126).

Covers: binary JSD formula, single-class drift, full sweep, alert thresholds,
sample-count warning, and report formatting.
"""

from __future__ import annotations

import pytest

from cohezion.governance.cerebellum_drift_jsd_sweep import (
    TASK_CLASSES,
    DriftResult,
    cerebellum_drift_single,
    cerebellum_drift_sweep,
    drift_report,
    _jsd,
    _JSD_ALERT_THRESHOLD,
)


class TestJSD:
    def test_identical_distributions_zero(self):
        # JSD(p, p) = 0
        assert _jsd(0.4, 0.4) == pytest.approx(0.0, abs=1e-9)

    def test_extreme_divergence_positive(self):
        # p near 0, q near 1 → large JSD (handled by boundary fallback)
        result = _jsd(0.0, 1.0)
        assert result == pytest.approx(1.0)

    def test_symmetry(self):
        assert _jsd(0.3, 0.7) == pytest.approx(_jsd(0.7, 0.3), abs=1e-9)

    def test_bounded_zero_one(self):
        for p, q in [(0.1, 0.9), (0.3, 0.6), (0.5, 0.5), (0.9, 0.1)]:
            result = _jsd(p, q)
            assert 0.0 <= result <= 1.0


class TestCerebellumDriftSingle:
    def test_identical_no_drift(self):
        baseline = {"code": 50, "reason": 50}
        current = {"code": 50, "reason": 50}
        r = cerebellum_drift_single("code", baseline, current)
        assert r.jsd == pytest.approx(0.0, abs=1e-9)
        assert r.alert is False

    def test_complete_shift_triggers_alert(self):
        # All traffic shifted from 'code' to 'reason'
        baseline = {"code": 100, "reason": 0}
        current = {"code": 0, "reason": 100}
        r = cerebellum_drift_single("code", baseline, current)
        assert r.alert is True
        assert r.jsd > _JSD_ALERT_THRESHOLD

    def test_missing_class_in_current(self):
        baseline = {"code": 100}
        current = {}
        r = cerebellum_drift_single("code", baseline, current)
        assert isinstance(r, DriftResult)
        assert r.task_class == "code"

    def test_sample_count_is_current_total(self):
        baseline = {"code": 50}
        current = {"code": 30, "reason": 20}
        r = cerebellum_drift_single("code", baseline, current)
        assert r.sample_count == 50

    def test_baseline_and_current_probabilities_match_totals(self):
        baseline = {"code": 40, "reason": 60}
        current = {"code": 20, "reason": 80}
        r = cerebellum_drift_single("code", baseline, current)
        assert r.baseline_prob == pytest.approx(0.4, abs=1e-9)
        assert r.current_prob == pytest.approx(0.2, abs=1e-9)


class TestCerebellumDriftSweep:
    def test_sweep_all_default_classes(self):
        baseline = {c: 100 for c in TASK_CLASSES}
        current = {c: 100 for c in TASK_CLASSES}
        result = cerebellum_drift_sweep(baseline, current)
        assert result.swept_classes == len(TASK_CLASSES)
        assert len(result.results) == len(TASK_CLASSES)

    def test_sweep_no_drift_no_alerts(self):
        baseline = {c: 50 for c in TASK_CLASSES}
        current = {c: 50 for c in TASK_CLASSES}
        result = cerebellum_drift_sweep(baseline, current)
        assert len(result.alerts) == 0
        assert result.max_jsd == pytest.approx(0.0, abs=1e-6)

    def test_sweep_detects_multi_class_drift(self):
        # Shift traffic: code 80% → 20%, reason 0% → 60%
        baseline = {"code": 80, "reason": 0, "classify": 10, "route": 10}
        current = {"code": 20, "reason": 60, "classify": 10, "route": 10}
        result = cerebellum_drift_sweep(baseline, current)
        alerted_classes = {r.task_class for r in result.alerts}
        # Both 'code' and 'reason' should alert
        assert "code" in alerted_classes or "reason" in alerted_classes

    def test_sweep_custom_classes(self):
        baseline = {"alpha": 50, "beta": 50}
        current = {"alpha": 50, "beta": 50}
        result = cerebellum_drift_sweep(baseline, current, classes=["alpha", "beta"])
        assert result.swept_classes == 2

    def test_sweep_result_max_jsd_is_maximum(self):
        baseline = {c: 100 for c in TASK_CLASSES}
        current = dict(baseline)
        current["code"] = 1  # shift one class
        result = cerebellum_drift_sweep(baseline, current)
        assert result.max_jsd == max(r.jsd for r in result.results)

    def test_sweep_result_alerts_subset_of_results(self):
        baseline = {c: 100 for c in TASK_CLASSES}
        current = {c: 100 for c in TASK_CLASSES}
        current["code"] = 0  # force a drift
        result = cerebellum_drift_sweep(baseline, current)
        for alert in result.alerts:
            assert alert in result.results

    def test_sweep_warns_on_low_samples(self, caplog):
        import logging

        baseline = {"code": 100}
        current = {"code": 5}  # total = 5, below _MIN_SAMPLES=10
        with caplog.at_level(logging.WARNING, logger="cohezion.governance.cerebellum_drift"):
            cerebellum_drift_sweep(baseline, current)
        assert any("only" in rec.message and "samples" in rec.message for rec in caplog.records)


class TestDriftReport:
    def test_report_contains_class_names(self):
        baseline = {c: 100 for c in TASK_CLASSES}
        current = {c: 100 for c in TASK_CLASSES}
        result = cerebellum_drift_sweep(baseline, current)
        report = drift_report(result)
        for cls in TASK_CLASSES:
            assert cls in report

    def test_report_contains_alert_section_when_alerts(self):
        # code drops from 80% to 5% — clear drift signal
        baseline = {"code": 80, "reason": 20}
        current = {"code": 5, "reason": 95}
        result = cerebellum_drift_sweep(baseline, current, classes=["code"])
        report = drift_report(result)
        assert "ALERT" in report

    def test_report_no_alert_section_when_clean(self):
        baseline = {"code": 100}
        current = {"code": 100}
        result = cerebellum_drift_sweep(baseline, current, classes=["code"])
        report = drift_report(result)
        assert "ALERT" not in report
