"""Tests for the ConservationFilter Anomaly Gate (float-error vs structural divergence)."""

from __future__ import annotations

import numpy as np

from cohezion.physics.conservation_filter import ConservationFilter, Verdict


STATE = np.full(12, 0.5)  # coherence = 1.0 (passes band)


def _filter():
    return ConservationFilter(energy_tolerance=0.05, div_b_tolerance=1e-6)


def _baseline(f, e=100.0):
    """First call establishes E0 and should be STANDARD."""
    return f.evaluate(STATE, raw_energy=e, spinor_norm_sq=1.0, div_b_error=0.0)


# -- STANDARD -----------------------------------------------------------------


def test_baseline_is_standard():
    r = _baseline(_filter())
    assert r.verdict is Verdict.STANDARD and r.integrity_ok and not r.physical_violation


def test_small_energy_drift_within_tau_is_standard():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=103.0, spinor_norm_sq=1.0, div_b_error=0.0)  # +3% < 5%
    assert r.verdict is Verdict.STANDARD


# -- ANOMALY (the discovery path) ---------------------------------------------


def test_energy_spike_with_integrity_intact_is_anomaly():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=200.0, spinor_norm_sq=1.0, div_b_error=0.0)  # +100% >> tau
    assert r.verdict is Verdict.ANOMALY
    assert r.integrity_ok and r.physical_violation
    assert "energy_conservation" in r.failed


# -- REJECT (numerical artifacts, NOT discoveries) ----------------------------


def test_solenoidal_violation_is_reject():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=101.0, spinor_norm_sq=1.0, div_b_error=1.0)  # ∇·B drift
    assert r.verdict is Verdict.REJECT and not r.integrity_ok
    assert "solenoidal_div_b" in r.failed


def test_unitarity_violation_is_reject():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=100.0, spinor_norm_sq=2.0, div_b_error=0.0)  # |ψ|² ≠ 1
    assert r.verdict is Verdict.REJECT
    assert "unitarity" in r.failed


def test_non_finite_energy_is_reject():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=float("inf"), spinor_norm_sq=1.0)
    assert r.verdict is Verdict.REJECT and "finiteness" in r.failed


def test_nan_div_b_is_reject():
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=100.0, spinor_norm_sq=1.0, div_b_error=float("nan"))
    assert r.verdict is Verdict.REJECT


# -- THE DISCRIMINATOR: integrity failure dominates a physical spike ----------


def test_energy_spike_WITH_integrity_failure_is_reject_not_anomaly():
    """A float error that also spikes energy must be REJECT (artifact), never ANOMALY.

    This is the whole point: an energy spike is only a discovery if the numerical integrity
    invariants still hold. ∇·B drift + energy spike = boundary artifact, not a breakthrough.
    """
    f = _filter()
    _baseline(f, 100.0)
    r = f.evaluate(STATE, raw_energy=500.0, spinor_norm_sq=1.0, div_b_error=10.0)
    assert r.verdict is Verdict.REJECT  # NOT anomaly
    assert r.physical_violation is True  # the spike is recorded...
    assert r.integrity_ok is False  # ...but integrity failed, so it's an artifact
    assert "solenoidal_div_b" in r.failed


# -- reset --------------------------------------------------------------------


def test_reset_clears_energy_baseline():
    f = _filter()
    _baseline(f, 100.0)
    f.reset()
    # after reset, a new energy becomes the baseline -> standard, not an anomaly vs the old E0
    r = f.evaluate(STATE, raw_energy=1000.0, spinor_norm_sq=1.0, div_b_error=0.0)
    assert r.verdict is Verdict.STANDARD
