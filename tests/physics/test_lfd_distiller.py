"""Unit and Invariant Tests for LLM-to-Flow Distillation (arXiv:2610.17246)."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.lfd_distiller import (
    AdaptiveCurriculumManager,
    FlowDPOLossEngine,
    LLMToFlowDistillationEngine,
    PermutationInvariantJudge,
    SubGoal,
)


def test_permutation_invariant_judge_symmetry() -> None:
    """Verifies that the judge eliminates position bias via reciprocal evaluation."""
    judge = PermutationInvariantJudge(min_margin=0.05, min_confidence=0.55)
    subgoal = SubGoal(
        goal_id="g1",
        description="Target norm 1.0",
        difficulty_level=1,
        target_metric="norm",
        threshold=1.0,
    )

    # State A is closer to 1.0 than State B
    state_a = np.array([0.9, 0.1, 0.0])  # norm ~= 0.905, diff to 1.0 ~= 0.095
    state_b = np.array([0.4, 0.1, 0.0])  # norm ~= 0.412, diff to 1.0 ~= 0.588

    # Pass 1: (a, b) -> a should win
    outcome_ab, conf_ab, margin_ab = judge.evaluate_pair(state_a, state_b, subgoal)
    assert outcome_ab == "a_wins"
    assert conf_ab > 0.60
    assert margin_ab > 0.05

    # Pass 2: (b, a) -> b should lose, so winner is 'b_wins' relative to the input ordering (b, a)
    # which corresponds to sample 'a' winning in both cases!
    outcome_ba, conf_ba, margin_ba = judge.evaluate_pair(state_b, state_a, subgoal)
    assert outcome_ba == "b_wins"
    assert conf_ba == pytest.approx(conf_ab, abs=1e-5)
    assert margin_ba == pytest.approx(margin_ab, abs=1e-5)


def test_permutation_invariant_judge_abstention() -> None:
    """Verifies that nearly identical states are cleanly relegated to abstention."""
    judge = PermutationInvariantJudge(min_margin=0.05)
    subgoal = SubGoal(
        goal_id="g1",
        description="Target norm 1.0",
        difficulty_level=1,
        target_metric="norm",
        threshold=1.0,
    )

    state_a = np.array([1.0, 0.0, 0.0])
    state_b = np.array([0.999, 0.001, 0.0])  # Extremely close in score

    outcome, _conf, _margin = judge.evaluate_pair(state_a, state_b, subgoal)
    assert outcome == "abstain"


def test_adaptive_curriculum_progression() -> None:
    """Verifies that the curriculum relaxes when coverage is low and tightens when coverage is high."""
    target_spec = {"name": "HIHO Attractor", "metric": "norm", "target_value": 2.0}
    manager = AdaptiveCurriculumManager(
        target_goal_spec=target_spec,
        min_coverage=0.20,
        max_coverage=0.60,
    )

    # Initial subgoal threshold is relaxed: 2.0 * (1 - 0.6) = 0.8
    assert manager.state.current_subgoal.threshold == pytest.approx(0.8, abs=1e-5)

    # Test 1: Low coverage (0.05 < 0.20) -> should relax
    subgoal_relaxed = manager.step_curriculum(coverage=0.05)
    assert "relaxed" in subgoal_relaxed.goal_id
    assert subgoal_relaxed.relaxation_factor > 0.6
    assert subgoal_relaxed.threshold < 0.8

    # Test 2: High coverage (0.85 > 0.60) -> should tighten
    subgoal_tightened = manager.step_curriculum(coverage=0.85)
    assert "tightened" in subgoal_tightened.goal_id
    assert subgoal_tightened.difficulty_level == 2
    assert subgoal_tightened.threshold > subgoal_relaxed.threshold

    # Test 3: Optimal coverage (0.45 in [0.20, 0.60]) -> should maintain
    subgoal_maintained = manager.step_curriculum(coverage=0.45)
    assert "maintained" in subgoal_maintained.goal_id
    assert subgoal_maintained.threshold == pytest.approx(subgoal_tightened.threshold)


def test_flow_dpo_loss_engine() -> None:
    """Verifies the Bradley-Terry DPO softplus loss computation and monotonic margin behavior."""
    engine = FlowDPOLossEngine(beta=0.1)

    # Scenario 1: Model prefers winner strongly
    log_theta_w = np.array([2.0, 3.0])
    log_ref_w = np.array([0.0, 0.0])
    log_theta_l = np.array([-2.0, -3.0])
    log_ref_l = np.array([0.0, 0.0])

    loss_aligned, margin_aligned, kl_aligned = engine.compute_loss(
        log_theta_w, log_ref_w, log_theta_l, log_ref_l
    )

    # Scenario 2: Model prefers loser (misaligned)
    log_theta_w_bad = np.array([-2.0, -3.0])
    log_theta_l_bad = np.array([2.0, 3.0])

    loss_misaligned, margin_misaligned, _ = engine.compute_loss(
        log_theta_w_bad, log_ref_w, log_theta_l_bad, log_ref_l
    )

    # Loss must be strictly higher for misaligned policy
    assert loss_misaligned > loss_aligned
    assert margin_aligned > 0.0
    assert margin_misaligned < 0.0
    assert kl_aligned >= 0.0


def test_llm_to_flow_distillation_engine_end_to_end() -> None:
    """End-to-end integration test of the full LFD engine."""
    target_spec = {"name": "Spherical Attractor", "metric": "norm", "target_value": 1.0}
    lfd = LLMToFlowDistillationEngine(
        target_goal_spec=target_spec,
        beta=0.1,
        min_coverage=0.10,
        max_coverage=0.70,
    )

    # Synthesize candidate samples on 3D space
    np.random.seed(42)
    samples = [np.random.randn(3) * 0.5 for _ in range(12)]

    # Mock log-likelihood functions
    def mock_log_theta(x: np.ndarray) -> float:
        # Policy gives higher probability to vectors closer to norm 0.5
        return -float(abs(np.linalg.norm(x) - 0.5))

    def mock_log_ref(x: np.ndarray) -> float:
        # Reference is uniform / zero-mean isotropic Gaussian
        return -0.5 * float(np.dot(x, x))

    metrics = lfd.run_distillation_step(
        samples=samples,
        log_prob_theta_fn=mock_log_theta,
        log_prob_ref_fn=mock_log_ref,
        max_pairs=10,
    )

    assert metrics.n_pairs_generated > 0
    assert metrics.abstention_rate >= 0.0
    assert metrics.mean_dpo_loss > 0.0
    assert len(lfd.distillation_log) == 1
    assert lfd.curriculum.state.current_round == 1
