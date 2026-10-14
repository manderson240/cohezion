"""Unit tests for Monadic Trace Engine, Markov Transition System, and Recursive Trace Logic."""

import pytest

from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.agi.monadic_trace_engine import (
    CompetitionState,
    Either,
    KaggleAscentMonad,
    MarkovTransitionEngine,
    RecursiveTraceEngine,
    TraceStep,
    Writer,
    ZobristGridHasher,
    autocontext_step_monad,
    autoharness_arc_verifier_monad,
    markov_zobrist_step_monad,
    refactor_monadic_trace_to_goal_plan,
    run_monadic_arc_pipeline,
    run_monadic_goal_loop,
)


def test_either_monad_laws() -> None:
    """Validate Left/Right either monad, short-circuiting on invariant failure."""
    right_val = Either.right(42)
    assert right_val.is_right is True
    assert right_val.value == 42

    # Map
    mapped = right_val.map(lambda x: x * 2)
    assert mapped.value == 84

    # Bind success
    bound = right_val.bind(lambda x: Either.right(str(x)))
    assert bound.value == "42"

    # Bind short-circuit to Left
    left_fail = right_val.bind(lambda x: Either.left("Invariant violation"))
    assert left_fail.is_right is False
    assert left_fail.error == "Invariant violation"

    # Further binds on Left short-circuit immediately without executing
    never_called = False
    def _dummy(x):
        nonlocal never_called
        never_called = True
        return Either.right(x)

    short_circuited = left_fail.bind(_dummy)
    assert short_circuited.is_right is False
    assert never_called is False


def test_writer_monad_log_accumulation() -> None:
    """Validate Writer monad monoidal trace log concatenation."""
    w1 = Writer(10, ("step1",))
    w2 = w1.bind(lambda v: Writer(v + 5, ("step2",)))

    assert w2.value == 15
    assert w2.logs == ("step1", "step2")


def test_zobrist_grid_hasher() -> None:
    """Validate 64-bit Zobrist grid hashing determinism and sensitivity."""
    hasher = ZobristGridHasher(max_h=10, max_w=10, num_colors=10)
    g1 = [[1, 2], [3, 4]]
    g2 = [[1, 2], [3, 4]]
    g3 = [[1, 2], [3, 5]]  # Delta at (1, 1)

    h1 = hasher.hash_grid(g1)
    h2 = hasher.hash_grid(g2)
    h3 = hasher.hash_grid(g3)

    assert h1 == h2  # Determinism
    assert h1 != h3  # Single cell sensitivity
    assert isinstance(h1, int)
    assert h1.bit_length() <= 64


def test_markov_cycle_detection_and_entropy() -> None:
    """Validate Markov chain state transition tracking and cycle detection."""
    markov = MarkovTransitionEngine()
    h_a = 0xAAAA
    h_b = 0xBBBB

    markov.record_transition(h_a, h_b)
    markov.record_transition(h_b, h_a)

    history = [h_a, h_b, h_a, h_b, h_a]
    assert markov.detect_cycle(history, h_a, threshold=3) is True
    assert markov.detect_cycle(history, h_b, threshold=3) is False

    entropy = markov.compute_cycle_entropy(history)
    assert entropy > 0.0


def test_recursive_trace_credit_and_pruning() -> None:
    """Validate credit assignment along execution trace and subtree pruning."""
    engine = RecursiveTraceEngine()
    steps = (
        TraceStep(0, "op_0", 2.0, 0x111, 1.0, "start"),
        TraceStep(1, "op_1", 2.1, 0x222, 1.2, "transform"),
        TraceStep(2, "op_2", 2.2, 0x333, 1.5, "finish"),
    )

    credits = engine.assign_credit(steps, terminal_reward=100.0, gamma=0.9)
    assert len(credits) == 3
    assert credits[2] == 100.0
    assert abs(credits[1] - 90.0) < 1e-5
    assert abs(credits[0] - 81.0) < 1e-5

    # Test equivalence class pruning on failed state
    engine.prune_branch_on_violation(failed_state_hash=0xDEAD, history=[0x111, 0xDEAD])
    assert engine.is_branch_pruned(0xDEAD) is True
    assert engine.is_branch_pruned(0x111 ^ 0xDEAD, parent_hash=0x111) is True
    assert engine.is_branch_pruned(0x222) is False


def test_monadic_arc_pipeline_success() -> None:
    """Validate composable monadic ARC pipeline executing valid transforms."""
    grid = [[1, 2], [3, 4]]

    # Transformation: rotate 90 degrees clockwise
    def rot90(g: list[list[int]]) -> list[list[int]]:
        return [list(reversed(col)) for col in zip(*g, strict=True)]

    # Transformation: recolor 4 -> 5
    def recolor(g: list[list[int]]) -> list[list[int]]:
        return [[5 if c == 4 else c for c in row] for row in g]

    res, trace = run_monadic_arc_pipeline(
        initial_grid=grid,
        operators=[rot90, recolor],
        expected_colors={1, 2, 3, 5},
    )

    assert res.is_right is True
    final_grid, final_state = res.value
    assert final_grid == [[3, 1], [5, 2]]
    assert final_state.step_count == 2
    assert len(trace) > 0


def test_monadic_arc_pipeline_short_circuits_on_invariant_violation() -> None:
    """Validate that monadic pipeline halts immediately upon AutoHarness invariant violation."""
    grid = [[1, 2], [3, 4]]

    # Malicious/buggy operator: produces invalid color 15 (not in [0..9])
    def illegal_color_op(g: list[list[int]]) -> list[list[int]]:
        return [[15, 2], [3, 4]]

    def second_op_never_reached(g: list[list[int]]) -> list[list[int]]:
        pytest.fail("Second operator was reached despite invariant failure!")
        return g

    res, trace = run_monadic_arc_pipeline(
        initial_grid=grid,
        operators=[illegal_color_op, second_op_never_reached],
        expected_colors=None,
    )

    assert res.is_right is False
    assert "Invalid color 15 not in [0, 9]" in res.error


def test_kaggle_ascent_monad_run_with_goal() -> None:
    """Validate that run_with_goal commits bounded PlanSegment to MemoryAsPlans."""
    goal = GoalSpecification(
        goal_id="goal_arc_unit_test",
        title="ARC Unit Invariant Goal",
        target_metric="invariant_pass",
        target_threshold=1.0,
    )
    state = CompetitionState(task_name="arc_task_001", grid=[[1, 2], [3, 4]])
    monad = KaggleAscentMonad.unit([[1, 2], [3, 4]])

    either_res, memory = monad.run_with_goal(goal, state)
    assert either_res.is_right is True
    assert len(memory.segments) == 1
    seg = memory.segments[0]
    assert seg.goal_id == "goal_arc_unit_test"
    assert seg.progress == 1.0
    assert seg.committed is True
    assert seg.verification_proof is not None


def test_refactor_monadic_trace_to_goal_plan() -> None:
    """Validate refactoring a linear TraceStep tuple into a PlanSegment."""
    goal = GoalSpecification(
        goal_id="goal_refactor_test",
        title="Refactor Monadic Trace Test",
        target_metric="trace_compression",
        target_threshold=1.0,
    )
    trace = (
        TraceStep(0, "autocontext_step", 2.0, 0x111, 0.5, "step 0"),
        TraceStep(1, "autoharness_verify", 2.0, 0x222, 0.4, "step 1"),
    )
    segment, memory = refactor_monadic_trace_to_goal_plan(
        goal=goal,
        trace=trace,
        success=True,
        details={"model": "qwen3.5:397b-cloud"},
    )
    assert segment.progress == 1.0
    assert segment.verification_proof is not None
    assert "trace_proof_" in segment.verification_proof
    assert segment.contract_guidance["trace_steps_count"] == 2
    assert len(memory.segments) == 1


def test_run_monadic_goal_loop_convergence_and_adaptation() -> None:
    """Validate closed goal loop over candidate operators until invariant satisfaction."""
    goal = GoalSpecification(
        goal_id="goal_arc_loop_solve",
        title="ARC Multi-Candidate Goal Loop",
        target_metric="grid_solution",
        target_threshold=1.0,
        max_iterations=3,
    )
    initial_grid = [[1, 2], [3, 4]]

    # Candidate 0: illegal color 15 (rejected)
    candidate_0 = [lambda g: [[15, 2], [3, 4]]]
    # Candidate 1: valid rot90 (accepted, satisfies expected_colors)
    candidate_1 = [lambda g: [[3, 1], [4, 2]]]

    converged, memory, final_grid = run_monadic_goal_loop(
        goal=goal,
        initial_grid=initial_grid,
        candidate_operator_sets=[candidate_0, candidate_1],
        expected_colors={1, 2, 3, 4},
    )

    assert converged is True
    assert final_grid == [[3, 1], [4, 2]]
    # Memory should hold the rejected attempt and the successful attempt
    assert len(memory.segments) == 2
    assert memory.segments[0].progress == 0.0  # Failed attempt
    assert memory.segments[1].progress == 1.0  # Succeeded attempt

