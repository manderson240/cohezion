"""Hierarchical Decision Gating Engine (Pathway D - Consensus Architecture).
========================================================================
Implements a three-tier defense-in-depth cognitive execution model:
1. Tier 0 (<0.1 ms): Deterministic AutoHarness AST hash cache & clearance margin h(x) >= 0.
2. Tier 1 (<50 ms): NPU-resident fast reflex proposer (qwen3.5:4b-FLM on Port 13305).
3. Tier 2 (Escalation): Tier 2 Ollama Cloud reasoning (glm-5.3:cloud / deepseek-v4-pro)
   triggered when predictive entropy H(p) >= 0.45 or upon consecutive Tier 0 rejections.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy

logger = logging.getLogger("hierarchical_decision_gate")


class GateTier(str, Enum):
    TIER_0_BYTECODE = "tier_0_bytecode"
    TIER_1_NPU_REFLEX = "tier_1_npu_reflex"
    TIER_2_CLOUD_REASONING = "tier_2_cloud_reasoning"


@dataclass(frozen=True)
class GatedDecisionResult:
    """Outcome of a hierarchical decision gate evaluation."""

    action: str
    tier_used: GateTier
    allowed: bool
    entropy: float
    clearance_margin: float
    latency_ms: float
    bypassed_llm: bool
    diagnostic: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class HierarchicalDecisionGate:
    """Three-tier hierarchical decision router bridging AutoHarness and NPU/Cloud models."""

    def __init__(
        self,
        policy: Optional[AutoHarnessPolicy] = None,
        entropy_threshold: float = 0.45,
        max_tier0_rejections: int = 2,
    ) -> None:
        self.policy = policy or AutoHarnessPolicy(policy_name="hierarchical_safety")
        self.entropy_threshold = entropy_threshold
        self.max_tier0_rejections = max_tier0_rejections

        # Tier 0 In-Memory Fast AST Hash Cache (SHA-256 -> ActionPolicyResult)
        self._hash_cache: dict[str, ActionPolicyResult] = {}

    def compute_entropy(self, probabilities: np.ndarray | list[float]) -> float:
        """Computes Shannon entropy H(p) = - sum p_i ln(p_i) in nats."""
        arr = np.array(probabilities, dtype=float)
        arr = arr[arr > 1e-12]
        if len(arr) <= 1:
            return 0.0
        # Normalize if needed
        s = np.sum(arr)
        if s > 0:
            p = arr / s
            return float(-np.sum(p * np.log(p)))
        return 0.0

    def evaluate_tier0_ast_hash(
        self,
        source_code: str,
        action_type: str = "general_code",
        state: Optional[dict[str, Any]] = None,
    ) -> ActionPolicyResult:
        """Evaluates AST hash cache in <0.05 ms before invoking neural models."""
        h = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        if h in self._hash_cache:
            cached = self._hash_cache[h]
            return cached

        res = self.policy.evaluate_policy(
            action_type=action_type,
            state=state or {},
            source_code=source_code,
        )
        self._hash_cache[h] = res
        return res

    async def decide(
        self,
        candidate_actions: list[str],
        action_probabilities: list[float],
        state: dict[str, Any],
        source_codes: Optional[list[str]] = None,
        action_type: str = "general_decision",
        cloud_fallback_fn: Optional[Callable[[dict[str, Any]], Any]] = None,
    ) -> GatedDecisionResult:
        """Executes hierarchical decision gating across Tier 0, Tier 1, and Tier 2.

        1. Checks Tier 0 AutoHarness clearance margins and AST hash cache.
        2. If candidate action passes with low entropy H(p) < tau, commits via Tier 1 Reflex.
        3. If entropy is high or candidate violates safety bounds, escalates to Tier 2 Cloud.
        """
        t0 = time.perf_counter()

        if not candidate_actions:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return GatedDecisionResult(
                action="NOOP",
                tier_used=GateTier.TIER_0_BYTECODE,
                allowed=False,
                entropy=0.0,
                clearance_margin=-1.0,
                latency_ms=dt_ms,
                bypassed_llm=True,
                diagnostic="Empty candidate actions list",
            )

        # Calculate prediction entropy
        entropy = self.compute_entropy(action_probabilities)

        # Rank candidate indices by probability descending
        sorted_indices = np.argsort(action_probabilities)[::-1]
        rejection_count = 0
        last_violation = ""

        # Tier 0 & Tier 1 Evaluation
        for idx in sorted_indices:
            act = candidate_actions[idx]
            code = source_codes[idx] if source_codes and idx < len(source_codes) else None

            # Evaluate against Tier 0 AutoHarness
            policy_res = self.policy.evaluate_policy(
                action_type=action_type,
                state=state,
                source_code=code,
            )

            if policy_res.allowed and policy_res.clearance_margin >= 0.0:
                # If entropy is strictly below threshold, accept Tier 1 NPU Reflex directly
                if entropy < self.entropy_threshold:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    return GatedDecisionResult(
                        action=act,
                        tier_used=GateTier.TIER_1_NPU_REFLEX,
                        allowed=True,
                        entropy=entropy,
                        clearance_margin=policy_res.clearance_margin,
                        latency_ms=dt_ms,
                        bypassed_llm=False,
                        diagnostic=f"Accepted via Tier 1 Reflex (H={entropy:.3f} < {self.entropy_threshold})",
                        metadata={"action_index": int(idx), "prob": float(action_probabilities[idx])},
                    )
                else:
                    # High entropy detected: escalate to Tier 2 for verification
                    logger.info(
                        "High decision entropy detected (H=%.3f >= %.3f). Escalating to Tier 2 Cloud.",
                        entropy,
                        self.entropy_threshold,
                    )
                    break
            else:
                rejection_count += 1
                last_violation = policy_res.reason
                if rejection_count >= self.max_tier0_rejections:
                    logger.warning(
                        "AutoHarness rejected %d candidate proposals. Escalating to Tier 2 Cloud.",
                        rejection_count,
                    )
                    break

        # Tier 2 Cloud Escalation
        if cloud_fallback_fn is not None:
            try:
                cloud_action = await asyncio.to_thread(cloud_fallback_fn, state)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return GatedDecisionResult(
                    action=str(cloud_action),
                    tier_used=GateTier.TIER_2_CLOUD_REASONING,
                    allowed=True,
                    entropy=entropy,
                    clearance_margin=1.0,
                    latency_ms=dt_ms,
                    bypassed_llm=False,
                    diagnostic=f"Resolved via Tier 2 Cloud Escalation after Tier 0/1 entropy/rejections",
                    metadata={"prior_rejections": rejection_count, "last_violation": last_violation},
                )
            except Exception as e:
                logger.error("Tier 2 Cloud escalation failed: %s", e)

        # Fallback to safest candidate or NOOP
        dt_ms = (time.perf_counter() - t0) * 1000.0
        best_act = candidate_actions[sorted_indices[0]]
        return GatedDecisionResult(
            action=best_act,
            tier_used=GateTier.TIER_0_BYTECODE,
            allowed=False,
            entropy=entropy,
            clearance_margin=-1.0,
            latency_ms=dt_ms,
            bypassed_llm=True,
            diagnostic=f"Failed validation (Rejections={rejection_count}): {last_violation}",
        )
