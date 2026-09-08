"""Unit tests for Sheaf Consistency Gate and Dynamic OOMGuard with Shmem accounting."""

from cohezion.governance.sheaf_consistency_gate import SheafConsistencyGate
from cohezion.reliability.oom_guard import OOMGuard


def test_sheaf_consistency_cohomology_clean_consensus():
    gate = SheafConsistencyGate(tolerance=0.10)

    # 3 agents in coherent agreement
    claims = {
        "agent_arch": [0.50, 0.51, 0.49],
        "agent_dev": [0.51, 0.50, 0.50],
        "agent_qa": [0.49, 0.50, 0.51],
    }
    intersections = [("agent_arch", "agent_dev"), ("agent_dev", "agent_qa")]

    report = gate.evaluate_consistency(claims, intersections)
    assert report.is_consistent is True
    assert report.dim_h0_consensus == 1
    assert report.dim_h1_obstructions == 0
    assert len(report.conflicting_pairs) == 0


def test_sheaf_consistency_cohomology_detects_contradiction():
    gate = SheafConsistencyGate(tolerance=0.10)

    # Agent QA fundamentally disagrees with Agent Dev
    claims = {
        "agent_arch": [0.50, 0.50, 0.50],
        "agent_dev": [0.50, 0.50, 0.50],
        "agent_qa": [0.90, 0.10, 0.20],  # Major epistemic contradiction
    }
    intersections = [("agent_arch", "agent_dev"), ("agent_dev", "agent_qa")]

    report = gate.evaluate_consistency(claims, intersections)
    assert report.is_consistent is False
    assert report.dim_h0_consensus == 0
    assert report.dim_h1_obstructions == 1
    assert len(report.conflicting_pairs) == 1
    assert report.conflicting_pairs[0][0] == "agent_dev"
    assert report.conflicting_pairs[0][1] == "agent_qa"


def test_oom_guard_shmem_and_dynamic_floor():
    state = OOMGuard.get_memory_state(largest_model_gb=16.0)
    assert state.total_gb > 0.0
    assert state.available_gb >= 0.0
    assert state.shmem_gb >= 0.0
    assert state.dynamic_floor_gb >= 20.0
