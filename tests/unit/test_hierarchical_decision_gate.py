"""Unit tests for Hierarchical Decision Gating Engine (Pathway D)."""

from __future__ import annotations

import pytest
import numpy as np
from unittest.mock import MagicMock

from cohezion.agi.hierarchical_decision_gate import (
    GateTier,
    GatedDecisionResult,
    HierarchicalDecisionGate,
)
from cohezion.agi.autoharness_policy import ActionPolicyResult, AutoHarnessPolicy


def test_shannon_entropy_calculation():
    """Verify Shannon entropy computation for sharp vs uniform distributions."""
    gate = HierarchicalDecisionGate(entropy_threshold=0.45)

    # Degenerate (100% confidence on single action) -> H = 0.0
    h_zero = gate.compute_entropy([1.0, 0.0, 0.0])
    assert pytest.approx(h_zero, abs=1e-5) == 0.0

    # High confidence (e.g. 95% on one action) -> H < 0.25
    h_low = gate.compute_entropy([0.95, 0.05])
    assert h_low < 0.25

    # Uniform (50/50 split) -> H = ln(2) approx 0.693 nats
    h_uniform = gate.compute_entropy([0.5, 0.5])
    assert pytest.approx(h_uniform, rel=1e-2) == 0.693

    # Empty list edge case
    assert gate.compute_entropy([]) == 0.0


def test_tier0_ast_hash_cache_hit():
    """Verify Tier 0 hash cache avoids redundant policy evaluations."""
    mock_policy = MagicMock(spec=AutoHarnessPolicy)
    mock_policy.evaluate_policy.return_value = ActionPolicyResult(
        allowed=True,
        bypassed_llm=True,
        action_type="test_action",
        verification_score=1.0,
        reason="safe",
        clearance_margin=1.5,
        execution_time_ms=0.01,
    )

    gate = HierarchicalDecisionGate(policy=mock_policy)
    source_code = "def action(): return 42"

    # First lookup: executes policy evaluation and caches SHA-256
    res1 = gate.evaluate_tier0_ast_hash(source_code)
    assert res1.allowed is True
    assert mock_policy.evaluate_policy.call_count == 1

    # Second lookup: instant cache hit, call_count remains 1
    res2 = gate.evaluate_tier0_ast_hash(source_code)
    assert res2.allowed is True
    assert mock_policy.evaluate_policy.call_count == 1
    assert res1 == res2


@pytest.mark.asyncio
async def test_tier1_fast_reflex_acceptance():
    """Verify low-entropy safe decisions are accepted instantly via Tier 1 Reflex."""
    gate = HierarchicalDecisionGate(entropy_threshold=0.45)

    candidates = ["MOVE_FORWARD", "TURN_LEFT"]
    # High confidence: 95% forward -> H approx 0.198 < 0.45
    probabilities = [0.95, 0.05]
    state = {"obstacles": []}

    decision = await gate.decide(
        candidate_actions=candidates,
        action_probabilities=probabilities,
        state=state,
        action_type="navigation",
    )

    assert decision.allowed is True
    assert decision.tier_used == GateTier.TIER_1_NPU_REFLEX
    assert decision.action == "MOVE_FORWARD"
    assert decision.entropy < 0.45
    assert decision.clearance_margin >= 0.0


@pytest.mark.asyncio
async def test_tier2_cloud_escalation_on_high_entropy():
    """Verify high entropy H(p) >= 0.45 escalates safely to Tier 2 Cloud reasoning."""
    gate = HierarchicalDecisionGate(entropy_threshold=0.45)

    candidates = ["UP", "DOWN", "LEFT", "RIGHT"]
    # Uniform uncertainty: 25% each -> H = ln(4) approx 1.386 > 0.45
    probabilities = [0.25, 0.25, 0.25, 0.25]
    state = {"grid": [0] * 10}

    def mock_cloud_reasoner(st: dict) -> str:
        return "SPECIAL_SOLVE_MACRO"

    decision = await gate.decide(
        candidate_actions=candidates,
        action_probabilities=probabilities,
        state=state,
        cloud_fallback_fn=mock_cloud_reasoner,
    )

    assert decision.allowed is True
    assert decision.tier_used == GateTier.TIER_2_CLOUD_REASONING
    assert decision.action == "SPECIAL_SOLVE_MACRO"
    assert decision.entropy >= 0.45


@pytest.mark.asyncio
async def test_tier2_escalation_on_policy_rejection():
    """Verify consecutive Tier 0 safety violations escalate to Tier 2 Cloud."""
    mock_policy = MagicMock(spec=AutoHarnessPolicy)
    # Reject candidate proposals (e.g. wall collision)
    mock_policy.evaluate_policy.return_value = ActionPolicyResult(
        allowed=False,
        bypassed_llm=True,
        action_type="collision",
        verification_score=0.0,
        reason="Trajectory collides with boundary wall",
        clearance_margin=-0.5,
        execution_time_ms=0.01,
    )

    gate = HierarchicalDecisionGate(
        policy=mock_policy,
        entropy_threshold=0.45,
        max_tier0_rejections=2,
    )

    candidates = ["STEP_INTO_WALL", "STEP_INTO_LAVA"]
    probabilities = [0.99, 0.01]  # Even with high confidence, safety rejects it!

    def mock_cloud_recovery(st: dict) -> str:
        return "RETREAT_SAFE"

    decision = await gate.decide(
        candidate_actions=candidates,
        action_probabilities=probabilities,
        state={"pos": [0, 0]},
        cloud_fallback_fn=mock_cloud_recovery,
    )

    assert decision.allowed is True
    assert decision.tier_used == GateTier.TIER_2_CLOUD_REASONING
    assert decision.action == "RETREAT_SAFE"


@pytest.mark.asyncio
async def test_empty_candidates_returns_safe_noop():
    """Verify empty candidate list returns non-allowed safe NOOP."""
    gate = HierarchicalDecisionGate()
    decision = await gate.decide([], [], state={})
    assert decision.allowed is False
    assert decision.action == "NOOP"
    assert decision.tier_used == GateTier.TIER_0_BYTECODE
