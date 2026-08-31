r"""THUNLP Proactive Reward Model & Expected Value of Intervention (EVI) Engine
=============================================================================
Implements THUNLP ProactiveAgent (ICLR 2025) reward modeling:
  R_\psi(s, a) = U(a) - \gamma * P(a) + \tau * T(a)
  EVI(s, a_proactive) = E[R(s, a_proactive)] - E[R(s, a_passive)]

Prevents unwanted user interruptions while ensuring maximum autonomous utility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RewardComponents:
    utility: float  # 0.0 to 1.0 (Value added by proactive action)
    intrusiveness_penalty: float  # 0.0 to 1.0 (Disruption to user)
    timing_precision: float  # 0.0 to 1.0 (Optimal timing)

    def total_score(self, gamma: float = 0.5, tau: float = 0.3) -> float:
        r"""Compute R_\psi(s, a) = U - \gamma * P + \tau * T."""
        return self.utility - (gamma * self.intrusiveness_penalty) + (tau * self.timing_precision)


class ProactiveRewardModel:
    """Reward Model aligning proactive actions with human preference."""

    def __init__(self, gamma: float = 0.5, tau: float = 0.3, evi_threshold: float = 0.25) -> None:
        self.gamma = gamma
        self.tau = tau
        self.evi_threshold = evi_threshold

    def evaluate_action(
        self,
        predicted_goal: str,
        user_busy_state: bool = False,
        historical_acceptance_rate: float = 0.85,
    ) -> RewardComponents:
        """Evaluate utility, intrusiveness penalty, and timing precision for an action."""
        if predicted_goal == "run_verification_tests":
            utility = 0.90
            intrusiveness = 0.10 if not user_busy_state else 0.40
            timing = 0.95
        elif predicted_goal == "memory_headroom_recovery":
            utility = 0.98
            intrusiveness = 0.05  # Critical background safety, low intrusiveness
            timing = 1.00
        else:
            utility = 0.60
            intrusiveness = 0.30 if not user_busy_state else 0.70
            timing = 0.60

        # Adjust timing by historical acceptance rate
        adjusted_timing = timing * historical_acceptance_rate

        return RewardComponents(
            utility=utility,
            intrusiveness_penalty=intrusiveness,
            timing_precision=adjusted_timing,
        )

    def compute_evi(
        self,
        proactive_rewards: RewardComponents,
        passive_rewards: RewardComponents,
    ) -> float:
        """Compute Expected Value of Intervention: EVI = R(proactive) - R(passive)."""
        r_proactive = proactive_rewards.total_score(self.gamma, self.tau)
        r_passive = passive_rewards.total_score(self.gamma, self.tau)
        return r_proactive - r_passive

    def should_intervene(
        self,
        predicted_goal: str,
        user_busy_state: bool = False,
        historical_acceptance_rate: float = 0.85,
    ) -> tuple[bool, float]:
        """Return (True, EVI) if EVI exceeds threshold."""
        proactive_rc = self.evaluate_action(
            predicted_goal, user_busy_state, historical_acceptance_rate
        )
        passive_rc = RewardComponents(
            utility=0.20, intrusiveness_penalty=0.0, timing_precision=0.50
        )

        evi = self.compute_evi(proactive_rc, passive_rc)
        return (evi >= self.evi_threshold, round(evi, 4))
