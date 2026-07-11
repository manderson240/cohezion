"""Runtime "frictional resistance" Φ — a composite active-inference bottleneck signal.

OBSERVE-ONLY: computes Φ ∈ [0,1] and classifies a hysteresis regime. It NEVER triggers
Electro-Nuclear Collapse (``SymmetryBreaking.cool``) or regeneration — wiring those to Φ is a
separate, calibration-gated step. See the design spec:
``vault/research/2026-07-11-friction-metric-and-physics-spec-mapping.md`` (§2–§4).

Φ composes signals the system ALREADY produces (map-don't-rebuild):
  - surprise            ``JEPAWorldModel.surprise_score()``           prediction error (primary)
  - phase_divergence    ``ExecutionAlignment.misalignment_score``     Knower-vs-Doer drift
  - entropy_production  ``ThermodynamicMetrics ... entropy_production_rate``  dissipation
  - quality_delta       quality-score change per cycle                stagnation (gated)

Rejected inputs: gradient volatility / loss stagnation — training-regime metrics, not runtime
signals. Perplexity/entropy is an auxiliary uncertainty sensor, not the trigger.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class FrictionReading:
    """One friction observation. ``regime`` is an OBSERVE-ONLY label — nothing acts on it."""

    phi: float
    surprise: float
    phase_divergence: float
    entropy_production: float
    stagnation: float
    regime: str  # "navigate" | "friction"


class FrictionMetric:
    """Composite runtime friction Φ ∈ [0,1] with a hysteresis regime classifier.

    Unbounded ≥0 inputs (surprise, entropy_production) are squashed to [0,1] via a saturating
    map ``x/(x+μ)`` against the rolling mean μ of PRIOR samples (so x==μ → 0.5, HIHO-centred;
    the first sample has no baseline and maps to the 0.5 grace value). ``phase_divergence`` is
    already [0,1]. Stagnation is CONJUNCTIVE: a quality plateau counts as friction only when
    surprise is also high ("working hard, going nowhere").

    The hysteresis classifier enters the "friction" regime only on Φ sustained above
    ``setpoint+band`` and exits below ``setpoint-band`` — preventing chatter around the
    threshold. It is a label generator, not an actuator.
    """

    def __init__(
        self,
        *,
        w_surprise: float = 0.40,
        w_divergence: float = 0.25,
        w_entropy: float = 0.25,
        w_stagnation: float = 0.10,
        setpoint: float = 0.5,  # HIHO
        band: float = 0.1,  # hysteresis half-width
        sustain: int = 2,  # cycles above enter-threshold before the regime flips
        window: int = 20,  # rolling window for saturating normalization
        stagnation_scale: float = 10.0,
    ) -> None:
        total = w_surprise + w_divergence + w_entropy + w_stagnation
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"friction weights must sum to 1.0, got {total}")
        self._w = (w_surprise, w_divergence, w_entropy, w_stagnation)
        self._enter = setpoint + band
        self._exit = setpoint - band
        self._sustain = sustain
        self._stagnation_scale = stagnation_scale
        self._surprise_hist: deque[float] = deque(maxlen=window)
        self._entropy_hist: deque[float] = deque(maxlen=window)
        self._in_friction = False
        self._streak = 0

    @staticmethod
    def _saturate(x: float, hist: deque[float]) -> float:
        """Map an unbounded x≥0 to [0,1) via x/(x+μ); μ = mean of PRIOR samples.

        First observation (no prior history) returns the 0.5 grace value.
        """
        x = max(0.0, float(x))
        mu = (sum(hist) / len(hist)) if hist else None
        hist.append(x)
        if mu is None:
            return 0.5
        if x + mu <= 0.0:
            return 0.0
        return x / (x + mu)

    def compute(
        self,
        *,
        surprise: float,
        phase_divergence: float,
        entropy_production: float,
        quality_delta: float,
    ) -> FrictionReading:
        """Fold the four signals into Φ ∈ [0,1] and classify the (observe-only) regime."""
        s = self._saturate(surprise, self._surprise_hist)
        d = min(1.0, max(0.0, float(phase_divergence)))
        g = self._saturate(entropy_production, self._entropy_hist)
        stagnation_raw = 1.0 - min(1.0, abs(float(quality_delta)) * self._stagnation_scale)
        p = stagnation_raw if s >= 0.5 else 0.0  # conjunctive gate: plateau + high surprise

        ws, wd, wg, wp = self._w
        phi = min(1.0, max(0.0, ws * s + wd * d + wg * g + wp * p))
        return FrictionReading(
            phi=phi,
            surprise=s,
            phase_divergence=d,
            entropy_production=g,
            stagnation=p,
            regime=self._classify(phi),
        )

    def _classify(self, phi: float) -> str:
        """Hysteresis regime — enter 'friction' on sustained high Φ, exit on low Φ.

        OBSERVE-ONLY: returns a label; triggers no ENC/ENG.
        """
        if not self._in_friction:
            self._streak = self._streak + 1 if phi > self._enter else 0
            if self._streak >= self._sustain:
                self._in_friction = True
        elif phi < self._exit:
            self._in_friction = False
            self._streak = 0
        return "friction" if self._in_friction else "navigate"
