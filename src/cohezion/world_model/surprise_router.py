"""Active-Inference action loop: turn JEPA surprise into explore/exploit + tier decisions.

This closes the seam that has existed since journey tracking was wired to the world model:
`JEPAWorldModel.surprise_score()` produces a prediction-error signal, `JourneyTracker`
enriches each journey point with ``metadata["jepa_surprise"]`` — but **nothing reads it to
act**. ``SurpriseExplorer`` consumes surprise only offline (scans the 12D manifold for
high-surprise regions to probe later); it does not steer the live action loop.

``SurpriseRouter`` is that missing reader. It implements the active-inference control rule:

    expected free energy  =  pragmatic value (reach goal -> EXPLOIT)
                           +  epistemic value (reduce uncertainty -> EXPLORE)

Surprise (prediction error) is the dial between the two. High surprise means the world model
is uncertain about the current transition, so epistemic value dominates: explore, and escalate
to a more capable tier to resolve the uncertainty. Low surprise means the model is confident:
exploit the cheapest tier.

Two robustness choices:

1. **Adaptive normalization.** ``surprise_score`` returns an MSE in embedding space — unbounded
   and dependent on embedding dimensionality, so no fixed threshold transfers across models.
   We normalize each observation against an EWMA running scale of recent surprise magnitudes,
   yielding a stable [0, 1] signal regardless of absolute MSE scale.

2. **Hysteresis.** A single threshold makes the mode flap when surprise hovers near it (and
   flapping the routing tier is expensive). We switch to EXPLORE only above
   ``threshold + hysteresis`` and back to EXPLOIT only below ``threshold - hysteresis``; in the
   dead-band we hold the previous mode. This is the grounded form of a "dynamic observer window".

The emitted ``tier`` vocabulary -- ``"npu" | "igpu" | "cpu"`` -- matches the fleet routing names
in ``local-inference-default`` (NPU 13306 -> iGPU 13307 -> CPU 13309), so the decision composes
directly with the existing CostAwareRouter / DegradationDetector tier feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


__all__ = ["ActionMode", "SurpriseDecision", "SurpriseRouter"]


class ActionMode(StrEnum):
    """Active-inference action mode selected from current surprise."""

    EXPLOIT = "exploit"  # low surprise: world model confident -> cheapest adequate tier
    EXPLORE = "explore"  # high surprise: gather information -> escalate tier


# Fleet routing tiers, cheapest -> most capable. Index = capability rank.
_TIERS = ("npu", "igpu", "cpu")


@dataclass(frozen=True)
class SurpriseDecision:
    """A single explore/exploit + tier decision derived from one surprise observation."""

    mode: ActionMode
    tier: str  # one of _TIERS
    surprise: float  # raw MSE prediction error as observed
    normalized: float  # surprise mapped to [0, 1] via the EWMA running scale
    rationale: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "tier": self.tier,
            "surprise": self.surprise,
            "normalized": self.normalized,
            "rationale": self.rationale,
        }


class SurpriseRouter:
    """Map JEPA surprise -> (explore/exploit, fleet tier) with adaptive scale + hysteresis.

    Parameters
    ----------
    explore_threshold:
        Normalized-surprise midpoint of the explore/exploit boundary (default 0.6 -- biased
        toward exploit so we escalate only when the model is genuinely surprised).
    hysteresis:
        Half-width of the dead-band around ``explore_threshold`` where the previous mode is
        held (default 0.1). Set 0 to disable.
    ewma_alpha:
        Smoothing factor for the running surprise scale (default 0.3). Higher = the scale
        adapts faster to recent magnitudes.
    """

    def __init__(
        self,
        explore_threshold: float = 0.6,
        hysteresis: float = 0.1,
        ewma_alpha: float = 0.3,
    ) -> None:
        if not 0.0 <= explore_threshold <= 1.0:
            raise ValueError("explore_threshold must be in [0, 1]")
        if not 0.0 <= hysteresis < 0.5:
            raise ValueError("hysteresis must be in [0, 0.5)")
        if not 0.0 < ewma_alpha <= 1.0:
            raise ValueError("ewma_alpha must be in (0, 1]")
        self.explore_threshold = explore_threshold
        self.hysteresis = hysteresis
        self.ewma_alpha = ewma_alpha
        self._scale: float | None = None  # EWMA of observed surprise magnitude
        self._last_mode: ActionMode = ActionMode.EXPLOIT  # cold start: assume confident

    # -- core ----------------------------------------------------------------

    def _update_scale(self, surprise: float) -> float:
        """Update and return the EWMA running scale of surprise magnitude."""
        mag = abs(surprise)
        if self._scale is None:
            self._scale = mag
        else:
            self._scale = self.ewma_alpha * mag + (1.0 - self.ewma_alpha) * self._scale
        return self._scale

    def _normalize(self, surprise: float, scale: float) -> float:
        """Map raw surprise to [0, 1] against the running scale.

        Normalizing against the EWMA mean places "typical" surprise near 0.5 and lets spikes
        push toward 1.0, independent of the absolute MSE scale. The 2x denominator centers the
        steady state (surprise == scale) at 0.5.
        """
        if scale <= 0.0:
            return 0.0
        return max(0.0, min(1.0, abs(surprise) / (2.0 * scale)))

    def _select_mode(self, normalized: float) -> ActionMode:
        """Apply hysteresis around the explore threshold; hold previous mode in the dead-band."""
        hi = self.explore_threshold + self.hysteresis
        lo = self.explore_threshold - self.hysteresis
        if normalized >= hi:
            return ActionMode.EXPLORE
        if normalized <= lo:
            return ActionMode.EXPLOIT
        return self._last_mode  # dead-band: no switch

    def _select_tier(self, normalized: float) -> str:
        """Three capability bands by normalized surprise: low->npu, mid->igpu, high->cpu."""
        if normalized < 1.0 / 3.0:
            return _TIERS[0]  # npu
        if normalized < 2.0 / 3.0:
            return _TIERS[1]  # igpu
        return _TIERS[2]  # cpu

    def observe(self, surprise: float) -> SurpriseDecision:
        """Ingest one surprise value and emit the explore/exploit + tier decision.

        Stateful: updates the EWMA scale and the last-mode used for hysteresis.
        """
        scale = self._update_scale(surprise)
        normalized = self._normalize(surprise, scale)
        mode = self._select_mode(normalized)
        tier = self._select_tier(normalized)
        self._last_mode = mode
        rationale = (
            f"surprise={surprise:.4f} scale={scale:.4f} norm={normalized:.2f} "
            f"-> {mode.value} (epistemic value {'high' if mode is ActionMode.EXPLORE else 'low'}) "
            f"-> tier={tier}"
        )
        return SurpriseDecision(
            mode=mode,
            tier=tier,
            surprise=float(surprise),
            normalized=normalized,
            rationale=rationale,
        )

    def decide_from_point(self, point: object) -> SurpriseDecision | None:
        """Read ``jepa_surprise`` from a JourneyTracker point's metadata and decide.

        Returns ``None`` when the point carries no surprise enrichment (the world model was
        untrained or the enrichment failed) -- a no-op, never a fabricated decision. This is
        the live consumer of the data ``JourneyTracker`` already writes.
        """
        meta = getattr(point, "metadata", None)
        if not isinstance(meta, dict):
            return None
        surprise = meta.get("jepa_surprise")
        if surprise is None:
            return None
        return self.observe(float(surprise))

    @property
    def scale(self) -> float | None:
        """Current EWMA surprise scale (None before the first observation)."""
        return self._scale
