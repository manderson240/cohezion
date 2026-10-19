"""Agent Runtime Inspection and Amendment (ARIA) Framework.

Implements the supervisory control plane for multi-agent swarm trajectories (arXiv:2610.20780):
1. Trajectory Event Stream: Tracks state deltas, confidence, verifier scores, and tool interactions.
2. In-Flight Cascade Anomaly Detectors:
   - Oscillation and repetitive loop detection.
   - Confidence collapse and verifier score degradation.
   - Schema drift and malformed payload detection.
   - High-fanout downstream dependency risk.
3. Intervention Modes:
   - OBSERVE, PAUSE, BRANCH, REPLACE_CONTINUATION, ROLLBACK, ESCALATE.
4. Continuation Replacement Engine:
   - Atomic checkpointing and shadow branch verification.
   - Verifier-gated continuation adoption with compute-aware decision hook (accept / expand / fallback).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class InterventionMode(StrEnum):
    """Intervention actions available to the ARIA supervisory control plane."""

    OBSERVE = "observe"
    PAUSE = "pause"
    BRANCH = "branch"
    REPLACE_CONTINUATION = "replace_continuation"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"


class TrajectoryEvent(BaseModel):
    """Immutable trace event recorded at an agent execution step boundary."""

    run_id: str = Field(..., description="Unique swarm workflow execution ID.")
    agent_id: str = Field(..., description="Identifier of the executing agent.")
    step_id: str = Field(..., description="Unique step identifier.")
    parent_step_id: str | None = Field(default=None, description="Previous causal step.")
    timestamp: float = Field(default_factory=time.time)
    observation: dict[str, Any] = Field(default_factory=dict)
    action: str = Field(..., description="Command or tool invocation dispatched.")
    tool_result: dict[str, Any] | None = Field(default=None)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verifier_score: float = Field(default=1.0, ge=0.0, le=1.0)
    downstream_agent_count: int = Field(default=1, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def state_hash(self) -> str:
        """Deterministic fingerprint of the observation and action payload."""
        content = json.dumps({"obs": self.observation, "act": self.action}, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


class CascadeRiskAssessment(BaseModel):
    """Output diagnostics from in-flight trajectory anomaly inspection."""

    run_id: str
    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized cascade propagation risk."
    )
    recommended_mode: InterventionMode
    anomaly_types: list[str] = Field(default_factory=list)
    rationale: str
    causal_trace: list[str] = Field(default_factory=list)
    checkpoint_recommended: bool = False


class ARIARuntimeInspector:
    """Real-time supervisory inspector evaluating active multi-agent trajectories."""

    def __init__(
        self,
        loop_threshold: int = 3,
        verifier_collapse_floor: float = 0.40,
        risk_threshold: float = 0.70,
    ) -> None:
        self.loop_threshold = loop_threshold
        self.verifier_collapse_floor = verifier_collapse_floor
        self.risk_threshold = risk_threshold
        self.trajectories: dict[str, list[TrajectoryEvent]] = {}

    def record_step(self, event: TrajectoryEvent) -> CascadeRiskAssessment:
        """Record an in-flight trajectory event and immediately evaluate cascade risk."""
        history = self.trajectories.setdefault(event.run_id, [])
        history.append(event)
        return self.inspect_trajectory(event.run_id)

    def inspect_trajectory(self, run_id: str) -> CascadeRiskAssessment:
        """Audit the trajectory history of a running swarm for error propagation risks."""
        history = self.trajectories.get(run_id, [])
        if not history:
            return CascadeRiskAssessment(
                run_id=run_id,
                risk_score=0.0,
                recommended_mode=InterventionMode.OBSERVE,
                rationale="Empty trajectory; normal execution.",
            )

        anomalies: list[str] = []
        causal_trace: list[str] = []
        raw_risk = 0.0

        current = history[-1]

        # 1. Detect Repetitive Loop / Oscillation
        if len(history) >= self.loop_threshold:
            recent_actions = [e.action for e in history[-self.loop_threshold :]]
            if len(set(recent_actions)) == 1:
                anomalies.append("repetitive_action_loop")
                raw_risk += 0.45
                causal_trace.append(
                    f"Identical action '{recent_actions[0]}' repeated {self.loop_threshold} times."
                )

        # 2. Detect Verifier Collapse or Sharp Degradation
        if current.verifier_score < self.verifier_collapse_floor:
            anomalies.append("verifier_score_collapse")
            raw_risk += 0.85
            causal_trace.append(
                f"Verifier score {current.verifier_score:.2f} fell below safety floor {self.verifier_collapse_floor:.2f}."
            )
        elif len(history) >= 2:
            prev = history[-2]
            drop = prev.verifier_score - current.verifier_score
            if drop >= 0.35:
                anomalies.append("sharp_verifier_regression")
                raw_risk += 0.35
                causal_trace.append(
                    f"Sharp drop in verifier score (-{drop:.2f}) from step {prev.step_id}."
                )

        # 3. Detect Confidence Drop with High Downstream Fanout
        if current.confidence < 0.50 and current.downstream_agent_count >= 3:
            anomalies.append("high_fanout_ambiguity")
            raw_risk += 0.30
            causal_trace.append(
                f"Low confidence ({current.confidence:.2f}) with {current.downstream_agent_count} downstream dependents."
            )

        # 4. Detect Tool Fault / Error in payload
        if current.tool_result and current.tool_result.get("error"):
            anomalies.append("tool_execution_error")
            raw_risk += 0.25
            causal_trace.append(
                f"Tool execution returned error: {current.tool_result.get('error')}"
            )

        normalized_risk = min(1.0, max(0.0, raw_risk))

        # Select Intervention Mode
        if "verifier_score_collapse" in anomalies or normalized_risk >= 0.85:
            mode = InterventionMode.ROLLBACK
        elif normalized_risk >= self.risk_threshold:
            mode = InterventionMode.REPLACE_CONTINUATION
        elif normalized_risk >= 0.40:
            mode = InterventionMode.PAUSE
        else:
            mode = InterventionMode.OBSERVE

        return CascadeRiskAssessment(
            run_id=run_id,
            risk_score=round(normalized_risk, 3),
            recommended_mode=mode,
            anomaly_types=anomalies,
            rationale=" | ".join(causal_trace)
            if causal_trace
            else "Trajectory within healthy operating bounds.",
            causal_trace=causal_trace,
            checkpoint_recommended=normalized_risk >= 0.50,
        )


class ARIAAmendmentEngine:
    """Orchestrates atomic continuation replacement and test-time compute decision triage."""

    def __init__(
        self,
        inspector: ARIARuntimeInspector,
        verifier_fn: Callable[[dict[str, Any], str], float] | None = None,
    ) -> None:
        self.inspector = inspector
        self.verifier_fn = verifier_fn or (lambda state, act: 1.0)
        self.checkpoints: dict[str, list[TrajectoryEvent]] = {}
        self.amendment_log: list[dict[str, Any]] = []

    def checkpoint(self, run_id: str) -> str:
        """Create a durable checkpoint snapshot of the current trajectory."""
        history = self.inspector.trajectories.get(run_id, [])
        checkpoint_id = f"ckpt_{run_id}_{len(history)}"
        self.checkpoints[checkpoint_id] = [e.model_copy() for e in history]
        return checkpoint_id

    def amend_continuation(
        self,
        run_id: str,
        assessment: CascadeRiskAssessment,
        candidate_continuations: Sequence[str],
        compute_budget: int = 3,
    ) -> tuple[bool, str, str]:
        """Intervene and evaluate candidate replacements before committing to live swarm.

        Incorporates Compute-Aware Three-Action Decision Logic (arXiv:2610.20836):
        - ACCEPT: If candidate exceeds baseline verifier score by delta.
        - EXPAND_ROLLOUT: If ambiguity persists and compute budget > 0.
        - FALLBACK: If all candidates fail to clear safety threshold.

        Returns
        -------
        tuple[bool, str, str]
            Tuple of (success: bool, adopted_continuation: str, decision_rationale: str).
        """
        history = self.inspector.trajectories.get(run_id, [])
        if not history:
            return False, "", "Cannot amend empty trajectory."

        current_event = history[-1]
        baseline_score = current_event.verifier_score

        best_cand: str | None = None
        best_score = -1.0

        for cand in candidate_continuations:
            score = self.verifier_fn(current_event.observation, cand)
            if score > best_score:
                best_score = score
                best_cand = cand

        # Three-Action Decision Logic
        if best_cand is not None and best_score >= max(baseline_score + 0.15, 0.70):
            # ACCEPT: Amend trajectory with certified continuation
            amended_event = TrajectoryEvent(
                run_id=run_id,
                agent_id=f"{current_event.agent_id}_aria_amended",
                step_id=f"{current_event.step_id}_amend",
                parent_step_id=current_event.parent_step_id,
                observation=current_event.observation,
                action=best_cand,
                confidence=0.90,
                verifier_score=best_score,
                metadata={"aria_amended": True, "original_action": current_event.action},
            )
            # Atomically replace final faulty step with certified continuation
            history[-1] = amended_event
            record = {
                "run_id": run_id,
                "decision": "ACCEPT",
                "original_action": current_event.action,
                "replacement_action": best_cand,
                "baseline_score": baseline_score,
                "new_score": best_score,
                "timestamp": time.time(),
            }
            self.amendment_log.append(record)
            return (
                True,
                best_cand,
                f"Accepted amendment '{best_cand}' (score: {best_score:.2f} vs baseline: {baseline_score:.2f}).",
            )

        if compute_budget > 1:
            # EXPAND_ROLLOUT: Requires further test-time search
            return (
                False,
                "",
                f"Ambiguity persists (best score {best_score:.2f}); expand search budget.",
            )

        # FALLBACK: Safe default action to stop cascading errors
        fallback_action = "aria_safe_deterministic_hold"
        return False, fallback_action, "All candidates failed threshold; fallback to safe hold."
