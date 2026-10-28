"""Unit tests for RRSI: Regularized Recursive Self-Improvement of Agent Harnesses."""

from cohezion.agi.rrsi_engine import (
    CandidateHarness,
    EvaluationOutcome,
    HarnessEdit,
    RRSIBudgetScheduler,
    RRSICritic,
    RRSIPruner,
    RRSIRegularizedEngine,
    RRSISelector,
)


def test_rrsi_budget_scheduler():
    scheduler = RRSIBudgetScheduler(initial_budget=5, decay_gamma=0.8, min_budget=1)
    # Iteration 0: floor(5 * 1.0) = 5
    assert scheduler.compute_budget(0) == 5
    # Iteration 1: floor(5 * 0.8) = 4
    assert scheduler.compute_budget(1) == 4
    # Iteration 2: floor(5 * 0.64) = 3
    assert scheduler.compute_budget(2) == 3
    # High iteration: decays to min_budget
    assert scheduler.compute_budget(20) == 1


def test_rrsi_critic_screening():
    critic = RRSICritic()

    clean_edit = HarnessEdit(
        edit_id="clean_1",
        target_component="prompt",
        description="Add structured JSON output schema instructions",
        diff_patch="+ Respond with strict JSON matching schema",
    )
    cand_clean = CandidateHarness("cand_1", "root", 0, [clean_edit])
    passed, _msg = critic.screen(cand_clean)
    assert passed is True

    leaky_edit = HarnessEdit(
        edit_id="leak_1",
        target_component="prompt",
        description="Fix task_408 failure with override",
        diff_patch="+ if problem_id == 'test_case_408': return 42",
    )
    cand_leaky = CandidateHarness("cand_2", "root", 0, [leaky_edit])
    passed_leak, msg_leak = critic.screen(cand_leaky)
    assert passed_leak is False
    assert "Rejected by Critic" in msg_leak


def test_rrsi_selector_noise_floor_and_cost():
    selector = RRSISelector(noise_delta=0.02, cost_lambda=0.0001)

    base = EvaluationOutcome(
        empirical_score=0.70, total_tokens_consumed=1000, execution_time_ms=10.0
    )

    # 1. Gain within noise band (Delta = +0.01 <= 0.02) -> Reject
    noisy = EvaluationOutcome(
        empirical_score=0.71, total_tokens_consumed=1000, execution_time_ms=10.0
    )
    accepted, msg = selector.should_accept(base, noisy)
    assert accepted is False
    assert "noise band" in msg

    # 2. Significant gain exceeding noise floor (Delta = +0.05 > 0.02) -> Accept
    good = EvaluationOutcome(
        empirical_score=0.75, total_tokens_consumed=1050, execution_time_ms=10.5
    )
    accepted_good, msg_good = selector.should_accept(base, good)
    assert accepted_good is True
    assert "exceeds noise threshold" in msg_good

    # 3. Large gain but excessive token bloat (Delta score = +0.03, Delta cost = +5000 tokens)
    # Threshold = 0.02 + 0.0001 * 5000 = 0.02 + 0.50 = 0.52 -> Reject
    bloated = EvaluationOutcome(
        empirical_score=0.73, total_tokens_consumed=6000, execution_time_ms=15.0
    )
    accepted_bloat, msg_bloat = selector.should_accept(base, bloated)
    assert accepted_bloat is False
    assert "insufficient to justify token cost" in msg_bloat


def test_rrsi_pruner_dormancy():
    pruner = RRSIPruner(dormancy_threshold_cycles=3)
    pruner.record_usage("edit_a", current_iteration=1)
    pruner.record_usage("edit_b", current_iteration=4)

    # At iteration 5:
    # edit_a last used at 1 (diff = 4 >= 3) -> prunable
    # edit_b last used at 4 (diff = 1 < 3) -> retain
    prunable = pruner.identify_prunable_edits(["edit_a", "edit_b"], current_iteration=5)
    assert "edit_a" in prunable
    assert "edit_b" not in prunable


def test_rrsi_regularized_engine_orchestration():
    engine = RRSIRegularizedEngine(initial_budget=2, decay_gamma=0.5, noise_delta=0.02)

    edits = [
        HarnessEdit("e1", "tool", "Add bash tool verifier", "+ verify_syntax()"),
        HarnessEdit("e2", "prompt", "Add concise directive", "+ Keep answers concise"),
        HarnessEdit("e3", "memory", "Add LRU cache", "+ Cache results"),
    ]

    # Iteration 0 has budget = 2, proposing 3 edits should be rejected
    cand_oversized, msg = engine.propose_candidate("cand_over", "root", edits)
    assert cand_oversized is None
    assert "exceed annealed budget" in msg

    # Propose 2 edits -> approved
    cand_valid, _msg_valid = engine.propose_candidate("cand_valid", "root", edits[:2])
    assert cand_valid is not None
    assert cand_valid.edit_count == 2

    # Evaluate
    base_eval = EvaluationOutcome(0.60, 500, 5.0)
    cand_eval = EvaluationOutcome(0.68, 520, 5.1)  # Delta +0.08 > 0.02 noise floor
    accepted, _eval_msg = engine.evaluate_and_step(cand_valid, base_eval, cand_eval)

    assert accepted is True
    assert "e1" in engine.active_edits
    assert "e2" in engine.active_edits
    assert engine.iteration == 1
