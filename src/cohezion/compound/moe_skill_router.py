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

    def get_weight(self, expert_name: str) -> float:
        return self.weights.get(expert_name, 0.0)

    def route(self, skill_name: str, metrics: Any) -> str:
        """Return the expert name with the highest current weight."""
        return max(self.weights, key=lambda k: self.weights[k])

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
