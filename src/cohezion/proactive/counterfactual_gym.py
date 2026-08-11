r"""Counterfactual Proactive Gym Simulator
========================================
Simulates counterfactual outcomes (Intervene vs. Wait) before executing proactive
agent interventions, evaluating expected reward differentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cohezion.proactive.proactive_reward_model import ProactiveRewardModel, RewardComponents
from cohezion.proactive.sensing import UserEvent


@dataclass(frozen=True, slots=True)
class CounterfactualRollout:
    goal: str
    proactive_score: float
    passive_score: float
    evi: float
    recommendation: str  # "INTERVENE" or "HOLD"


class CounterfactualProactiveGym:
    """Simulator for counterfactual proactive decision outcomes."""

    def __init__(self, reward_model: ProactiveRewardModel | None = None) -> None:
        self.reward_model = reward_model or ProactiveRewardModel()

    def simulate_rollout(
        self,
        predicted_goal: str,
        events: list[UserEvent],
        user_busy: bool = False,
    ) -> CounterfactualRollout:
        """Simulate proactive vs passive branches and compute EVI."""
        proactive_rc = self.reward_model.evaluate_action(predicted_goal, user_busy_state=user_busy)
        passive_rc = RewardComponents(utility=0.15, intrusiveness_penalty=0.0, timing_precision=0.40)

        r_proactive = proactive_rc.total_score()
        r_passive = passive_rc.total_score()
        evi = r_proactive - r_passive

        rec = "INTERVENE" if evi >= self.reward_model.evi_threshold else "HOLD"

        return CounterfactualRollout(
            goal=predicted_goal,
            proactive_score=round(r_proactive, 4),
            passive_score=round(r_passive, 4),
            evi=round(evi, 4),
            recommendation=rec,
        )
