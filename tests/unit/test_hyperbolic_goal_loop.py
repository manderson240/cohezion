"""Unit tests for Hyperbolic Goal-Loop Engineering System."""

import pytest
import numpy as np
from cohezion.compound.hyperbolic_goal_loop import (
    GoalState,
    HyperbolicGoal,
    HyperbolicLoopController,
    HyperbolicGoalLoopRefactorEngine,
)


class TestHyperbolicMetrics:
    """Test Poincaré hyperbolic distance invariants."""

    def test_distance_at_origin(self):
        controller = HyperbolicLoopController(
            loop_id="test_loop",
            goal=HyperbolicGoal(goal_id="g1", intent="Test"),
        )
        origin = np.zeros(16, dtype=np.float64)
        dist = controller.compute_poincare_distance(origin, origin)
        assert pytest.approx(dist, abs=1e-5) == 0.0

    def test_distance_symmetry(self):
        controller = HyperbolicLoopController(
            loop_id="test_loop",
            goal=HyperbolicGoal(goal_id="g1", intent="Test"),
        )
        u = np.array([0.1, 0.2, 0.3] + [0.0] * 13, dtype=np.float64)
        v = np.array([0.3, -0.1, 0.2] + [0.0] * 13, dtype=np.float64)

        d_uv = controller.compute_poincare_distance(u, v)
        d_vu = controller.compute_poincare_distance(v, u)
        assert pytest.approx(d_uv, rel=1e-5) == d_vu
        assert d_uv > 0.0

    def test_hyperbolic_growth_near_boundary(self):
        controller = HyperbolicLoopController(
            loop_id="test_loop",
            goal=HyperbolicGoal(goal_id="g1", intent="Test"),
        )
        origin = np.zeros(16, dtype=np.float64)
        near_boundary = np.zeros(16, dtype=np.float64)
        near_boundary[0] = 0.99  # Near boundary ||z|| -> 1

        dist = controller.compute_poincare_distance(origin, near_boundary)
        # Hyperbolic distance expands logarithmically toward infinity near the boundary
        assert dist > 4.0


class TestHyperbolicLoopController:
    """Test closed-loop feedback, SPR gating, and Zobrist anti-cycle detection."""

    def test_convergence_on_strict_success(self):
        goal = HyperbolicGoal(goal_id="g_conv", intent="Converge to solution")
        controller = HyperbolicLoopController(loop_id="loop_conv", goal=goal)

        # Incomplete iteration
        conv1, spr1, hyp1 = controller.evaluate_step(
            action_name="partial_patch",
            strict_success=False,
            passed_checks=25,
            new_coord=np.ones(16) * 0.10,
        )
        assert not conv1
        assert spr1 < 1.0
        assert goal.state == GoalState.ACTIVE

        # Verified success iteration
        conv2, spr2, hyp2 = controller.evaluate_step(
            action_name="verified_sota_patch",
            strict_success=True,
            passed_checks=50,
            new_coord=np.zeros(16),
        )
        assert conv2
        assert spr2 >= 1.0
        assert goal.state == GoalState.CONVERGED
        assert pytest.approx(hyp2, abs=1e-4) == 0.0

    def test_zobrist_livelock_detection(self):
        goal = HyperbolicGoal(goal_id="g_cycle", intent="Detect cycle")
        controller = HyperbolicLoopController(loop_id="loop_cycle", goal=goal)

        fixed_coord = np.ones(16) * 0.05
        # Repeat identical state twice
        controller.evaluate_step("oscillate", strict_success=False, passed_checks=5, new_coord=fixed_coord)
        assert goal.state == GoalState.ACTIVE

        # Second identical state triggers livelock
        controller.evaluate_step("oscillate", strict_success=False, passed_checks=5, new_coord=fixed_coord)
        assert goal.state == GoalState.LIVELOCK_DETECTED


class TestHyperbolicGoalLoopRefactorEngine:
    """Test automated refactoring of linear traces into closed-loop controllers."""

    def test_refactor_linear_trace_to_goal_loop(self):
        engine = HyperbolicGoalLoopRefactorEngine()
        events = [
            {"action": "explore_hypothesis", "strict_success": False, "passed_checks": 10},
            {"action": "tune_invariants", "strict_success": False, "passed_checks": 30},
            {"action": "autoharness_verify", "strict_success": True, "passed_checks": 60},
        ]

        goal, controller = engine.refactor_trace(
            trace_id="trace_kaggle_arc2_v17",
            events=events,
            domain="arc_agi",
        )

        assert goal.state == GoalState.CONVERGED
        assert controller.iteration_count == 3
        assert len(controller.history) == 3
        assert controller.history[-1]["spr_score"] >= 1.0
