"""OS1-OS4: oscillation detection must catch what higuchi_fd is blind to — and only that.

Every threshold in this file traces to a measurement recorded in the module docstring.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.oscillation_detector import (
    OSCILLATION_THRESHOLD,
    is_hidden_thrash,
    score,
)
from cohezion.inference.fractal_metrics import higuchi_fd


N = 20
_T = np.arange(N)


def _period(p: float, amp: float = 0.25, base: float = 0.65) -> list[float]:
    return list(base + amp * np.sin(2 * np.pi * _T / p))


class TestOS1TheBlindnessIsReal:
    """The premise. If higuchi_fd stopped mislabelling period-8 tones, this module is moot."""

    def test_period_8_pure_tone_is_misread_as_healthy_by_fd(self) -> None:
        fd = higuchi_fd(_period(8))
        assert 1.3 <= fd <= 1.7, (
            f"premise broken: period-8 tone now reads FD={fd:.3f}, outside the CC1 healthy "
            "band. If this fails, re-derive whether this detector is still needed."
        )

    def test_slow_tone_is_correctly_read_as_stuck(self) -> None:
        """Discriminating: shows the misread is period-specific, not a blanket FD failure."""
        assert higuchi_fd(_period(32)) < 1.3


class TestOS2CatchesOscillation:
    def test_period_8_cycle_scores_high(self) -> None:
        assert score(_period(8)) > OSCILLATION_THRESHOLD

    def test_ab_alternation_scores_high(self) -> None:
        """Period-2 has no k/2 lag; it needs the negative-lag-1 branch."""
        assert score([0.9, 0.4] * (N // 2)) > OSCILLATION_THRESHOLD

    def test_period_4_cycle_scores_high(self) -> None:
        assert score([0.9, 0.8, 0.4, 0.5] * (N // 4)) > OSCILLATION_THRESHOLD


class TestOS3DoesNotFireOnHealthyOrStuck:
    """THE discriminating class. A prior design (raw max-autocorrelation) passed every test in
    OS2 and still had to be rejected, because it scored 0.821 on Brownian drift. Correlation
    is not oscillation."""

    def test_brownian_drift_does_not_fire(self) -> None:
        rng = np.random.default_rng(3)
        drift = list(np.clip(0.7 + np.cumsum(rng.normal(0, 0.04, N)), 0, 1))
        s = score(drift)
        assert s <= OSCILLATION_THRESHOLD, f"fired on healthy drift (score={s:.3f})"

    def test_monotone_degradation_does_not_fire(self) -> None:
        assert score(list(np.linspace(0.9, 0.3, N))) <= OSCILLATION_THRESHOLD

    def test_flat_series_scores_zero(self) -> None:
        assert score([0.62] * N) == 0.0

    def test_noisy_series_does_not_fire(self) -> None:
        rng = np.random.default_rng(11)
        assert score(list(np.clip(0.7 + rng.normal(0, 0.12, N), 0, 1))) <= OSCILLATION_THRESHOLD

    def test_short_series_returns_zero(self) -> None:
        assert score([0.1, 0.9, 0.1, 0.9]) == 0.0


class TestOS4HiddenThrashGate:
    """The composite signal: oscillating AND inside the band where FD says healthy."""

    def test_period_8_is_hidden_thrash(self) -> None:
        s = _period(8)
        assert is_hidden_thrash(s, higuchi_fd(s)) is True

    def test_oscillation_outside_the_healthy_band_is_not_hidden(self) -> None:
        """Discriminating: A/B alternation oscillates hard, but FD already calls it chaotic
        (2.0), so FD is NOT being fooled and this is not the hidden case."""
        s = [0.9, 0.4] * (N // 2)
        fd = higuchi_fd(s)
        assert fd > 1.7, f"expected FD to already flag alternation, got {fd:.3f}"
        assert is_hidden_thrash(s, fd) is False

    def test_healthy_drift_in_band_is_not_hidden_thrash(self) -> None:
        rng = np.random.default_rng(3)
        drift = list(np.clip(0.7 + np.cumsum(rng.normal(0, 0.04, N)), 0, 1))
        assert is_hidden_thrash(drift, higuchi_fd(drift)) is False
