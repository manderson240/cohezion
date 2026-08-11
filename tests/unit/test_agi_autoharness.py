import pytest
from cohezion.agi.autoharness_policy import AutoHarnessPolicy, ActionPolicyResult
from cohezion.agi.arc_aimo_solver import ARCSolverHarness, ARCTask, ARCResult

def test_autoharness_policy_bounded_grid():
    policy = AutoHarnessPolicy()

    # Valid grid <= 30x30
    valid_grid = [[1, 2], [3, 4]]
    res = policy.evaluate_policy("bounded_grid", {"grid": valid_grid})
    assert res.allowed is True
    assert res.bypassed_llm is True
    assert res.verification_score == 1.0

    # Invalid grid > 30x30
    invalid_grid = [[0] * 35 for _ in range(35)]
    res_inv = policy.evaluate_policy("bounded_grid", {"grid": invalid_grid})
    assert res_inv.allowed is False
    assert res_inv.bypassed_llm is True
    assert "violated deterministic policy" in res_inv.reason

def test_autoharness_policy_positive_mass():
    policy = AutoHarnessPolicy()
    assert policy.evaluate_policy("positive_mass", {"mass": 5.0}).allowed is True
    assert policy.evaluate_policy("positive_mass", {"mass": -1.0}).allowed is False

def test_arc_solver_harness():
    harness = ARCSolverHarness()
    task = ARCTask(
        train_pairs=[([[1, 0], [0, 1]], [[1, 0], [0, 1]])],
        test_inputs=[[[2, 3], [4, 5]]],
    )
    result = harness.solve(task)
    assert result.solved is True
    assert result.policy_bypassed is True
    assert result.predicted_outputs == [[[2, 3], [4, 5]]]
