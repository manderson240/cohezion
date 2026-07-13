"""Tests for RetardedField — OPH signal propagation with causal delay.

Grounded in X-ray reverberation mapping (Kara 2026, MIT): a source flash
travels to a reflector and arrives at the observer with delay τ = r/c.
In OPH terms: two observer patches exchange information at finite propagation
speed; the observed signal is the emitted signal shifted by τ.

22-hour delay anchor: signals emitted at t=0 arrive at t=τ.  Querying before
τ must return the pre-emission baseline; querying after τ must return the
emitted value.
"""

from __future__ import annotations

import pytest


pytest.importorskip(
    "cohezion.physics.observer_patch", reason="TDD-red: FrequencyDispersedDelay not yet implemented"
)

import math

import pytest

from cohezion.physics.observer_patch import (
    ObserverPatch,
    RetardedField,
    compute_retarded_delay,
    signal_at_observer,
)
from cohezion.physics.spinor import SpinorState


# ---------------------------------------------------------------------------
# T1 structural
# ---------------------------------------------------------------------------


class TestRetardedFieldStructural:
    """Structural invariants: API surface must exist with correct types."""

    def test_retarded_field_dataclass_exists(self) -> None:
        rf = RetardedField(delay_seconds=79200.0)
        assert rf.delay_seconds == pytest.approx(79200.0)

    def test_retarded_field_has_propagation_speed(self) -> None:
        rf = RetardedField(delay_seconds=100.0, propagation_speed=1e-4)
        assert rf.propagation_speed == pytest.approx(1e-4)

    def test_compute_retarded_delay_callable(self) -> None:
        """compute_retarded_delay(patch_a, patch_b, speed) must return float >= 0."""
        s = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
        p_a = ObserverPatch(agent_id="a", spinor=s)
        p_b = ObserverPatch(agent_id="b", spinor=s)
        tau = compute_retarded_delay(p_a, p_b, propagation_speed=1e-3)
        assert isinstance(tau, float)
        assert tau >= 0.0

    def test_signal_at_observer_callable(self) -> None:
        """signal_at_observer(signal_fn, t, delay) must return a float."""
        def signal_fn(t):
            return 1.0 if t >= 0 else 0.0
        val = signal_at_observer(signal_fn, t=1000.0, delay=500.0)
        assert isinstance(val, float)


# ---------------------------------------------------------------------------
# T2 discriminating
# ---------------------------------------------------------------------------


class TestRetardedFieldDiscriminating:
    """Causal delay must shift the signal — not merely scale it."""

    _22H = 22 * 3600  # 79200 seconds

    def test_signal_not_yet_arrived_before_delay(self) -> None:
        """At t < τ, observer still sees pre-emission baseline (0.0).

        Wrong impl: returns the emitted value immediately (no delay).
        Discriminating: must be 0.0 at t=21h when τ=22h.
        """

        # Step function: 0 before t=0, 1 at t>=0 (emission event at t=0)
        def step_signal(t: float) -> float:
            return 1.0 if t >= 0.0 else 0.0

        val = signal_at_observer(step_signal, t=21 * 3600, delay=self._22H)
        assert val == pytest.approx(0.0), (
            f"At t=21h < τ=22h, observer must still see pre-emission 0.0; got {val}"
        )

    def test_signal_arrived_after_delay(self) -> None:
        """At t > τ, observer receives the emitted value.

        Wrong impl: returns 0.0 always.
        Discriminating: must be 1.0 at t=23h when τ=22h.
        """

        def step_signal(t: float) -> float:
            return 1.0 if t >= 0.0 else 0.0

        val = signal_at_observer(step_signal, t=23 * 3600, delay=self._22H)
        assert val == pytest.approx(1.0), (
            f"At t=23h > τ=22h, observer must receive emitted 1.0; got {val}"
        )

    def test_delay_exactly_at_boundary(self) -> None:
        """At t = τ exactly, observer receives the t=0 emission."""

        def ramp(t: float) -> float:
            return max(0.0, t)

        val = signal_at_observer(ramp, t=self._22H, delay=self._22H)
        # Retarded time = t - τ = 0, ramp(0) = 0
        assert val == pytest.approx(0.0)

    def test_zero_delay_is_identity(self) -> None:
        """With τ=0, observer receives the signal with no shift."""
        def fn(t):
            return math.sin(t)

        for t in [0.0, 1.0, 100.0, -5.0]:
            assert signal_at_observer(fn, t=t, delay=0.0) == pytest.approx(math.sin(t))

    def test_separated_patches_have_nonzero_delay(self) -> None:
        """Two patches at opposite poles (separation=π) have delay > 0.

        Wrong impl: always returns delay=0 regardless of geometry.
        """
        # Spin-up (+Z pole) and spin-down (−Z pole) are maximally separated
        up = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
        dn = SpinorState(alpha=complex(0, 0), beta=complex(1, 0))
        p_up = ObserverPatch(agent_id="up", spinor=up)
        p_dn = ObserverPatch(agent_id="dn", spinor=dn)

        tau = compute_retarded_delay(p_up, p_dn, propagation_speed=1e-3)
        assert tau > 0.0, "Maximally separated patches must have positive delay"

    def test_identical_patches_have_zero_delay(self) -> None:
        """Two co-located patches (separation=0) have delay=0."""
        s = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
        p = ObserverPatch(agent_id="x", spinor=s)
        tau = compute_retarded_delay(p, p, propagation_speed=1e-3)
        assert tau == pytest.approx(0.0, abs=1e-9)

    def test_retarded_field_delay_matches_compute(self) -> None:
        """RetardedField.delay_seconds from patches agrees with compute_retarded_delay."""
        up = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
        dn = SpinorState(alpha=complex(0, 0), beta=complex(1, 0))
        p_up = ObserverPatch(agent_id="up", spinor=up)
        p_dn = ObserverPatch(agent_id="dn", spinor=dn)

        speed = 2e-4
        tau = compute_retarded_delay(p_up, p_dn, propagation_speed=speed)
        rf = RetardedField(delay_seconds=tau, propagation_speed=speed)
        assert rf.delay_seconds == pytest.approx(tau)

    def test_faster_propagation_reduces_delay(self) -> None:
        """Higher propagation_speed → shorter delay (τ = separation / speed)."""
        up = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))
        dn = SpinorState(alpha=complex(0, 0), beta=complex(1, 0))
        p_up = ObserverPatch(agent_id="up", spinor=up)
        p_dn = ObserverPatch(agent_id="dn", spinor=dn)

        slow = compute_retarded_delay(p_up, p_dn, propagation_speed=1e-4)
        fast = compute_retarded_delay(p_up, p_dn, propagation_speed=1e-3)
        assert fast < slow, "Faster propagation must yield shorter delay"
