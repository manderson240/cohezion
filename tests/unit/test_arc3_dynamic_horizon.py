"""Unit tests for Dynamic Entropy-Bounded Horizon Controller (Pathway III)."""

from __future__ import annotations

import pytest

from cohezion.arc.tracks.arc3_dynamic_horizon import (
    DynamicEntropyHorizonController,
    HorizonDecision,
)


def test_dynamic_horizon_entropy_scaling():
    """Verify horizon expands when confidence is high and contracts when entropy spikes."""
    ctrl = DynamicEntropyHorizonController(
        h_min=4,
        h_max=30,
        entropy_critical=1.38,
        base_horizon=15,
    )

    # Low entropy (near 0) -> high confidence -> depth should approach h_max
    h_deep = ctrl.calculate_horizon(current_entropy=0.0, clearance_margin=2.0)
    assert h_deep >= 25
    assert h_deep <= 30

    # High entropy (at critical threshold 1.38) -> uncertainty -> depth contracts towards h_min
    h_short = ctrl.calculate_horizon(current_entropy=1.38, clearance_margin=0.0)
    assert h_short <= 15
    assert h_short >= 4

    # Ultra-high entropy -> strictly clipped to h_min
    h_clamped = ctrl.calculate_horizon(current_entropy=5.0)
    assert h_clamped == 4


def test_dynamic_horizon_budget_fraction_attenuation():
    """Verify horizon is attenuated when remaining step budget is depleted."""
    ctrl = DynamicEntropyHorizonController(h_min=4, h_max=30, base_horizon=15)

    # Full budget (1.0) vs near-exhaustion budget (0.1)
    h_full = ctrl.calculate_horizon(current_entropy=0.5, remaining_budget_fraction=1.0)
    h_depleted = ctrl.calculate_horizon(current_entropy=0.5, remaining_budget_fraction=0.1)

    assert h_depleted <= h_full
    assert h_depleted >= 4


def test_evaluate_step_normal_progression():
    """Verify mental rollout continues when entropy, drift, and margin are healthy."""
    ctrl = DynamicEntropyHorizonController()
    dec = ctrl.evaluate_step(
        step_idx=5,
        step_entropy=0.2,
        geodesic_drift=1.2,
        clearance_margin=1.5,
        current_max_horizon=20,
    )
    assert dec.should_terminate is False
    assert dec.termination_reason == "Safe within Lyapunov and entropy bounds"


def test_evaluate_step_entropy_spike_halt():
    """Verify mental simulation immediately halts when predictive transition entropy spikes."""
    ctrl = DynamicEntropyHorizonController(entropy_critical=1.38)
    dec = ctrl.evaluate_step(
        step_idx=7,
        step_entropy=1.45,
        geodesic_drift=0.8,
        clearance_margin=2.0,
    )
    assert dec.should_terminate is True
    assert "Predictive entropy spiked" in dec.termination_reason
    assert dec.computed_horizon == 7


def test_evaluate_step_clearance_breach_halt():
    """Verify mental simulation immediately halts if AutoHarness clearance margin breaches."""
    ctrl = DynamicEntropyHorizonController()
    dec = ctrl.evaluate_step(
        step_idx=4,
        step_entropy=0.1,
        geodesic_drift=0.5,
        clearance_margin=-0.2,
    )
    assert dec.should_terminate is True
    assert "clearance margin breached" in dec.termination_reason


def test_evaluate_step_geodesic_drift_halt():
    """Verify mental simulation halts if hyperbolic manifold distance drifts out of bounds."""
    ctrl = DynamicEntropyHorizonController(max_geodesic_drift=4.5)
    dec = ctrl.evaluate_step(
        step_idx=10,
        step_entropy=0.3,
        geodesic_drift=4.9,
        clearance_margin=1.0,
    )
    assert dec.should_terminate is True
    assert "Hyperbolic geodesic drift exceeded bounds" in dec.termination_reason


def test_evaluate_step_max_horizon_reach():
    """Verify simulation halts upon reaching computed max horizon."""
    ctrl = DynamicEntropyHorizonController()
    dec = ctrl.evaluate_step(
        step_idx=12,
        step_entropy=0.2,
        geodesic_drift=1.0,
        clearance_margin=1.0,
        current_max_horizon=12,
    )
    assert dec.should_terminate is True
    assert "maximum allocated simulation horizon" in dec.termination_reason
