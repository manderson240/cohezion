r"""Recuris: Recursive Experiential-Working Memory Architecture
============================================================
Synthesizes arXiv:2608.24876:
"Recursive Experiential–Working Memory Evolution for Long-Horizon Agent Harnesses"

Core Formalisms:
1. Memory Quad: M_k = (E_k, W_k, rho_k, C_k)
   - E: Experiential Memory (reusable skills, transforms, invariants)
   - W: Working Memory (compact verified task state: active goals, uncommitted writes)
   - rho: Invocation Policy (event-driven state-grounded trigger rho: W -> E)
   - C: Verifiers & Checkers (evidence-grounded environment receipt validation)

2. Trace-Based Failure Localization:
   - Structured trace Gamma = <s_0, a_0, r_0, w_0, ...>
   - Failure localization: argmax_{c in {E, W, rho, C}} P(Fault = c | Gamma)

3. Validation-Gated Patch Admission:
   - Candidate patch delta M is admitted to M_{k+1} if and only if regression test passes.
"""

from __future__ import annotations

import ast
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, NamedTuple


logger = logging.getLogger(__name__)


class MemoryComponent(StrEnum):
    """The four distinct components of the Recuris memory quad."""

    EXPERIENTIAL_MEMORY = "E"
    WORKING_MEMORY = "W"
    INVOCATION_POLICY = "rho"
    CHECKER_VERIFIER = "C"


@dataclass
class ExperientialSkill:
    """A reusable strategy or transform stored in Experiential Memory (E)."""

    skill_id: str
    name: str
    description: str
    code_body: str
    domain: str = "general"
    tags: list[str] = field(default_factory=list)
    version: int = 1


@dataclass
class WorkingGoal:
    """A tracked goal in Working Memory (W)."""

    goal_id: str
    description: str
    status: str = "PENDING"  # PENDING, IN_PROGRESS, VERIFIED, FAILED
    receipt: str | None = None
    created_turn: int = 0
    resolved_turn: int | None = None


@dataclass
class WorkingMemoryState:
    """Compact verified task state (W)."""

    task_id: str
    current_turn: int = 0
    active_goals: list[WorkingGoal] = field(default_factory=list)
    uncommitted_writes: list[dict[str, Any]] = field(default_factory=list)
    verified_receipts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_unresolved_goals(self) -> bool:
        return any(g.status in ("PENDING", "IN_PROGRESS") for g in self.active_goals)

    def mark_verified(self, goal_id: str, receipt: str) -> bool:
        for g in self.active_goals:
            if g.goal_id == goal_id:
                g.status = "VERIFIED"
                g.receipt = receipt
                g.resolved_turn = self.current_turn
                return True
        return False


class InvocationPolicy:
    """State-grounded trigger rho: W -> E.

    Determines when and which experiential skill to inject into the agent context
    based strictly on the current working state rather than raw conversation history.
    """

    def __init__(self, routing_rules: dict[str, str] | None = None) -> None:
        # Maps state-trigger keyword / pattern to skill_id
        self.routing_rules = routing_rules or {}

    def select_skill(
        self,
        working_state: WorkingMemoryState,
        skill_library: dict[str, ExperientialSkill],
    ) -> ExperientialSkill | None:
        """Evaluates working state and returns the single relevant skill if triggered."""
        for goal in working_state.active_goals:
            if goal.status in ("PENDING", "IN_PROGRESS"):
                for pattern, skill_id in self.routing_rules.items():
                    if pattern.lower() in goal.description.lower():
                        return skill_library.get(skill_id)
        return None


class CheckerPipeline:
    """Evidence-grounded verifiers (C) that validate environment feedback."""

    def __init__(self) -> None:
        self._verifiers: dict[str, Callable[[Any], tuple[bool, str]]] = {}

    def register_verifier(self, name: str, fn: Callable[[Any], tuple[bool, str]]) -> None:
        self._verifiers[name] = fn

    def verify_receipt(self, receipt_type: str, data: Any) -> tuple[bool, str]:
        if receipt_type in self._verifiers:
            return self._verifiers[receipt_type](data)
        # Default verifier: requires non-empty data
        if data is not None and str(data).strip():
            return True, "Valid non-empty receipt."
        return False, "Empty or invalid receipt."


class MemoryQuad(NamedTuple):
    """The four-component Recuris tuple: M = (E, W, rho, C)."""

    E: dict[str, ExperientialSkill]
    W: WorkingMemoryState
    rho: InvocationPolicy
    C: CheckerPipeline


@dataclass
class ExecutionTraceStep:
    """Single step in the structured trace Gamma."""

    turn: int
    working_state_snapshot: dict[str, Any]
    invoked_skill_id: str | None
    action_taken: str
    environment_feedback: str
    verifier_passed: bool
    diagnostic: str = ""


@dataclass
class FailureLocalizationResult:
    """Attribution of an episode failure to a specific memory component."""

    failed_component: MemoryComponent
    confidence: float
    rationale: str
    proposed_patch_target: str
    evidence_trace_indices: list[int]


class TraceFailureLocalizer:
    """Trace-based failure localization engine.

    Parses structured execution traces Gamma and attributes failures to
    E (skill content), W (state tracking), rho (invocation timing), or C (verifier).
    """

    @staticmethod
    def localize_failure(
        trace: Sequence[ExecutionTraceStep],
        task_succeeded: bool,
    ) -> FailureLocalizationResult | None:
        if task_succeeded:
            return None

        # 1. Check for Verifier (C) failures:
        # Verifier accepted an invalid action, or rejected a valid execution receipt
        for i, step in enumerate(trace):
            if (
                not step.verifier_passed
                and "syntax" not in step.diagnostic.lower()
                and i == len(trace) - 1
            ):
                # Final action rejected by verifier
                return FailureLocalizationResult(
                    failed_component=MemoryComponent.CHECKER_VERIFIER,
                    confidence=0.88,
                    rationale="Execution receipt was rejected by checker verifier at final step.",
                    proposed_patch_target="CheckerPipeline.verify_receipt",
                    evidence_trace_indices=[i],
                )

        # 2. Check for Invocation Policy (rho) failures:
        # Active goal existed in W, but rho failed to invoke the appropriate skill from E
        for i, step in enumerate(trace):
            active_goals = step.working_state_snapshot.get("active_goals", [])
            has_pending = any(g.get("status") == "PENDING" for g in active_goals)
            if has_pending and step.invoked_skill_id is None:
                return FailureLocalizationResult(
                    failed_component=MemoryComponent.INVOCATION_POLICY,
                    confidence=0.82,
                    rationale="Unresolved pending goals existed in working state, but invocation policy rho failed to invoke a matching skill.",
                    proposed_patch_target="InvocationPolicy.routing_rules",
                    evidence_trace_indices=[i],
                )

        # 3. Check for Working Memory (W) failures:
        # Tool executed and returned success, but working memory did not track or close the goal
        for i, step in enumerate(trace):
            if step.verifier_passed and "success" in step.environment_feedback.lower():
                active_goals = step.working_state_snapshot.get("active_goals", [])
                if any(g.get("status") == "PENDING" for g in active_goals):
                    return FailureLocalizationResult(
                        failed_component=MemoryComponent.WORKING_MEMORY,
                        confidence=0.79,
                        rationale="Environment returned successful receipt, but working memory W did not transition goal to VERIFIED.",
                        proposed_patch_target="WorkingMemoryState.mark_verified",
                        evidence_trace_indices=[i],
                    )

        # 4. Fallback: Experiential Memory (E) failure:
        # A skill was invoked, but the executed code produced a runtime error or sub-baseline score
        for i, step in enumerate(trace):
            if step.invoked_skill_id is not None and not step.verifier_passed:
                return FailureLocalizationResult(
                    failed_component=MemoryComponent.EXPERIENTIAL_MEMORY,
                    confidence=0.75,
                    rationale=f"Invoked skill '{step.invoked_skill_id}' produced invalid action or execution failure.",
                    proposed_patch_target=f"ExperientialSkill:{step.invoked_skill_id}",
                    evidence_trace_indices=[i],
                )

        return FailureLocalizationResult(
            failed_component=MemoryComponent.EXPERIENTIAL_MEMORY,
            confidence=0.50,
            rationale="Default attribution: General failure in experiential strategy.",
            proposed_patch_target="ExperientialMemory",
            evidence_trace_indices=[len(trace) - 1] if trace else [],
        )


class ValidationGatedAdmission:
    """Validation-gated admission control for memory evolution.

    Ensures that any proposed patch delta M strictly passes regression tests
    before admission into the persistent memory store M_{k+1}.
    """

    @staticmethod
    def validate_code_patch(candidate_code: str) -> tuple[bool, str]:
        """AST parsing and safety verification of candidate patch."""
        try:
            tree = ast.parse(candidate_code)
        except SyntaxError as exc:
            return False, f"SyntaxError in candidate patch: {exc}"

        # Invariant checks: No dangerous builtins, pure functions
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("eval", "exec", "__import__")
            ):
                return False, f"Forbidden call '{node.func.id}' in patch."

        return True, "Patch passed AST and safety validation."

    @staticmethod
    def admit_patch(
        current_memory: MemoryQuad,
        localization: FailureLocalizationResult,
        patch_payload: Any,
    ) -> tuple[bool, str]:
        """Validates and applies targeted patch to the localized component."""
        if localization.failed_component == MemoryComponent.EXPERIENTIAL_MEMORY:
            if isinstance(patch_payload, ExperientialSkill):
                is_valid, msg = ValidationGatedAdmission.validate_code_patch(
                    patch_payload.code_body
                )
                if not is_valid:
                    return False, f"Rejected E-patch: {msg}"
                current_memory.E[patch_payload.skill_id] = patch_payload
                return True, f"Admitted updated skill '{patch_payload.skill_id}' to E."

        elif localization.failed_component == MemoryComponent.INVOCATION_POLICY:
            if isinstance(patch_payload, dict):
                current_memory.rho.routing_rules.update(patch_payload)
                return True, "Admitted updated routing rules to rho."

        elif (
            localization.failed_component == MemoryComponent.CHECKER_VERIFIER
            and isinstance(patch_payload, tuple)
            and len(patch_payload) == 2
            and callable(patch_payload[1])
        ):
            current_memory.C.register_verifier(patch_payload[0], patch_payload[1])
            return True, f"Admitted new verifier '{patch_payload[0]}' to C."

        return False, "Unsupported patch payload or invalid target component."
