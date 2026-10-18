"""Unit tests for Terminal-RSI: SPR, TB-GAE, and RSR (arXiv:2610.22192)."""

import pytest
import numpy as np
from cohezion.agi.terminal_rsi import (
    FamilyCalibrationConfig,
    RecursiveTrajectoryRewriter,
    SuccessPrioritizedReward,
    TurnBoundaryGAE,
    TurnStep,
)


class TestSuccessPrioritizedReward:
    """Test SPR mathematical properties and bounded partial credit invariants."""

    def test_failure_is_strictly_bounded_below_one(self):
        spr = SuccessPrioritizedReward()
        # Even with 1,000 passed checks, a failure must NEVER reach 1.0
        reward = spr.compute_reward(strict_success=False, passed_checks=1000)
        assert 0.0 <= reward < 1.0
        assert reward > 0.90  # Bounded below 1

    def test_success_is_strictly_at_least_one(self):
        spr = SuccessPrioritizedReward()
        # With 0 partial checks, a strict success is exactly 1.0
        reward_0 = spr.compute_reward(strict_success=True, passed_checks=0)
        assert reward_0 == 1.0

        # With 50 partial checks, success is in [1.0, 2.0)
        reward_50 = spr.compute_reward(strict_success=True, passed_checks=50)
        assert 1.0 <= reward_50 < 2.0
        assert reward_50 > 1.0

    def test_concavity_of_progress_credit(self):
        spr = SuccessPrioritizedReward()
        p1 = spr.compute_reward(strict_success=False, passed_checks=10)
        p2 = spr.compute_reward(strict_success=False, passed_checks=20)
        p3 = spr.compute_reward(strict_success=False, passed_checks=30)

        delta1 = p2 - p1
        delta2 = p3 - p2
        # Strict concavity: marginal gain strictly diminishes
        assert delta1 > delta2

    def test_family_calibration_multipliers(self):
        configs = {
            "kaggle_arc": FamilyCalibrationConfig(family="kaggle_arc", default_divisor=80.0)
        }
        spr = SuccessPrioritizedReward(family_configs=configs)
        
        # High reward failure suppresses reward (doubles divisor)
        r_normal = spr.compute_reward(strict_success=False, passed_checks=40, family="kaggle_arc")
        r_suppressed = spr.compute_reward(
            strict_success=False, passed_checks=40, family="kaggle_arc", high_reward_failure=True
        )
        assert r_suppressed < r_normal


class TestTurnBoundaryGAE:
    """Test TB-GAE turn-boundary credit assignment and observation invariance."""

    def test_empty_steps(self):
        tb_gae = TurnBoundaryGAE()
        adv, targets = tb_gae.compute_advantages([])
        assert len(adv) == 0
        assert len(targets) == 0

    def test_within_turn_tokens_receive_unit_decay(self):
        # 3 tokens within Turn 0, then 1 token in Turn 1
        steps = [
            TurnStep(turn_id=0, is_decision_token=True, value=1.0, reward=0.0),
            TurnStep(turn_id=0, is_decision_token=True, value=1.0, reward=0.0),
            TurnStep(turn_id=0, is_decision_token=True, value=1.0, reward=0.0),
            TurnStep(turn_id=1, is_decision_token=True, value=2.0, reward=5.0, is_terminal=True),
        ]
        tb_gae = TurnBoundaryGAE(gamma_turn=0.90, lambda_turn=0.80)
        adv, targets = tb_gae.compute_advantages(steps)

        assert len(adv) == 4
        # Terminal step advantage is simply delta = 5.0 - 2.0 = 3.0
        assert pytest.approx(adv[3], rel=1e-4) == 3.0

        # Steps 0, 1, 2 should receive turn-boundary decay when crossing from Turn 0 to Turn 1
        assert adv[2] > 0.0

    def test_cross_turn_decay(self):
        # Turn 0 -> Turn 1 with 1 step each
        steps = [
            TurnStep(turn_id=0, is_decision_token=True, value=0.0, reward=0.0),
            TurnStep(turn_id=1, is_decision_token=True, value=0.0, reward=10.0, is_terminal=True),
        ]
        tb_gae = TurnBoundaryGAE(gamma_turn=0.50, lambda_turn=0.50)
        adv, _ = tb_gae.compute_advantages(steps)

        # Terminal step: delta = 10.0 - 0.0 = 10.0
        assert adv[1] == 10.0
        # Turn 0 step: delta = 0 + gamma_turn * v_next(0.0) - v_curr(0.0) = 0.0
        # adv = delta + gamma * lambda * adv[1] = 0.0 + 0.50 * 0.50 * 10.0 = 2.5
        assert pytest.approx(adv[0], rel=1e-4) == 2.5


class TestRecursiveTrajectoryRewriter:
    """Test RSR trajectory collection and clean replay curation."""

    def test_verified_and_clean_ingestion(self):
        rsr = RecursiveTrajectoryRewriter()
        accepted = rsr.evaluate_and_ingest(
            task_id="arc_task_01",
            actions=[{"tool": "bash", "cmd": "pytest"}],
            final_output="PASS",
            verifier_outcome=True,
            leakage_clean=True,
            runbook="1. Inspect 2. Patch 3. Verify",
        )
        assert accepted is True
        assert len(rsr.verified_pool) == 1

    def test_reject_unverified_or_leaked(self):
        rsr = RecursiveTrajectoryRewriter()
        # Rejected due to verifier failure
        rej1 = rsr.evaluate_and_ingest(
            task_id="arc_task_02",
            actions=[],
            final_output="FAIL",
            verifier_outcome=False,
            leakage_clean=True,
        )
        assert rej1 is False

        # Rejected due to leakage violation
        rej2 = rsr.evaluate_and_ingest(
            task_id="arc_task_03",
            actions=[],
            final_output="PASS",
            verifier_outcome=True,
            leakage_clean=False,
        )
        assert rej2 is False
        assert len(rsr.verified_pool) == 0
