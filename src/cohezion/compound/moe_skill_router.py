"""Mixture-of-Experts router for SkillRefiner heads (#83).

Routes improvement recommendations through learned per-expert weights.
Experts correspond to the five Autodata perspectives in SkillRefiner.

Parameterisation (changed 2026-09-20): the weights are a categorical distribution over the
five experts, stored as **natural (logit) coordinates** and read through softmax. The
categorical family is both a mixture family (coordinates = the probabilities, constrained to
the simplex) and an exponential family (coordinates = log-odds, unconstrained in R^n). Learning
in the exponential coordinates means an update is a plain additive step along the
e-geodesic -- no clamps, no renormalisation, and ``get_weight`` is a genuine probability.
The previous EMA in probability coordinates was bounded per expert but never summed to one.
"""

from __future__ import annotations

import math
from typing import Any


class MoESkillRouter:
    """Learned weight router over the five SkillRefiner Autodata expert heads.

    Expert names map 1-to-1 with ``SkillRefiner._AUTODATA_PERSPECTIVES`` keys:
    ``quality``, ``efficiency``, ``caching``, ``tier``, ``fallback``.

    Usage::

        router = MoESkillRouter(alpha=0.1)
        best = router.route(skill_name, metrics)   # highest-weight expert
        router.update("quality", quality_delta)    # logit += alpha * clamp(delta)
        router.replay([("tier", 0.8), ("tier", 0.6)])  # batch update
    """

    _EXPERT_NAMES: list[str] = ["quality", "efficiency", "caching", "tier", "fallback"]

    def __init__(self, alpha: float = 0.1) -> None:
        self._alpha = alpha
        # Natural coordinates. All-zero logits == the uniform distribution (MR1).
        self._logits: dict[str, float] = dict.fromkeys(self._EXPERT_NAMES, 0.0)
        # MR5: how many times each expert has been ROUTED to (not updated). Drives the
        # 1/(1+routes) exploration discount in route(); see RV2 for the precedent.
        self._route_counts: dict[str, int] = {}

    @property
    def weights(self) -> dict[str, float]:
        """The expert distribution: softmax of the logits. Sums to 1 by construction."""
        m = max(self._logits.values())
        exp = {k: math.exp(v - m) for k, v in self._logits.items()}
        z = sum(exp.values())
        return {k: v / z for k, v in exp.items()}

    def get_weight(self, expert_name: str) -> float:
        return self.weights.get(expert_name, 0.0)

    def route(self, skill_name: str, metrics: Any) -> str:
        """Return the best expert, discounted by how often it has already been routed to.

        MR5 (hidden-cycle guard, 2026-07-26). Pure ``max(self.weights, ...)`` made this a Cycle
        wearing a Router's clothes: only the routed expert is ever ``update()``d, so only its weight
        moved and every other expert stayed frozen at its initial ``1/n`` forever — the node's output
        determining the distribution of its own future inputs.

        The ``1/(1+routes)`` discount is propagated from ``SkillRefiner._autodata_select``
        (invariant RV2), where it already prevents exactly this lock-in. It is a NUDGE, not a reset:
        a genuinely dominant expert still wins most rounds (see MR5 exploitation test), while an
        untried expert is eventually sampled so its weight can move at all.

        MR3 is preserved: an expert that has never been routed to has ``routes == 0``, so its
        discount is 1.0 and selection falls back to pure weight — which is the case MR3 asserts.
        """
        w = self.weights
        chosen = max(w, key=lambda k: w[k] / (1.0 + self._route_counts.get(k, 0)))
        self._route_counts[chosen] = self._route_counts.get(chosen, 0) + 1
        return chosen

    def update(self, expert_name: str, quality_delta: float) -> None:
        """Additive step in natural coordinates: ``logit += alpha * clamp(delta, -1, 1)``.

        One step along the exponential geodesic. The other experts' probabilities move through
        the shared normaliser; nothing is clamped and nothing is renormalised.
        """
        if expert_name not in self._logits:
            return
        self._logits[expert_name] += self._alpha * max(-1.0, min(1.0, quality_delta))

    def replay(self, history: list[tuple[str, float]]) -> None:
        """Batch update from (expert_name, quality_delta) tuples."""
        for expert_name, quality_delta in history:
            self.update(expert_name, quality_delta)
