r"""Proactive Trigger Gate (Threshold Evaluator)
==============================================
Evaluates whether a predicted goal meets the proactive confidence threshold
(default: confidence >= 0.75) before triggering proactive assistance.
"""

from __future__ import annotations

from cohezion.proactive.predictor import GoalPrediction


class ProactiveTriggerGate:
    """Confidence threshold gate for proactive interventions."""

    DEFAULT_THRESHOLD: float = 0.75

    @classmethod
    def should_trigger(
        cls,
        prediction: GoalPrediction,
        min_threshold: float | None = None,
    ) -> bool:
        """Return True if prediction confidence meets or exceeds threshold."""
        threshold = min_threshold if min_threshold is not None else cls.DEFAULT_THRESHOLD
        return prediction.confidence >= threshold
