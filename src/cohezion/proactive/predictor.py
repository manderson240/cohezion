r"""Proactive Goal Predictor
=========================
Predicts implicit user intent and proactive assistance goals based on
activity event history and local model heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from cohezion.proactive.sensing import UserEvent


@dataclass(frozen=True, slots=True)
class GoalPrediction:
    """Predicted proactive goal with confidence score."""

    predicted_goal: str
    confidence: float  # 0.0 to 1.0
    suggested_action: str
    rationale: str
    metadata: dict = field(default_factory=dict)


class ProactiveGoalPredictor:
    """Predicts implicit goals from recent activity event streams."""

    @classmethod
    def predict_goal(cls, events: Sequence[UserEvent]) -> GoalPrediction:
        """Statically/heuristically analyze recent event history to predict goal."""
        if not events:
            return GoalPrediction(
                predicted_goal="idle",
                confidence=0.0,
                suggested_action="none",
                rationale="No activity events observed.",
            )

        event_types = [e.event_type for e in events]

        # Rule 1: High frequency of code edits -> Predict test execution
        if event_types.count("code_edit") >= 2 and "test_pass" not in event_types[-2:]:
            return GoalPrediction(
                predicted_goal="run_verification_tests",
                confidence=0.88,
                suggested_action="pytest_verification",
                rationale="Multiple recent code edits detected without verification test run.",
            )

        # Rule 2: Memory warning -> Predict memory cleanup & OOM guard check
        if "oom_warning" in event_types[-3:]:
            return GoalPrediction(
                predicted_goal="memory_headroom_recovery",
                confidence=0.95,
                suggested_action="oom_guard_settle",
                rationale="Recent memory pressure event detected.",
            )

        # Default fallback prediction
        return GoalPrediction(
            predicted_goal="proactive_code_audit",
            confidence=0.76,
            suggested_action="autoharness_verify",
            rationale="General proactive maintenance trigger.",
        )
