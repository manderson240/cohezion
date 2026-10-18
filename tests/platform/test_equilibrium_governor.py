"""Unit tests for Master Cybernetic Equilibrium Governor (VSM System 3)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.cybernetics.proprioceptive_sensor import Proprioceptive12DState
from cohezion.platform.equilibrium_governor import (
    DispatchTier,
    GovernorAction,
    MasterEquilibriumGovernor,
    get_equilibrium_governor,
)


def test_equilibrium_governor_singleton() -> None:
    """Verify governor singleton initialization."""
    gov1 = get_equilibrium_governor()
    gov2 = get_equilibrium_governor()
    assert gov1 is gov2
    assert isinstance(gov1, MasterEquilibriumGovernor)


def test_lyapunov_drift_plus_penalty_monotonicity() -> None:
    """Verify Lyapunov Drift-Plus-Penalty scales monotonically with queue backlog."""
    gov = MasterEquilibriumGovernor(lyapunov_tradeoff_v=5.0)

    # Empty queue
    dpp_empty = gov.compute_lyapunov_drift_plus_penalty(
        DispatchTier.TIER1_LOCAL_NPU, resource_cost=1.0
    )

    # Add backlog
    gov.record_queue_arrival("kaggle", count=10)
    gov.record_queue_arrival("research", count=5)
    dpp_loaded = gov.compute_lyapunov_drift_plus_penalty(
        DispatchTier.TIER1_LOCAL_NPU, resource_cost=1.0
    )

    assert dpp_loaded > dpp_empty

    # Drain queue
    gov.record_queue_completion("kaggle", count=10)
    gov.record_queue_completion("research", count=5)
    dpp_cleared = gov.compute_lyapunov_drift_plus_penalty(
        DispatchTier.TIER1_LOCAL_NPU, resource_cost=1.0
    )

    assert pytest.approx(dpp_cleared, rel=1e-5) == dpp_empty


def test_evaluate_dispatch_tier_mapping() -> None:
    """Verify optimal tier dispatch based on task complexity."""
    gov = MasterEquilibriumGovernor()

    # 1. Micro-verification -> Tier 1 NPU
    act_micro = gov.evaluate_dispatch(task_type="ast_verify")
    assert isinstance(act_micro, GovernorAction)
    assert act_micro.allowed is True
    assert act_micro.tier == DispatchTier.TIER1_LOCAL_NPU
    assert act_micro.model_hint == "qwen3.5-4b-FLM"

    # 2. Heavy Coding -> Tier 2 Cloud MoE
    act_code = gov.evaluate_dispatch(task_type="coding_refactor", estimated_tokens=16000)
    assert act_code.allowed is True
    assert act_code.tier == DispatchTier.TIER2_OLLAMA_CLOUD
    assert "glm-5.3" in act_code.model_hint or "deepseek" in act_code.model_hint

    # 3. Frontier Meta-Architecture -> Tier 3 Thinking Cloud
    act_frontier = gov.evaluate_dispatch(task_type="meta_architecture", required_reasoning="max")
    assert act_frontier.allowed is True
    assert act_frontier.tier == DispatchTier.TIER3_THINKING_API
    assert "gemini-3.8-flash-high" in act_frontier.model_hint


def test_autogenic_inhibition_safeguard() -> None:
    """Verify governor fails closed if proprioceptive mechanoreceptors signal memory yield stress."""
    gov = MasterEquilibriumGovernor()

    # Simulate critical memory strain (> 0.85)
    critical_state = Proprioceptive12DState(
        ast_depth=10,
        mcts_frontier_breadth=5,
        context_occupancy_ratio=0.5,
        turn_execution_latency=1.0,
        ast_node_length=100,
        ast_mutation_velocity=10.0,
        gto_compute_tension=0.5,
        gtt_memory_strain=0.92,  # Critical strain
        joint_limit_margin=0.1,
        efference_residual=0.0,
        vestibular_hiho_curvature=0.02,
        metabolic_fatigue_entropy=0.1,
    )

    with patch.object(gov.proprioception, "sample", return_value=critical_state):
        action = gov.evaluate_dispatch(task_type="heavy_computation")
        assert action.allowed is False
        assert "Autogenic inhibition tripped" in action.reason
