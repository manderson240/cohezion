r"""Ambient AI Agent Engine
========================
Runs background-sensing Ambient AI Agents that operate continuously without explicit
user prompts, sensing system events, predicting user goals, and executing EVI-backed
interventions when thresholds are met.

Formulation:
  - Sensing Loop: Event stream -> Goal Predictor -> Counterfactual Gym
  - EVI Decision: EVI = R(Intervene) - R(Passive) >= 0.75
  - Ambient Dispatch: AutoHarness Zero-Cost Action Verification
"""

from __future__ import annotations

from dataclasses import dataclass

from cohezion.proactive.counterfactual_gym import CounterfactualProactiveGym
from cohezion.proactive.predictor import ProactiveGoalPredictor
from cohezion.proactive.sensing import ActivitySensingGym, UserEvent


@dataclass(frozen=True, slots=True)
class AmbientCycleResult:
    agent_id: str
    sensed_events_count: int
    predicted_goal: str
    evi_score: float
    action_taken: str
    bypassed_llm: bool


class AmbientAgent:
    """Continuous Ambient AI Agent running background sensing & EVI intervention."""

    def __init__(self, agent_id: str = "ambient_agent_alpha") -> None:
        self.agent_id = agent_id
        self.sensing_gym = ActivitySensingGym()
        self.counterfactual_gym = CounterfactualProactiveGym()

    def perceive_and_act(self, new_events: list[UserEvent]) -> AmbientCycleResult:
        """Run an ambient perception-intervention cycle."""
        for evt in new_events:
            self.sensing_gym.log_event(evt.event_type, evt.payload)

        recent = self.sensing_gym.get_recent_events(count=10)
        prediction = ProactiveGoalPredictor.predict_goal(recent)

        rollout = self.counterfactual_gym.simulate_rollout(prediction.predicted_goal, recent)

        action_taken = "NO_ACTION"
        if rollout.recommendation == "INTERVENE":
            action_taken = f"EXECUTE_{prediction.suggested_action.upper()}"

        return AmbientCycleResult(
            agent_id=self.agent_id,
            sensed_events_count=len(recent),
            predicted_goal=prediction.predicted_goal,
            evi_score=rollout.evi,
            action_taken=action_taken,
            bypassed_llm=True,
        )
