"""CompoundHealthOracle — unified health synthesis for the compound loop.

Synthesizes two independent monitoring signals into a single actionable
``HealthAssessment``:

1. ``RollingRegimeTracker`` — Higuchi FD regime (STUCK / HIHO / CHAOTIC)
   measures the *texture* of the quality-score time series.  HIHO is the
   target Brownian equilibrium; STUCK means the loop is over-exploiting;
   CHAOTIC means quality is oscillating wildly.

2. ``DegradationDetector`` (optional) — metric-based tier suggestion derived
   from cache-hit-rate, coherence, and token-efficiency trends.  When wired,
   it provides the *current* tier recommendation (npu / igpu / cpu).  When
   absent the oracle falls back to regime-driven defaults.

The oracle is a *consumer* of both producers, not another detector.  It does
not write to either; it reads their latest state and translates it into a
``HealthAssessment`` that compound loop consumers can act on directly.

Example
-------
>>> oracle = CompoundHealthOracle(window_size=20)
>>> for score in quality_history:
...     assessment = oracle.assess(score)
>>> if not oracle.is_healthy():
...     route_to(assessment.tier_recommendation)
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.inference.fractal_metrics import FractalRegime, RollingRegimeTracker


logger = logging.getLogger(__name__)

_DEFAULT_STATE_PATH = Path.home() / ".cohezion" / "oracle_state.json"


# Tier escalation order (cheapest → most capable).
_TIER_ORDER: tuple[str, ...] = ("npu", "igpu", "cpu", "cloud")

# Quality-statistic thresholds. These answer the question FD cannot: is quality good, is it
# falling, is it steady. Deliberately conservative — the veto only fires for a window that is
# BOTH high and steady, so a genuinely troubled lane still reaches the FD-derived branches.
_HEALTHY_MEAN: float = 0.70  # mean at or above this is a lane doing its job
_STEADY_STDEV: float = 0.15  # dispersion at or below this is stable, not oscillating

# Degradation needs BOTH tests, because either alone produces false alarms:
#
#   significance — a slope must exceed _SLOPE_SIGMAS standard errors. An ABSOLUTE slope
#     threshold cannot work: SE(slope) ~= sigma / (sd_x * sqrt(n)), so for sigma=0.05 over 20
#     samples SE is ~0.0019. A fixed -0.002 cut is therefore ~1 SE, which pure noise crosses
#     roughly 16% of the time. That was the first version of this fix, and its own fixture-guard
#     test caught it (2026-08-16) — a false-alarm generator inside a fix for false alarms.
#
#   materiality — significance alone flags a tiny but very clean decline. A 0.001 drop measured
#     precisely is still not a health problem, so the fitted end-to-end fall must also clear
#     _MIN_TOTAL_DROP.
_SLOPE_SIGMAS: float = 2.0
_MIN_TOTAL_DROP: float = 0.10


def _escalate_tier(current: str) -> str:
    """Return the next-more-capable tier, capped at 'cpu' (never auto-escalate to cloud)."""
    try:
        idx = _TIER_ORDER.index(current)
    except ValueError:
        return "igpu"  # unknown tier → escalate to igpu as safe midpoint
    return _TIER_ORDER[min(idx + 1, len(_TIER_ORDER) - 2)]  # cap at cpu


@dataclass
class HealthAssessment:
    """Unified health snapshot from the compound loop oracle.

    Attributes
    ----------
    regime : FractalRegime
        Higuchi FD regime — STUCK / HIHO / CHAOTIC.
    tier_recommendation : str
        Recommended routing tier — "npu" | "igpu" | "cpu".  Never "cloud"
        (the oracle does not authorize cloud escalation; it only adjusts
        within the local silicon fleet).
    confidence : float
        Confidence in the current assessment, in [0.0, 1.0].  Derived from
        HIHO deviation: ``max(0.0, 1.0 - 2.0 * deviation)``.  Low confidence
        during warm-up (< min_samples) or when quality is far from 0.5.
    alert_level : str
        "ok" (HIHO), "warn" (STUCK), or "critical" (CHAOTIC).
    alerts : list[str]
        Human-readable alert strings.  Empty list when alert_level is "ok".
    """

    regime: FractalRegime
    tier_recommendation: str
    confidence: float
    alert_level: str
    alerts: list[str] = field(default_factory=list)


class CompoundHealthOracle:
    """Unified health oracle synthesizing fractal regime + degradation signals.

    Parameters
    ----------
    window_size : int
        Rolling window size for the ``RollingRegimeTracker``.  Minimum 20
        for a reliable Higuchi FD estimate; larger windows give more stable
        regime classification at the cost of slower adaptation.
    degradation_detector : Any, optional
        A ``DegradationDetector`` instance (duck-typed; must expose
        ``suggest_routing_tier() -> str``).  When provided, its tier
        suggestion informs ``HealthAssessment.tier_recommendation``.
        When absent, the oracle falls back to regime-driven defaults.
    """

    def __init__(
        self,
        window_size: int = 80,
        degradation_detector: Any = None,
    ) -> None:
        self._tracker = RollingRegimeTracker(window_size=window_size)
        self._detector = degradation_detector
        self._last_assessment: HealthAssessment | None = None

    # ── Public API ─────────────────────────────────────────────────────────

    def assess(
        self,
        quality_score: float,
        execution_metrics: dict | None = None,  # reserved for future signal fusion
    ) -> HealthAssessment:
        """Ingest a quality score and return the current health assessment.

        Parameters
        ----------
        quality_score : float
            Scalar quality score from the latest compound loop execution (0–1).
        execution_metrics : dict, optional
            Currently unused in synthesis logic; reserved for future fusion.

        Returns
        -------
        HealthAssessment
            Synthesized assessment reflecting the current regime and tier
            recommendation.  Returns a "warming-up" assessment (regime=STUCK,
            confidence=0.0) while the tracker is below its min_samples gate.
        """
        regime = self._tracker.update(quality_score)
        deviation = self._tracker.deviation()
        confidence = max(0.0, min(1.0, 1.0 - 2.0 * deviation))

        if regime is None:
            # Below min_samples — use safe worst-case defaults.
            assessment = HealthAssessment(
                regime=FractalRegime.STUCK,
                tier_recommendation="igpu",
                confidence=0.0,
                alert_level="warn",
                alerts=[
                    "Oracle warming up — insufficient samples for reliable regime classification."
                ],
            )
            self._last_assessment = assessment
            return assessment

        assessment = self._synthesize(regime, confidence)
        self._last_assessment = assessment
        return assessment

    def is_healthy(self) -> bool:
        """Return True iff the latest assessment is alert_level="ok" (HIHO regime).

        Returns False before the first assess() call (no data = not healthy).
        """
        if self._last_assessment is None:
            return False
        return self._last_assessment.alert_level == "ok"

    @property
    def tracker(self) -> RollingRegimeTracker:
        """Direct access to the underlying RollingRegimeTracker (read-only intent)."""
        return self._tracker

    # ── Internal helpers ───────────────────────────────────────────────────

    def _quality_stats(self) -> tuple[float, float, float] | None:
        """(mean, slope, stdev) over the tracker's rolling window, or None if unavailable.

        Higuchi FD is amplitude-INVARIANT by construction: it characterises the SHAPE of a curve,
        not its magnitude. That is correct for its own purpose and wrong as a health signal, where
        magnitude is the entire question. Measured on this class 2026-08-16:

            0.85 +/- iid noise sd=0.005 (healthy)   -> CHAOTIC / critical / escalate to cpu
            0.9 -> 0.4 linear decline   (degrading) -> STUCK   / warn
            0.9 then 0.2 collapse       (very bad)  -> STUCK   / warn, confidence 0.93

        Both errors point the wrong way, because what FD actually discriminates is sample-to-
        sample AUTOCORRELATION: any i.i.d. jitter reads CHAOTIC however small, while a smooth
        decline reads as ordered. Health needs level, trend and dispersion instead.
        """
        scores = list(getattr(self._tracker, "_scores", []) or [])
        if len(scores) < 3:
            return None
        n = len(scores)
        mean = sum(scores) / n
        # Least-squares slope over the window; negative means quality is falling.
        xs = range(n)
        x_mean = (n - 1) / 2.0
        denom = sum((x - x_mean) ** 2 for x in xs)
        slope = (
            sum((x - x_mean) * (s - mean) for x, s in zip(xs, scores, strict=False)) / denom
            if denom
            else 0.0
        )
        stdev = (sum((s - mean) ** 2 for s in scores) / n) ** 0.5
        return mean, slope, stdev

    def _is_degrading(self, scores: list[float], slope: float) -> bool:
        """True when the window falls both SIGNIFICANTLY and MATERIALLY. See the constants."""
        n = len(scores)
        if n < 4 or slope >= 0.0:
            return False
        if abs(slope) * n < _MIN_TOTAL_DROP:  # materiality
            return False
        x_mean = (n - 1) / 2.0
        denom = sum((x - x_mean) ** 2 for x in range(n))
        if denom <= 0:
            return False
        y_mean = sum(scores) / n
        intercept = y_mean - slope * x_mean
        resid_sq = sum((s - (intercept + slope * x)) ** 2 for x, s in enumerate(scores))
        # SE of the slope from the residuals — self-calibrating to however noisy this lane is.
        se = ((resid_sq / (n - 2)) / denom) ** 0.5 if n > 2 and resid_sq > 0 else 0.0
        return se == 0.0 or abs(slope) >= _SLOPE_SIGMAS * se

    def _synthesize(self, regime: FractalRegime, confidence: float) -> HealthAssessment:
        """Produce a HealthAssessment from a confirmed regime + deviation-confidence.

        The FD regime sets the SHAPE story; quality statistics decide the ALERT. Without that
        split the oracle raised critical on stable lanes and warn on collapses — see
        :meth:`_quality_stats` for the measured evidence.
        """
        detector_tier: str | None = self._read_detector_tier()
        stats = self._quality_stats()

        if stats is not None:
            mean, slope, stdev = stats
            # A falling window is a real degradation whatever its shape. Checked FIRST so a
            # smooth decline (which FD calls STUCK or even HIHO) cannot be reported as ok.
            if self._is_degrading(list(getattr(self._tracker, "_scores", []) or []), slope):
                base = detector_tier or "npu"
                escalated = _escalate_tier(base)
                return HealthAssessment(
                    regime=regime,
                    tier_recommendation=escalated,
                    confidence=confidence,
                    alert_level="critical",
                    alerts=[
                        f"quality DEGRADING: slope {slope:+.4f}/sample over the window, "
                        f"mean {mean:.3f}. Escalating {base!r} -> {escalated!r}. "
                        f"(FD regime {regime.value!r} is shape-only and does not see this.)"
                    ],
                )
            # A high, steady window is healthy no matter what the FD shape says. This is the
            # veto that stops i.i.d. jitter of sd=0.005 from reading as CHAOTIC/critical.
            if mean >= _HEALTHY_MEAN and stdev <= _STEADY_STDEV:
                return HealthAssessment(
                    regime=regime,
                    tier_recommendation=detector_tier or "npu",
                    confidence=confidence,
                    alert_level="ok",
                    alerts=[],
                )

        if regime is FractalRegime.HIHO:
            tier = detector_tier if detector_tier is not None else "npu"
            return HealthAssessment(
                regime=regime,
                tier_recommendation=tier,
                confidence=confidence,
                alert_level="ok",
                alerts=[],
            )

        if regime is FractalRegime.STUCK:
            base_tier = detector_tier if detector_tier is not None else "npu"
            escalated = _escalate_tier(base_tier)
            return HealthAssessment(
                regime=regime,
                tier_recommendation=escalated,
                confidence=confidence,
                alert_level="warn",
                alerts=[
                    f"STUCK regime (FD < 1.3): loop is over-exploiting. "
                    f"Escalating tier {base_tier!r} → {escalated!r} to restore exploration."
                ],
            )

        # CHAOTIC
        chaotic_tier = "cpu"  # max local tier — slow down, increase reasoning depth
        return HealthAssessment(
            regime=regime,
            tier_recommendation=chaotic_tier,
            confidence=confidence,
            alert_level="critical",
            alerts=[
                "CHAOTIC regime (FD > 1.7): quality oscillating wildly. "
                f"Forcing tier → {chaotic_tier!r} to stabilize. Check model health."
            ],
        )

    def _read_detector_tier(self) -> str | None:
        """Return the degradation detector's tier suggestion, or None if unavailable."""
        if self._detector is None:
            return None
        try:
            tier = self._detector.suggest_routing_tier()
            if tier in _TIER_ORDER:
                return tier
        except Exception:
            pass
        return None

    # ── Serialization (HO1–HO3 harness invariants) ────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict of oracle state for cross-session persistence.

        Keys
        ----
        window_size : int
        min_samples : int
        scores : list[float]
            Ordered scores in the rolling window (oldest → newest).
        regime_history : list[str]
            FractalRegime values as strings (e.g. "hiho", "stuck", "chaotic").
        last_assessment : dict | None
            Serialized HealthAssessment or None if assess() hasn't been called.
        """
        regime_history = [r.value for r in self._tracker.regime_history()]
        scores = list(self._tracker._scores)

        last: dict[str, Any] | None = None
        if self._last_assessment is not None:
            last = {
                "regime": self._last_assessment.regime.value,
                "tier_recommendation": self._last_assessment.tier_recommendation,
                "confidence": self._last_assessment.confidence,
                "alert_level": self._last_assessment.alert_level,
                "alerts": list(self._last_assessment.alerts),
            }

        return {
            "window_size": self._tracker._window_size,
            "min_samples": self._tracker._min_samples,
            "scores": scores,
            "regime_history": regime_history,
            "last_assessment": last,
        }

    @classmethod
    def from_dict(
        cls,
        state: dict[str, Any],
        degradation_detector: Any = None,
    ) -> CompoundHealthOracle:
        """Restore an oracle from a previously serialized dict.

        CB16-pattern safe defaults: missing keys fall back to empty/zero state
        (never crash on a partial or stale file).
        """
        window_size = int(state.get("window_size", 80))
        oracle = cls(window_size=window_size, degradation_detector=degradation_detector)

        # Restore min_samples (may differ from window_size for tests)
        min_samples = int(state.get("min_samples", window_size))
        oracle._tracker._min_samples = min_samples

        # Restore rolling window scores
        scores = state.get("scores", [])
        oracle._tracker._scores.extend(float(s) for s in scores)

        # Restore regime history
        regime_str_list = state.get("regime_history", [])
        _str_to_regime = {r.value: r for r in FractalRegime}
        for rs in regime_str_list:
            regime = _str_to_regime.get(rs)
            if regime is not None:
                oracle._tracker._regime_history.append(regime)

        # Restore last assessment (derived state — useful for is_healthy() on startup)
        la = state.get("last_assessment")
        if la is not None:
            try:
                oracle._last_assessment = HealthAssessment(
                    regime=_str_to_regime.get(la["regime"], FractalRegime.STUCK),
                    tier_recommendation=la.get("tier_recommendation", "igpu"),
                    confidence=float(la.get("confidence", 0.0)),
                    alert_level=la.get("alert_level", "warn"),
                    alerts=list(la.get("alerts", [])),
                )
            except Exception:
                pass  # fail-open: missing/corrupt last_assessment is fine

        return oracle

    def save_state(self, path: str | Path | None = None) -> None:
        """Persist oracle state to a JSON file.

        Parameters
        ----------
        path : str or Path, optional
            Target file path.  Defaults to ``~/.cohezion/oracle_state.json``.
        """
        target = Path(path) if path is not None else _DEFAULT_STATE_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
            logger.debug("CompoundHealthOracle: saved state to %s", target)
        except Exception as exc:
            logger.debug("CompoundHealthOracle: save_state failed (non-blocking): %s", exc)

    def restore_state(self, path: str | Path | None = None) -> bool:
        """Restore oracle state from a JSON file.

        Returns
        -------
        bool
            True on success, False when the file is absent or corrupt (fail-open).
        """
        target = Path(path) if path is not None else _DEFAULT_STATE_PATH
        if not target.exists():
            return False
        try:
            state = json.loads(target.read_text(encoding="utf-8"))
            # Replay scores and regime history into self (in-place restoration)
            window_size = int(state.get("window_size", self._tracker._window_size))
            min_samples = int(state.get("min_samples", self._tracker._min_samples))
            # Only restore if window_size matches (prevents corrupt/mismatched state)
            if window_size != self._tracker._window_size:
                logger.debug(
                    "CompoundHealthOracle: restore_state window_size mismatch (%d vs %d), skipping",
                    window_size,
                    self._tracker._window_size,
                )
                return False

            self._tracker._min_samples = min_samples
            self._tracker._scores.extend(float(s) for s in state.get("scores", []))

            _str_to_regime = {r.value: r for r in FractalRegime}
            for rs in state.get("regime_history", []):
                regime = _str_to_regime.get(rs)
                if regime is not None:
                    self._tracker._regime_history.append(regime)

            la = state.get("last_assessment")
            if la is not None:
                with contextlib.suppress(Exception):
                    self._last_assessment = HealthAssessment(
                        regime=_str_to_regime.get(la["regime"], FractalRegime.STUCK),
                        tier_recommendation=la.get("tier_recommendation", "igpu"),
                        confidence=float(la.get("confidence", 0.0)),
                        alert_level=la.get("alert_level", "warn"),
                        alerts=list(la.get("alerts", [])),
                    )

            logger.debug(
                "CompoundHealthOracle: restored state from %s (%d scores, %d regime entries)",
                target,
                len(self._tracker._scores),
                len(self._tracker._regime_history),
            )
            return True
        except Exception as exc:
            logger.debug("CompoundHealthOracle: restore_state failed (non-blocking): %s", exc)
            return False

    def to_health_dict(self) -> dict[str, Any]:
        """Return a compact health summary for API exposure.

        Safe to call even before the first assess() call.
        """
        la = self._last_assessment
        return {
            "regime": la.regime.value if la else "warming_up",
            "tier_recommendation": la.tier_recommendation if la else "igpu",
            "confidence": round(la.confidence, 4) if la else 0.0,
            "alert_level": la.alert_level if la else "warn",
            "alerts": list(la.alerts) if la else [],
            "window_fill": len(self._tracker),
            "is_healthy": self.is_healthy(),
        }
