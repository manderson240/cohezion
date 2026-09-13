import pytest
import time
from cohezion.physics.orch_or_runtime_service import (
    OrchORRuntimeService,
    SuperposedPolicyBranch,
    CollapseResult,
    HIHO_EQUILIBRIUM_TARGET,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


def test_orch_or_single_branch_collapse():
    service = OrchORRuntimeService()
    branch = SuperposedPolicyBranch(
        branch_id="test-b1",
        action_type="orch_or_hiho",
        payload={"coherence": 0.50},
    )
    result = service.evaluate_superposition([branch])

    assert isinstance(result, CollapseResult)
    assert result.collapsed_branch.branch_id == "test-b1"
    assert result.final_coherence == HIHO_EQUILIBRIUM_TARGET
    assert result.is_hiho_equilibrium is True
    assert result.conflict_resolved is True
    assert result.execution_latency_ms < 25.0
    assert result.autoharness_result.allowed is True


def test_orch_or_multi_branch_hiho_convergence():
    service = OrchORRuntimeService()

    # Branch 1: far from HIHO stability (coherence = 0.95, low born probability)
    b1 = SuperposedPolicyBranch(
        branch_id="extreme_coherence_branch",
        action_type="orch_or_hiho",
        payload={"coherence": 0.95},
        tubulin_dimers=5_000,
        initial_coherence=0.95,
        spacetime_coords=(2.0, 1.0, 1.0, 1.0),
        amplitude=0.3 + 0.1j,
    )

    # Branch 2: exact HIHO sweet spot (coherence = 0.50, high born probability)
    b2 = SuperposedPolicyBranch(
        branch_id="hiho_optimal_branch",
        action_type="orch_or_hiho",
        payload={"coherence": 0.50},
        tubulin_dimers=15_000,
        initial_coherence=0.50,
        spacetime_coords=(1.0, 1.0, 0.0, 0.0),  # On null lightcone
        amplitude=0.9 + 0.2j,
    )

    result = service.evaluate_superposition([b1, b2])

    assert result.collapsed_branch.branch_id == "hiho_optimal_branch"
    assert result.final_coherence == HIHO_EQUILIBRIUM_TARGET
    assert result.is_hiho_equilibrium is True
    assert result.gravitational_self_energy_eg > 0.0
    assert result.reduction_time_tau_ms > 0.0
    assert result.execution_latency_ms < 25.0
    assert result.autoharness_result.allowed is True


def test_orch_or_conflict_resolution():
    service = OrchORRuntimeService()

    # Conflicting actions from two competing subagents
    branch_a = SuperposedPolicyBranch(
        branch_id="agent_alpha_divergent",
        action_type="orch_or_hiho",
        payload={"coherence": 0.15, "direction": "left"},
        tubulin_dimers=8_000,
        initial_coherence=0.15,
        amplitude=0.5 + 0.0j,
    )
    branch_b = SuperposedPolicyBranch(
        branch_id="agent_beta_harmonic",
        action_type="orch_or_hiho",
        payload={"coherence": 0.51, "direction": "center"},
        tubulin_dimers=12_000,
        initial_coherence=0.51,
        amplitude=0.8 + 0.0j,
    )

    result = service.resolve_conflicting_actions(branch_a, branch_b)

    assert result.conflict_resolved is True
    assert result.collapsed_branch.branch_id == "agent_beta_harmonic"
    assert result.final_coherence == 0.50
    assert result.autoharness_result.allowed is True


def test_orch_or_latency_benchmark():
    service = OrchORRuntimeService()
    branches = [
        SuperposedPolicyBranch(
            branch_id=f"branch_{i}",
            action_type="orch_or_hiho",
            payload={"coherence": 0.45 + 0.01 * i},
            tubulin_dimers=10_000 + i * 1_000,
            initial_coherence=0.45 + 0.01 * i,
        )
        for i in range(10)
    ]

    t0 = time.perf_counter()
    result = service.evaluate_superposition(branches)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    assert dt_ms < 25.0  # Must be well under the 25ms threshold
    assert result.is_hiho_equilibrium is True
    assert result.autoharness_result.allowed is True
