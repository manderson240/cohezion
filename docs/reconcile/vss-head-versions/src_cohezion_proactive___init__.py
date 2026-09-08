"""Cohezion Native ProactiveAgent Package (THUNLP ICLR 2025 Paradigm)

Shifts agents from purely reactive responses to active, autonomous assistance
by sensing activity events, anticipating implicit user goals, evaluating trigger
confidence gates (>= 0.75), and executing zero-cost AutoHarness verified actions.
"""

from cohezion.proactive.agent import ProactiveAgent, ProactiveAction, ProactiveResult
from cohezion.proactive.sensing import ActivitySensingGym, UserEvent
from cohezion.proactive.predictor import ProactiveGoalPredictor, GoalPrediction
from cohezion.proactive.trigger_gate import ProactiveTriggerGate
from cohezion.proactive.proactive_reward_model import ProactiveRewardModel, RewardComponents
from cohezion.proactive.counterfactual_gym import CounterfactualProactiveGym, CounterfactualRollout

__all__ = [
    "ProactiveAgent",
    "ProactiveAction",
    "ProactiveResult",
    "ActivitySensingGym",
    "UserEvent",
    "ProactiveGoalPredictor",
    "GoalPrediction",
    "ProactiveTriggerGate",
    "ProactiveRewardModel",
    "RewardComponents",
    "CounterfactualProactiveGym",
    "CounterfactualRollout",
]
