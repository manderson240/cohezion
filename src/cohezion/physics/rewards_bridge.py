"""Rewards Bridge — wires cohezion.rewards into the Genesis Engine physics layer.

Wraps RewardCalculator (Gaussian-at-0.5 HIHO reward) for use in ManifoldEnv,
and adds a lightweight ratchet mechanism to prevent coherence backsliding.

The original RatchetMechanism in cohezion.rewards.ratchet is async and coupled
to ObsidianMCP.  This bridge provides a synchronous, dependency-free ratchet
suitable for real-time RL stepping.
"""

from __future__ import annotations

import logging

from cohezion.rewards.calculator import RewardCalculator


logger = logging.getLogger(__name__)


class CoherenceRatchet:
    """Prevents HIHO coherence from backsliding below a high-water mark.

    Once the agent achieves a coherence level within ``margin`` of the
    HIHO target (0.5), the ratchet locks: any subsequent step that drops
    coherence below ``floor`` incurs a penalty.
    """

    def __init__(self, margin: float = 0.05, penalty: float = 0.2) -> None:
        self.margin = margin
        self.penalty = penalty
        self._best_deviation: float = 1.0  # worst possible

    def reset(self) -> None:
        self._best_deviation = 1.0

    def check(self, coherence: float) -> float:
        """Return a penalty (negative) if coherence regressed, else 0.0."""
        deviation = abs(coherence - 0.5)

        if deviation < self._best_deviation:
            self._best_deviation = deviation
            return 0.0

        # Backslide detected — penalise proportionally
        regression = deviation - self._best_deviation
        if regression > self.margin:
            return -self.penalty * regression

        return 0.0


class RewardsBridge:
    """Unified reward signal for ManifoldEnv using the HIHO Gaussian reward.

    Combines:
    1. ``RewardCalculator.calculate_score`` — Gaussian peaked at coherence=0.5
    2. ``CoherenceRatchet.check`` — penalty for backsliding
    """

    def __init__(
        self,
        coherence_target: float = 0.5,
        token_penalty_weight: float = 0.0,
        ratchet_margin: float = 0.05,
        ratchet_penalty: float = 0.2,
    ) -> None:
        self._calculator = RewardCalculator(
            coherence_target=coherence_target,
            token_penalty_weight=token_penalty_weight,
        )
        self._ratchet = CoherenceRatchet(
            margin=ratchet_margin,
            penalty=ratchet_penalty,
        )

    def reset(self) -> None:
        self._ratchet.reset()

    def compute(self, coherence: float, tokens_used: int = 0) -> float:
        """Compute combined reward: Gaussian score + ratchet penalty."""
        base_reward = self._calculator.calculate_score(coherence, tokens_used)
        ratchet_penalty = self._ratchet.check(coherence)
        return base_reward + ratchet_penalty

    @property
    def calculator(self) -> RewardCalculator:
        return self._calculator

    @property
    def ratchet(self) -> CoherenceRatchet:
        return self._ratchet


__all__ = ["CoherenceRatchet", "RewardsBridge"]
