"""The health oracle must answer a question about QUALITY, not about curve shape.

Measured on the production class 2026-08-16, before this fix:

    0.85 +/- iid noise sd=0.005 (healthy)  -> CHAOTIC / critical / escalate to cpu
    0.95 +/- 0.01               (excellent)-> CHAOTIC / critical / escalate to cpu
    0.9 -> 0.4 linear decline   (degrading)-> STUCK   / warn
    0.9 then 0.2 collapse       (very bad) -> STUCK   / warn, confidence 0.93

Both errors point the wrong way: healthy lanes raised critical and were escalated to the
expensive tier, while a collapse raised only warn — with HIGHER confidence.

Root cause: the alert was derived solely from Higuchi FD, whose bands are calibrated on Brownian
motion (a cumulative, non-stationary process) while quality scores are bounded and stationary.
FD is amplitude-invariant by construction, so what it actually discriminates is sample-to-sample
autocorrelation — i.i.d. jitter reads CHAOTIC at ANY amplitude, and a smooth decline reads as
ordered. Every test here is written to FAIL against the FD-only implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.compound.compound_health_oracle import CompoundHealthOracle


def _drive(scores: list[float]):
    oracle = CompoundHealthOracle()
    assessment = None
    for s in scores:
        assessment = oracle.assess(s)
    return assessment


class TestHealthyLanesAreNotAlarmed:
    @pytest.mark.parametrize("sd", [0.005, 0.02, 0.05])
    def test_steady_high_quality_is_ok_at_any_jitter(self, sd: float) -> None:
        """DISCRIMINATING: FD calls all of these CHAOTIC/critical.

        i.i.d. jitter reads as chaos regardless of amplitude, so an FD-only oracle raised
        critical on a lane holding 0.85 with half-a-percent noise — and escalated it to the
        most expensive local tier, which is a cost leak in a cost-ordered architecture.
        """
        rng = np.random.default_rng(7)
        a = _drive(list(np.clip(0.85 + rng.normal(0, sd, 100), 0.0, 1.0)))
        assert a.alert_level == "ok", f"healthy lane (sd={sd}) alarmed as {a.alert_level}"
        assert a.tier_recommendation != "cpu", "healthy lane escalated to the expensive tier"

    def test_excellent_quality_is_ok(self) -> None:
        rng = np.random.default_rng(11)
        a = _drive(list(np.clip(0.95 + rng.normal(0, 0.01, 100), 0.0, 1.0)))
        assert a.alert_level == "ok"


class TestDegradationIsCaught:
    def test_linear_decline_is_critical_not_warn(self) -> None:
        """DISCRIMINATING: FD calls a smooth decline STUCK, i.e. merely 'over-exploiting'."""
        a = _drive([0.9 - 0.5 * i / 99 for i in range(100)])
        assert a.alert_level == "critical", f"degradation reported as {a.alert_level}"
        assert "DEGRADING" in " ".join(a.alerts)

    def test_collapse_is_critical(self) -> None:
        """A step from 0.9 to 0.2 previously reported warn WITH HIGHER CONFIDENCE than the
        false critical on a healthy lane — the worst possible ordering."""
        a = _drive([0.9] * 50 + [0.2] * 50)
        assert a.alert_level == "critical"

    def test_degradation_escalates_the_tier(self) -> None:
        a = _drive([0.9 - 0.5 * i / 99 for i in range(100)])
        assert a.tier_recommendation in {"igpu", "cpu"}


class TestTheVetoIsNotBlanket:
    """The fix must not simply silence the oracle — it has to still fire on real trouble."""

    def test_low_quality_is_not_vetoed_to_ok(self) -> None:
        """Steady but BAD: mean below the healthy floor must not reach the ok branch."""
        rng = np.random.default_rng(3)
        a = _drive(list(np.clip(0.30 + rng.normal(0, 0.01, 100), 0.0, 1.0)))
        assert a.alert_level != "ok", "a steady-but-poor lane was vetoed to ok"

    def test_wildly_oscillating_is_not_vetoed_to_ok(self) -> None:
        """High mean but high dispersion: genuinely unstable, must not be called ok."""
        a = _drive([0.95 if i % 2 == 0 else 0.35 for i in range(100)])
        assert a.alert_level != "ok", "an oscillating lane was vetoed to ok"

    def test_rising_quality_is_not_reported_as_degrading(self) -> None:
        """Slope sign must matter — improvement is not degradation."""
        a = _drive([0.4 + 0.5 * i / 99 for i in range(100)])
        assert "DEGRADING" not in " ".join(a.alerts)


class TestRegimeIsStillReported:
    def test_regime_survives_as_context(self) -> None:
        """FD is still a real signal about SHAPE; the fix changes what drives the ALERT,
        it does not delete the regime. A caller reading `.regime` keeps working."""
        rng = np.random.default_rng(5)
        a = _drive(list(np.clip(0.85 + rng.normal(0, 0.01, 100), 0.0, 1.0)))
        assert a.regime is not None
