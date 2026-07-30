"""Discriminating tests for the PlattCalibrator FEEDER (unlocks the unfed calibrator dormancy).

Motivated by CMS BPH-26-005 flavour-tag calibration: a classifier's raw score is not a calibrated
probability until fit against a control channel. Each test fails for the dormant (unfit/identity) state.
"""

from cohezion.inference.confidence_calibration import (
    PlattCalibrator,
    calibrated_classify,
    fit_default_calibrator,
    set_default_calibrator,
)


def teardown_function():
    # restore identity so tests don't leak a fitted global calibrator
    set_default_calibrator(PlattCalibrator())


def test_calibrator_learns_high_confidence_is_wrong():
    # control signal: raw 0.9 confidence but ALWAYS wrong → calibrated prob must collapse low.
    cal = PlattCalibrator().fit([0.9] * 12, [0] * 12)
    # discriminating: the UNFIT default gives sigmoid(0.9)=0.711; a real fit drives it far lower.
    assert cal.calibrate(0.9) < 0.3, cal.calibrate(0.9)


def test_calibrator_learns_high_confidence_is_right():
    cal = PlattCalibrator().fit([0.9] * 12, [1] * 12)
    assert cal.calibrate(0.9) > 0.7, cal.calibrate(0.9)


def test_feeder_installs_a_fitted_non_identity_calibrator():
    # THE UNLOCK: fit_default_calibrator() runs classify on the control set and installs a fitted
    # calibrator — the default is no longer identity (A=1.0, B=0.0).
    cal = fit_default_calibrator()
    assert cal.fitted is True
    assert (cal.A, cal.B) != (1.0, 0.0), (cal.A, cal.B)


def test_calibrated_classify_consumes_the_fitted_calibrator():
    # CONSUMPTION: after feeding, calibrated_classify's confidence equals the fitted calibrator's
    # output for the raw score, and the reason records the fitted A/B (proving it's not identity).
    fit_default_calibrator()
    d = calibrated_classify("What is 2+2?")
    assert "platt A=" in d.reason
    assert "A=1.000 B=0.000" not in d.reason  # a no-op/unfed calibrator would show identity params
