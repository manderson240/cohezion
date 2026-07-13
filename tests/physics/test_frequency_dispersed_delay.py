"""Tests for FrequencyDispersedDelay — pulsar dispersion model in OPH.

Grounded in MWA millisecond pulsar PSR J0125−5854 (2026-06-27 research):
    τ_DM = K_DM × DM / ν²

where K_DM = 4148.808 MHz² pc⁻¹ cm³ s, DM is the dispersion measure
(pc cm⁻³), and ν is the observation frequency (MHz).

Two stacked delays in pulsar timing:
  1. Dispersion delay: τ_DM (frequency-dependent, dominant at MWA bands)
  2. Geometric (Roemer) delay: ±a_sin_i / c (orbital, frequency-independent)

In OPH terms: the S² screen acts as a frequency-dispersive medium; signals
at different spectral channels arrive at different retarded times.  This
extends RetardedField to the frequency axis.
"""

from __future__ import annotations

import pytest


pytest.importorskip(
    "cohezion.physics.observer_patch", reason="TDD-red: FrequencyDispersedDelay not yet implemented"
)

import math

import pytest

from cohezion.physics.observer_patch import (
    _K_DM,
    FrequencyDispersedDelay,
    signal_at_observer,
    stack_delays,
)


# ---------------------------------------------------------------------------
# T1 structural
# ---------------------------------------------------------------------------


class TestFrequencyDispersedDelayStructural:
    """API surface must exist with correct types."""

    def test_dataclass_importable_and_instantiable(self) -> None:
        fd = FrequencyDispersedDelay(dm=9.9, nu_mhz=154.0)
        assert fd.dm == pytest.approx(9.9)
        assert fd.nu_mhz == pytest.approx(154.0)

    def test_delay_seconds_property_returns_float(self) -> None:
        fd = FrequencyDispersedDelay(dm=1.0, nu_mhz=200.0)
        d = fd.delay_seconds
        assert isinstance(d, float), f"Expected float, got {type(d)}"

    def test_k_dm_module_constant_accessible(self) -> None:
        """_K_DM is the standard pulsar dispersion constant 4148.808 MHz² pc⁻¹ cm³ s."""
        assert isinstance(_K_DM, float)
        assert pytest.approx(4148.808, rel=1e-6) == _K_DM

    def test_stack_delays_callable(self) -> None:
        """stack_delays(*delays) sums multiple delay contributions."""
        total = stack_delays(1.0, 2.5, 0.5)
        assert total == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# T2 discriminating
# ---------------------------------------------------------------------------


class TestFrequencyDispersedDelayDiscriminating:
    """Dispersion must vary as ν⁻², not linearly or constantly."""

    def test_zero_dm_gives_zero_delay(self) -> None:
        """DM=0 ↔ no dispersive medium ↔ delay must be exactly 0.

        Wrong impl: returns K_DM / ν² (ignores DM factor).
        """
        fd = FrequencyDispersedDelay(dm=0.0, nu_mhz=154.0)
        assert fd.delay_seconds == pytest.approx(0.0, abs=1e-15)

    def test_zero_frequency_gives_infinite_delay(self) -> None:
        """ν → 0 means τ → ∞ (low-frequency cutoff).

        Wrong impl: returns 0 or raises ZeroDivisionError.
        """
        fd = FrequencyDispersedDelay(dm=10.0, nu_mhz=0.0)
        assert math.isinf(fd.delay_seconds)

    def test_mwa_psr_j0125_numerical_calibration(self) -> None:
        """Numerical anchor from MWA PSR J0125−5854 (2026-06-27 vault research).

        DM ≈ 9.9 pc cm⁻³, ν = 154 MHz → τ_DM ≈ 1.731 s.

        Wrong impl: uses linear DM/ν or wrong K_DM units.
        Discriminating: must match to within 0.1% relative.
        """
        fd = FrequencyDispersedDelay(dm=9.9, nu_mhz=154.0)
        expected = 4148.808 * 9.9 / (154.0**2)  # ≈ 1.7317 s
        assert fd.delay_seconds == pytest.approx(expected, rel=1e-3), (
            f"MWA calibration: expected ≈{expected:.4f} s, got {fd.delay_seconds:.4f} s"
        )

    def test_lower_frequency_gives_longer_delay(self) -> None:
        """τ ∝ ν⁻²: 100 MHz channel arrives later than 200 MHz channel.

        Wrong impl: delay increases with frequency (sign error).
        Discriminating: τ(100 MHz) must be strictly greater than τ(200 MHz).
        """
        fd_low = FrequencyDispersedDelay(dm=5.0, nu_mhz=100.0)
        fd_high = FrequencyDispersedDelay(dm=5.0, nu_mhz=200.0)
        assert fd_low.delay_seconds > fd_high.delay_seconds, (
            "Lower frequency must arrive LATER (longer delay)"
        )

    def test_halving_frequency_quadruples_delay(self) -> None:
        """τ ∝ ν⁻²: halving ν doubles delay twice → 4× total.

        Wrong impl: linear τ ∝ ν⁻¹ would give 2× not 4×.
        Discriminating: ratio must be 4.0 within 0.01%.
        """
        dm = 7.0
        fd_full = FrequencyDispersedDelay(dm=dm, nu_mhz=200.0)
        fd_half = FrequencyDispersedDelay(dm=dm, nu_mhz=100.0)
        ratio = fd_half.delay_seconds / fd_full.delay_seconds
        assert ratio == pytest.approx(4.0, rel=1e-4), (
            f"Halving ν must quadruple delay (ν⁻² law); ratio={ratio:.6f}"
        )

    def test_stack_delays_combines_dispersion_and_geometric(self) -> None:
        """stack_delays sums dispersion + Roemer (or any geometric) delay.

        PSR J0125−5854: τ_DM ≈ 1.73 s + Roemer ≈ 241 s → total ≈ 242.73 s.
        Wrong impl: returns max() or only the first argument.
        """
        fd = FrequencyDispersedDelay(dm=9.9, nu_mhz=154.0)
        roemer_s = 241.0  # ±a sin(i)/c for this system
        total = stack_delays(fd.delay_seconds, roemer_s)
        assert total == pytest.approx(fd.delay_seconds + roemer_s, rel=1e-9)

    def test_signal_at_observer_uses_dispersed_delay(self) -> None:
        """FrequencyDispersedDelay integrates with signal_at_observer.

        A step-function signal emitted at t=0 must not arrive at t < τ_DM.
        """
        fd = FrequencyDispersedDelay(dm=9.9, nu_mhz=154.0)  # τ ≈ 1.73 s
        def step(t):
            return 1.0 if t >= 0.0 else 0.0

        before = signal_at_observer(step, t=1.0, delay=fd.delay_seconds)
        after = signal_at_observer(step, t=3.0, delay=fd.delay_seconds)

        assert before == pytest.approx(0.0), "Signal must not arrive before τ_DM"
        assert after == pytest.approx(1.0), "Signal must arrive after τ_DM"
