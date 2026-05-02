"""Routing feedback loop — track and optimize model routing decisions."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class RoutingDecisionType(Enum):
    """Types of routing decisions made."""

    MODEL_SELECTION = "model_selection"


@dataclass
class RoutingDecision:
    """Record of a single routing decision."""

    decision_type: RoutingDecisionType
    selected_model: str
    task_type: str
    context_length: int
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    execution_time_ms: float = 0.0
    tokens_generated: int = 0


@dataclass
class RoutingMetrics:
    """Aggregated routing metrics."""

    total_decisions: int = 0
    successful_decisions: int = 0
    decision_types: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_decisions == 0:
            return 0.0
        return self.successful_decisions / self.total_decisions


class RoutingOptimizationFeedback:
    """Tracks routing optimization patterns."""

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._decisions: list[RoutingDecision] = []
        self._metrics = RoutingMetrics()

    def record_decision(self, decision: RoutingDecision) -> None:
        """Record a routing decision."""
        self._decisions.append(decision)
        if len(self._decisions) > self._window_size:
            self._decisions.pop(0)
        self._metrics.total_decisions += 1
        if decision.success:
            self._metrics.successful_decisions += 1

    def detect_anomalies(self) -> list[dict[str, Any]]:
        """Detect anomalies in routing decisions."""
        anomalies = []
        if len(self._decisions) < 2:
            return anomalies
        recent = self._decisions[-self._window_size :]
        model_switches = 0
        for i in range(1, len(recent)):
            if recent[i].selected_model != recent[i - 1].selected_model:
                model_switches += 1
        if len(recent) > 0 and model_switches / len(recent) > 0.5:
            anomalies.append(
                {
                    "type": "model_thrashing",
                    "severity": "warning",
                }
            )
        return anomalies

    def get_routing_recommendations(self) -> dict[str, Any]:
        """Generate recommendations for routing optimization."""
        return {
            "model_preference": {},
            "warnings": [],
        }

    def get_metrics(self) -> RoutingMetrics:
        """Get current routing metrics."""
        return self._metrics

    def reset(self) -> None:
        """Reset all tracking data."""
        self._decisions.clear()
        self._metrics = RoutingMetrics()


_routing_feedback: RoutingOptimizationFeedback | None = None


def get_routing_feedback() -> RoutingOptimizationFeedback:
    """Get or create the singleton routing feedback tracker."""
    global _routing_feedback
    if _routing_feedback is None:
        _routing_feedback = RoutingOptimizationFeedback()
    return _routing_feedback
