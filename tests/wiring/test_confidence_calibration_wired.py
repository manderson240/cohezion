"""Discriminating tests: Platt calibration wired into inference surface."""

import math

from cohezion.inference import PlattCalibrator as pkg_cal
from cohezion.inference import calibrated_classify as pkg_cc
from cohezion.inference import set_default_calibrator as pkg_sdc
from cohezion.inference.confidence_calibration import PlattCalibrator as src_cal
from cohezion.inference.confidence_calibration import calibrated_classify as src_cc
from cohezion.inference.confidence_calibration import set_default_calibrator as src_sdc


def test_platt_calibrator_identity():
    """PlattCalibrator(A=1, B=0): σ(f) maps 0 → 0.5, preserves ordering.

    Note: raw confidence values in task_classifier are in [0.7, 0.95], so identity
    σ(f) maps them all to (0.5, 1.0). The meaningful property is ordering preservation.
    """
    cal = pkg_cal()
    assert abs(cal.calibrate(0.0) - 0.5) < 1e-6  # σ(0) = 0.5
    # Ordering preserved: higher raw score → higher calibrated score
    assert cal.calibrate(0.9) > cal.calibrate(0.7)
    assert cal.calibrate(0.7) > cal.calibrate(0.5)


def test_platt_calibrator_fit_discriminates():
    """After fit(), calibrate() returns values consistent with provided labels.

    Discriminating: if fit() were a no-op, the calibrated value for a score
    whose label=1 would not shift toward 1 after training on perfect data.
    """
    cal = src_cal()
    # Perfect separability: scores > 0.7 → correct (1), scores < 0.5 → wrong (0)
    raw = [0.8, 0.85, 0.9, 0.4, 0.3, 0.45]
    labels = [1, 1, 1, 0, 0, 0]
    cal.fit(raw, labels)

    assert cal.fitted
    # After fitting on separable data, high raw scores calibrate higher than low ones.
    # Discriminating: if fit() were a no-op (A=1, B=0), ordering would still hold but
    # the gap would be smaller. After Platt fit, A > 1 amplifies the difference.
    assert cal.calibrate(0.85) > cal.calibrate(0.35)
    # A > 1 after fitting on perfectly separable data (amplifies scores)
    assert cal.A > 1.0


def test_calibrated_classify_routing_unchanged():
    """Routing decision must be identical — only confidence changes."""
    from cohezion.inference.task_classifier import classify

    raw = classify("Reply with a single word only.")
    cal = src_cc("Reply with a single word only.")

    assert raw.node == cal.node
    assert raw.output_type == cal.output_type
    assert raw.quality_gate_chars == cal.quality_gate_chars
    assert "[platt" in cal.reason


def test_calibrated_classify_confidence_in_range():
    """calibrated_classify() confidence must be in [0, 1]."""
    result = pkg_cc("What is the HIHO stability principle?")
    assert 0.0 <= result.confidence <= 1.0


def test_calibrator_is_same():
    assert pkg_cal is src_cal
    assert pkg_cc is src_cc
    assert pkg_sdc is src_sdc


def test_calibrated_classify_math_sigma():
    """σ(A*f + B) must match expected value for known params.

    Discriminating: if calibrate() used the wrong formula (e.g. linear instead of logistic),
    this would fail.
    """
    cal = src_cal(A=2.0, B=-1.0)
    f = 0.8
    expected = 1.0 / (1.0 + math.exp(-(2.0 * f + (-1.0))))
    assert abs(cal.calibrate(f) - expected) < 1e-9
