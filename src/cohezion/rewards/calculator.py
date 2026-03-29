import logging
import math


logger = logging.getLogger(__name__)


class RewardCalculator:
    """
    Calculates agent rewards based on manifold stability and efficiency.
    """

    def __init__(self, coherence_target: float = 0.5, token_penalty_weight: float = 0.01):
        self.coherence_target = coherence_target
        self.token_penalty_weight = token_penalty_weight

    def calculate_score(self, coherence: float, tokens_used: int) -> float:
        """
        Computes a normalized reward score in [0, 1].

        Score components:
        1. Coherence Stability: Peaks at 0.5 (Gaussian).
        2. Token Efficiency: Logarithmic penalty for high usage.
        """
        # 1. Coherence Reward (Gaussian centered at target)
        sigma = 0.1
        coherence_reward = math.exp(-((coherence - self.coherence_target) ** 2) / (2 * sigma**2))

        # 2. Token Efficiency Penalty
        token_penalty = self.token_penalty_weight * math.log1p(tokens_used)

        # Combine and clamp
        final_score = coherence_reward - token_penalty

        return max(0.0, min(1.0, final_score))
