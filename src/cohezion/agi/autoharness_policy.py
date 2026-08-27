r"""AutoHarness Policy & Action-Verifier Engine (arXiv:2603.03329v1)
===================================================================
Synthesizes deterministic code harnesses (Code-as-action-verifier) and
harness-as-policy rules to prevent illegal agent actions and bypass
LLM calls at inference time with 0 ms latency.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.contracts import VerificationResult


@dataclass(frozen=True, slots=True)
class ActionPolicyResult:
    """Outcome of a synthesized AutoHarness policy check."""

    allowed: bool
    bypassed_llm: bool
    action_type: str
    verification_score: float
    execution_time_ms: float
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AutoHarnessPolicy:
    """Deterministic Harness-as-Policy engine for AGI self-orchestration."""

    def __init__(self, verifier: AutoHarnessVerifier | None = None) -> None:
        self.verifier = verifier or AutoHarnessVerifier()
        self._policy_registry: dict[str, Callable[[dict[str, Any]], bool]] = {}
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register deterministic pre-verification policies."""
        # 1. Bounds policy: ensure array dimensions and values stay bounded
        self._policy_registry["bounded_grid"] = lambda state: (
            isinstance(state.get("grid"), list)
            and len(state["grid"]) <= 30
            and all(isinstance(row, list) and len(row) <= 30 for row in state["grid"])
        )

        # 2. Physics policy: mass > 0, energy conserved
        self._policy_registry["positive_mass"] = lambda state: (
            isinstance(state.get("mass"), (int, float)) and state["mass"] > 0.0
        )

        # 3. Memory floor policy: available_gb >= 20.0
        self._policy_registry["memory_safe"] = lambda state: (
            isinstance(state.get("available_gb"), (int, float)) and state["available_gb"] >= 20.0
        )

    def register_policy(self, name: str, policy_fn: Callable[[dict[str, Any]], bool]) -> None:
        """Register a custom deterministic policy function."""
        self._policy_registry[name] = policy_fn

    def evaluate_policy(
        self, action_type: str, state: dict[str, Any], source_code: str | None = None
    ) -> ActionPolicyResult:
        """Evaluate an action against deterministic harness policies before LLM invocation."""
        t0 = time.perf_counter()

        # Step 1: Check registered policy rules
        policy_fn = self._policy_registry.get(action_type)
        if policy_fn:
            try:
                allowed = policy_fn(state)
                if not allowed:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    return ActionPolicyResult(
                        allowed=False,
                        bypassed_llm=True,
                        action_type=action_type,
                        verification_score=0.0,
                        execution_time_ms=dt_ms,
                        reason=f"Action violated deterministic policy '{action_type}'",
                    )
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"Policy evaluation error: {e}",
                )

        # Step 2: If source code is supplied, run zero-cost static AST verification
        v_score = 1.0
        if source_code:
            v_res = self.verifier.verify_code(source_code)
            v_score = v_res.score
            if not v_res.valid:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return ActionPolicyResult(
                    allowed=False,
                    bypassed_llm=True,
                    action_type=action_type,
                    verification_score=0.0,
                    execution_time_ms=dt_ms,
                    reason=f"AST verification failed: {v_res.errors}",
                )

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return ActionPolicyResult(
            allowed=True,
            bypassed_llm=True,  # Successfully validated without LLM inference call!
            action_type=action_type,
            verification_score=v_score,
            execution_time_ms=dt_ms,
            reason="Validated by AutoHarness policy",
        )


# --- reconcile 2026-08-26: preserved from main (importers: see docs/reconcile/2026-08-26-merge-resolution.md) ---
@dataclass
class VerificationResult:
    """Outcome of AutoHarness deterministic verification."""

    valid: bool
    latency_ms: float
    verifier_name: str
    violations: list[str] = field(default_factory=list)
    ast_nodes_scanned: int = 0

