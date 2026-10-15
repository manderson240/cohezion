"""Structured Inter-Agent Handoff Contracts & Trajectory Gating (2026 Roadmap).
=============================================================================
Abstracted from KDnuggets 'Roadmap to Mastering Agentic AI Systems in 2026':
1. Level 1: Structured Tool & Action Schema Validation (Pydantic / TypeChat).
2. Level 2: Tri-Partite Memory Contracts (Working Context vs Episodic vs Semantic).
3. Level 3: Typed Swarm Handoff Contracts & Explicit Conflict Resolution Protocols.
4. Level 4: Trajectory-Level Tracing, Circuit Breaker Ceilings & Runaway Loop Caps.
"""

from __future__ import annotations

import enum
import hashlib
import time
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field


class AgentRole(str, enum.Enum):
    """Specialized Swarm Agent Topologies."""

    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    PROPOSER = "proposer"
    CRITIC = "critic"
    VERIFIER = "verifier"
    SYNTHESIZER = "synthesizer"


class ConflictResolutionStrategy(str, enum.Enum):
    """Deterministic Conflict Resolution Mechanisms for Multi-Agent Swarms."""

    DEBATE_AND_CRITIQUE = "debate_and_critique"
    WEIGHTED_VOTING = "weighted_voting"
    ADVERSARIAL_REQUERY = "adversarial_requery"
    ESCALATE_TO_ORCHESTRATOR = "escalate_to_orchestrator"


class TaskStatus(str, enum.Enum):
    """Lifecycle states of a swarm task."""

    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    CRITIQUED = "critiqued"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CIRCUIT_BROKEN = "circuit_broken"
    COMPLETED = "completed"


class StepTraceRecord(BaseModel):
    """Granular execution graph record for trajectory-level evaluation."""

    step_index: int
    agent_id: str
    role: AgentRole
    action_type: str
    tokens_consumed: int = Field(ge=0)
    duration_ms: float = Field(ge=0.0)
    state_digest: str
    passed_validation: bool
    diagnostics: str = ""
    timestamp: float = Field(default_factory=time.time)


class TaskHandoffContract(BaseModel):
    """Explicit, typed inter-agent handoff schema eliminating unstructured text drift."""

    contract_id: str
    parent_task_id: str
    source_agent: str
    source_role: AgentRole
    target_agent: str
    target_role: AgentRole
    task_intent: str
    input_payload: dict[str, Any]
    acceptance_criteria: list[str]
    recursion_depth: int = Field(default=0, ge=0)
    max_recursion_depth: int = Field(default=8, ge=1)
    accumulated_tokens: int = Field(default=0, ge=0)
    max_token_ceiling: int = Field(default=32768, ge=512)
    trajectory: list[StepTraceRecord] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.INITIALIZED

    def can_proceed(self) -> tuple[bool, str]:
        """Circuit breaker evaluating recursion depth and token expenditure ceilings."""
        if self.recursion_depth >= self.max_recursion_depth:
            return False, f"Circuit Breaker: Recursion depth limit reached ({self.recursion_depth}/{self.max_recursion_depth})"
        if self.accumulated_tokens >= self.max_token_ceiling:
            return False, f"Circuit Breaker: Token ceiling exceeded ({self.accumulated_tokens}/{self.max_token_ceiling})"
        return True, "Nominal"

    def record_step(
        self,
        agent_id: str,
        role: AgentRole,
        action_type: str,
        tokens: int,
        duration_ms: float,
        passed_validation: bool,
        diagnostics: str = "",
    ) -> None:
        """Appends a validated trajectory step and updates counters."""
        state_repr = f"{agent_id}:{action_type}:{tokens}:{passed_validation}"
        digest = hashlib.sha256(state_repr.encode("utf-8")).hexdigest()[:12]
        
        record = StepTraceRecord(
            step_index=len(self.trajectory) + 1,
            agent_id=agent_id,
            role=role,
            action_type=action_type,
            tokens_consumed=tokens,
            duration_ms=duration_ms,
            state_digest=digest,
            passed_validation=passed_validation,
            diagnostics=diagnostics,
        )
        self.trajectory.append(record)
        self.accumulated_tokens += tokens
        self.recursion_depth += 1


class CriticEvaluationResult(BaseModel):
    """Structured critique output from a critic agent in a debate-and-critique pair."""

    contract_id: str
    critic_agent: str
    approved: bool
    critique_score: float = Field(ge=0.0, le=1.0)
    identified_defects: list[str] = Field(default_factory=list)
    suggested_modifications: list[str] = Field(default_factory=list)
    recommended_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.DEBATE_AND_CRITIQUE


class SwarmConflictResolver:
    """Deterministic conflict resolution engine across specialized agents."""

    @staticmethod
    def resolve_critique(
        contract: TaskHandoffContract,
        critique: CriticEvaluationResult,
    ) -> TaskStatus:
        """Determines next lifecycle action based on critic evaluation and circuit limits."""
        can_proceed, reason = contract.can_proceed()
        if not can_proceed:
            contract.status = TaskStatus.CIRCUIT_BROKEN
            return TaskStatus.CIRCUIT_BROKEN

        if critique.approved and critique.critique_score >= 0.85:
            contract.status = TaskStatus.VERIFIED
            return TaskStatus.VERIFIED

        if critique.recommended_strategy == ConflictResolutionStrategy.DEBATE_AND_CRITIQUE:
            contract.status = TaskStatus.CRITIQUED
            return TaskStatus.CRITIQUED

        if critique.recommended_strategy == ConflictResolutionStrategy.ESCALATE_TO_ORCHESTRATOR:
            contract.status = TaskStatus.REJECTED
            return TaskStatus.REJECTED

        return TaskStatus.IN_PROGRESS
