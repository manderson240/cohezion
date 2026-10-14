"""Unit tests for Monadic Local Markov Planning and Monotonic Improvement Invariant."""

import pytest
from cohezion.planning import (
    LocalMarkovPlanner,
    LocalState,
    PlanM,
    StepResult,
    splitmix64,
)


def test_local_markov_penalties_prevent_deadlock():
    """Verify local state penalties apply only locally, avoiding global constraint pollution."""
    planner = LocalMarkovPlanner(step_budget=20, wall_bump_penalty=50.0)

    s0 = LocalState.create((5, 5))
    planner.record_visit(s0)

    # Agent bumps into wall taking action 'UP' at (5, 5)
    planner.penalize_local_action(s0, "UP")

    # Penalty at (5, 5) for 'UP' is >= 50
    assert planner.get_action_penalty(s0, "UP") >= 50.0
    # Penalty at (5, 5) for 'RIGHT' is 0 + revisit penalty
    assert planner.get_action_penalty(s0, "RIGHT") < 50.0

    # Moving to a new state (6, 5) has NO 'UP' penalty! Global colors/directions are not banned!
    s1 = s0.transition((6, 5), action="RIGHT")
    assert planner.get_action_penalty(s1, "UP") == 0.0


def test_plan_m_monadic_bind_and_composition():
    """Verify PlanM monadic chaining, state threading, and trace accumulation."""
    def step1(s: LocalState) -> StepResult[LocalState, int]:
        s_next = s.transition((s.coordinates[0] + 1,), action="INC")
        return StepResult(value=10, next_state=s_next, cost=1.0, trace=("STEP_1",))

    def step2(val: int) -> PlanM[LocalState, int]:
        def _step(s: LocalState) -> StepResult[LocalState, int]:
            s_next = s.transition((s.coordinates[0] + val,), action="JUMP")
            return StepResult(value=val * 2, next_state=s_next, cost=2.0, trace=("STEP_2",))
        return PlanM(_step)

    initial_s = LocalState.create((0,))
    plan1 = PlanM(step1)
    chained_plan = plan1.bind(step2)

    result = chained_plan.run(initial_s)
    assert result.value == 20
    assert result.cost == 3.0
    assert result.trace == ("STEP_1", "STEP_2")
    assert result.next_state.coordinates == (11,)


def test_monotonic_improvement_invariant():
    """Verify that secondary plans cannot clobber valid primary plans, but fill dummy slots."""
    # Primary plan produces valid output "NEURAL_PRED"
    primary_valid = PlanM.pure("NEURAL_PRED")
    # Secondary plan produces heuristic output "DSL_PRED"
    secondary = PlanM.pure("DSL_PRED")

    is_dummy = lambda x: x == "DUMMY"

    # Test 1: Valid primary preserves primary in Slot 1, secondary in Slot 2
    ens1 = PlanM.monotonic_ensemble(primary_valid, secondary, is_dummy_fn=is_dummy)
    res1 = ens1.run(LocalState.create((0,)))
    assert res1.value == ("NEURAL_PRED", "DSL_PRED")

    # Test 2: Dummy primary promotes secondary to primary Slot 1
    primary_dummy = PlanM.pure("DUMMY")
    ens2 = PlanM.monotonic_ensemble(primary_dummy, secondary, is_dummy_fn=is_dummy)
    res2 = ens2.run(LocalState.create((0,)))
    assert res2.value == ("DSL_PRED", None)
