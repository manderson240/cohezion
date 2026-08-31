"""Mixture-of-Experts router for SkillRefiner heads (#83).

Routes improvement recommendations through learned per-expert weights.
Experts correspond to the five Autodata perspectives in SkillRefiner.
Weight updates via EMA; replay() propagates feedback through history.
"""

from __future__ import annotations

from typing import Any


class MoESkillRouter:
    """Learned weight router over the five SkillRefiner Autodata expert heads.

    Expert names map 1-to-1 with ``SkillRefiner._AUTODATA_PERSPECTIVES`` keys:
    ``quality``, ``efficiency``, ``caching``, ``tier``, ``fallback``.

    Usage::

        router = MoESkillRouter(alpha=0.1)
        best = router.route(skill_name, metrics)   # highest-weight expert
        router.update("quality", quality_delta)    # EMA update
        router.replay([("tier", 0.8), ("tier", 0.6)])  # batch update
    """

    _EXPERT_NAMES: list[str] = ["quality", "efficiency", "caching", "tier", "fallback"]

    def __init__(self, alpha: float = 0.1) -> None:
        self._alpha = alpha
        n = len(self._EXPERT_NAMES)
        self.weights: dict[str, float] = dict.fromkeys(self._EXPERT_NAMES, 1.0 / n)
        # MR5: how many times each expert has been ROUTED to (not updated). Drives the
        # 1/(1+routes) exploration discount in route(); see RV2 for the precedent.
        self._route_counts: dict[str, int] = {}

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
        chosen = max(
            self.weights,
            key=lambda k: self.weights[k] / (1.0 + self._route_counts.get(k, 0)),
        )
        self._route_counts[chosen] = self._route_counts.get(chosen, 0) + 1
        return chosen

    def update(self, expert_name: str, quality_delta: float) -> None:
        """EMA update: reward = 0.5 + 0.5 * clamp(delta, -1, 1)."""
        if expert_name not in self.weights:
            return
        reward = max(-1.0, min(1.0, quality_delta))
        self.weights[expert_name] = (1.0 - self._alpha) * self.weights[
            expert_name
        ] + self._alpha * (0.5 + 0.5 * reward)

    def replay(self, history: list[tuple[str, float]]) -> None:
        """Batch update from (expert_name, quality_delta) tuples."""
        for expert_name, quality_delta in history:
            self.update(expert_name, quality_delta)
