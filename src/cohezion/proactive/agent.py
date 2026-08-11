r"""THUNLP ProactiveAgent Master Orchestrator (ICLR 2025 Paradigm)
===============================================================
Shifts agents from reactive responses to active assistance:
  1. ActivitySensingGym: Environment event logging
  2. ProactiveGoalPredictor: Implicit goal prediction
  3. ProactiveTriggerGate: Intervention gate (confidence >= 0.75)
  4. AutoHarness & OOMGuard: Zero-cost verified execution
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.proactive.predictor import GoalPrediction, ProactiveGoalPredictor
from cohezion.proactive.sensing import ActivitySensingGym, UserEvent
from cohezion.proactive.trigger_gate import ProactiveTriggerGate
from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProactiveAction:
    action_type: str
    target_goal: str
    code_snippet: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProactiveResult:
    triggered: bool
    confidence: float
    action_type: str
    verified: bool
    bypassed_llm: bool
    execution_time_ms: float
    message: str


class ProactiveAgent:
    """Master Proactive Agent implementing the THUNLP ICLR 2025 paradigm."""

    def __init__(self, confidence_threshold: float = 0.75) -> None:
        self.sensing_gym = ActivitySensingGym()
        self.confidence_threshold = confidence_threshold
        self.policy_engine = AutoHarnessPolicy()

    def record_activity(self, event_type: str, payload: dict[str, Any] | None = None) -> UserEvent:
        """Record user/environment activity to gym."""
        return self.sensing_gym.log_event(event_type, payload or {})

    def evaluate_and_act(self) -> ProactiveResult:
        """Evaluate activity history and trigger proactive assistance if confidence >= threshold."""
        t0 = time.perf_counter()

        # Step 1: Preflight Memory Safety Check
        mem = OOMGuard.get_memory_state()
        if not mem.is_safe:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return ProactiveResult(
                triggered=False,
                confidence=0.0,
                action_type="oom_safety_hold",
                verified=False,
                bypassed_llm=True,
                execution_time_ms=dt_ms,
                message=f"Proactive intervention suppressed: Memory headroom low ({mem.available_gb} GiB)",
            )

        # Step 2: Predict Implicit Goal from Event History
        recent_events = self.sensing_gym.get_recent_events(count=10)
        prediction = ProactiveGoalPredictor.predict_goal(recent_events)

        # Step 3: Check Trigger Gate (confidence >= threshold)
        if not ProactiveTriggerGate.should_trigger(prediction, self.confidence_threshold):
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return ProactiveResult(
                triggered=False,
                confidence=prediction.confidence,
                action_type=prediction.suggested_action,
                verified=False,
                bypassed_llm=True,
                execution_time_ms=dt_ms,
                message=f"Intervention below confidence threshold ({prediction.confidence:.2f} < {self.confidence_threshold})",
            )

        # Step 4: Evaluate Action Policy via AutoHarness (Zero-Cost Execution)
        p_res = self.policy_engine.evaluate_policy(prediction.suggested_action, {"available_gb": mem.available_gb})

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return ProactiveResult(
            triggered=True,
            confidence=prediction.confidence,
            action_type=prediction.suggested_action,
            verified=p_res.allowed,
            bypassed_llm=p_res.bypassed_llm,
            execution_time_ms=dt_ms,
            message=f"Proactive Assistance Triggered: '{prediction.predicted_goal}' ({prediction.rationale})",
        )
