from cohezion.agi.arc_aimo_solver import ARCSolverHarness, ARCTask
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


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


def test_autoharness_policy_continuous_clearance_margins():
    """Verify continuous clearance margin h(x) is reported accurately."""
    policy = AutoHarnessPolicy()

    # Memory margin policy: available_gb - 20.0
    res_safe = policy.evaluate_policy("memory_safe", {"available_gb": 32.5})
    assert res_safe.allowed is True
    assert res_safe.clearance_margin == 12.5

    res_unsafe = policy.evaluate_policy("memory_safe", {"available_gb": 14.0})
    assert res_unsafe.allowed is False
    assert res_unsafe.clearance_margin == -6.0

    # Custom margin policy
    policy.register_margin_policy("vram_headroom", lambda s: float(s.get("free_vram", 0.0) - 4.0))
    res_vram = policy.evaluate_policy("vram_headroom", {"free_vram": 8.0})
    assert res_vram.allowed is True
    assert res_vram.clearance_margin == 4.0

    res_vram_low = policy.evaluate_policy("vram_headroom", {"free_vram": 2.0})
    assert res_vram_low.allowed is False
    assert res_vram_low.clearance_margin == -2.0


def test_autoharness_policy_efference_copy_corollary_discharge():
    """Verify corollary discharge detects prediction discrepancy and microsecond halts."""
    policy = AutoHarnessPolicy()

    # Efference ticket predicts memory impact = 18.0 GiB with tolerance 1.5 GiB
    ticket = {"ram_gib": 18.0, "_tolerance": 1.5}

    # Case 1: Actual state closely matches prediction -> Allowed
    state_match = {"ram_gib": 18.8, "mass": 10.0}
    res_ok = policy.evaluate_policy("positive_mass", state_match, efference_ticket=ticket)
    assert res_ok.allowed is True
    assert res_ok.efference_copy["mismatch"] is False
    assert abs(res_ok.efference_copy["residuals"]["ram_gib"] - 0.8) < 1e-5

    # Case 2: Actual state wildly deviates (e.g. unexpected spike to 25.0 GiB) -> Halted
    state_deviated = {"ram_gib": 25.0, "mass": 10.0}
    res_halt = policy.evaluate_policy("positive_mass", state_deviated, efference_ticket=ticket)
    assert res_halt.allowed is False
    assert res_halt.efference_copy["mismatch"] is True
    assert "Corollary discharge mismatch" in res_halt.reason

