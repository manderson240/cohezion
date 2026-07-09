"""TDD tests for RubricMiddleware wiring in CompoundExecutor (Task #23).

V-Model level: AD1 (Architecture Design) — integration between CompoundExecutor
post-execution path and RubricMiddleware judgment.

V-Model contracts:
  AD1: CompoundExecutor accepts rubric_middleware kwarg in __init__
  AD2: _rubric_middleware attribute stored on executor
  AD3: executor exposes _evaluate_rubric() helper (or equivalent gate)
  AD4: rejected output (passed=False) sets should_refine=False gate
  AD5: rejected output skips MGPO accumulation
  AD6: passed output still reaches MGPO accumulator
  AD7: absent rubric_middleware is a no-op (no AttributeError)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.rubric_middleware import RubricMiddleware, RubricVerdict


def _make_executor(rubric_middleware=None):
    return CompoundExecutor(
        mcp_client=None,
        skill_refiner=MagicMock(),
        enable_skill_refinement=True,
        enable_guardrails=False,
        rubric_middleware=rubric_middleware,
    )


# ── AD1/AD2: constructor & attribute ─────────────────────────────────────────


def test_executor_accepts_rubric_middleware_kwarg():
    """CompoundExecutor.__init__ must accept rubric_middleware without raising."""
    rm = RubricMiddleware(rubric="Output must be concise.")
    ex = _make_executor(rubric_middleware=rm)
    assert ex is not None


def test_executor_stores_rubric_middleware():
    """_rubric_middleware must be stored on the executor instance."""
    rm = RubricMiddleware(rubric="Output must be coherent.")
    ex = _make_executor(rubric_middleware=rm)
    assert hasattr(ex, "_rubric_middleware"), "_rubric_middleware attribute missing"
    assert ex._rubric_middleware is rm


def test_executor_none_rubric_middleware_stored():
    """When no rubric_middleware is passed, _rubric_middleware must be None."""
    ex = _make_executor(rubric_middleware=None)
    assert ex._rubric_middleware is None


# ── AD7: no rubric_middleware is noop ────────────────────────────────────────


def test_no_rubric_middleware_does_not_raise():
    """Executor without rubric_middleware must not raise during accumulation."""
    ex = _make_executor(rubric_middleware=None)
    ex._recent_skill_names = []
    # Direct call to the internal gate that would use rubric middleware
    ex._recent_skill_names.append("some_skill")
    ex._check_mgpo_batch()  # must not raise


# ── AD5/AD6: MGPO accumulation gating ────────────────────────────────────────


def test_rejected_output_skips_mgpo_accumulation():
    """When rubric rejects output, skill must not be added to _recent_skill_names."""
    failing_rm = MagicMock(spec=RubricMiddleware)
    failing_rm.evaluate.return_value = RubricVerdict(passed=False, reason="Output is incoherent.")

    ex = _make_executor(rubric_middleware=failing_rm)
    ex._recent_skill_names = []

    # Simulate the rubric-gated accumulation path
    ex._rubric_gated_accumulate(
        skill_name="rejected_skill",
        task_output="Bad output.",
    )

    assert "rejected_skill" not in ex._recent_skill_names, (
        "Rejected skill must not enter MGPO accumulator"
    )


def test_passed_output_reaches_mgpo_accumulator():
    """When rubric passes output, skill must be added to _recent_skill_names."""
    passing_rm = MagicMock(spec=RubricMiddleware)
    passing_rm.evaluate.return_value = RubricVerdict(passed=True, reason="Output looks good.")

    ex = _make_executor(rubric_middleware=passing_rm)
    ex._recent_skill_names = []

    ex._rubric_gated_accumulate(
        skill_name="accepted_skill",
        task_output="Good output.",
    )

    assert "accepted_skill" in ex._recent_skill_names, "Accepted skill must enter MGPO accumulator"


def test_no_rubric_middleware_accumulates_unconditionally():
    """Without rubric_middleware, skill is accumulated regardless."""
    ex = _make_executor(rubric_middleware=None)
    ex._recent_skill_names = []

    ex._rubric_gated_accumulate(
        skill_name="unconditional_skill",
        task_output="Any output.",
    )

    assert "unconditional_skill" in ex._recent_skill_names


# ── AD4: should_refine gate ───────────────────────────────────────────────────


def test_rejected_output_sets_rubric_passed_false():
    """_evaluate_rubric returns False when middleware rejects."""
    failing_rm = MagicMock(spec=RubricMiddleware)
    failing_rm.evaluate.return_value = RubricVerdict(passed=False, reason="Bad.")

    ex = _make_executor(rubric_middleware=failing_rm)
    result = ex._evaluate_rubric(task_output="Bad output.", task_context="skill")

    assert result is False


def test_passed_output_sets_rubric_passed_true():
    """_evaluate_rubric returns True when middleware accepts."""
    passing_rm = MagicMock(spec=RubricMiddleware)
    passing_rm.evaluate.return_value = RubricVerdict(passed=True, reason="Good.")

    ex = _make_executor(rubric_middleware=passing_rm)
    result = ex._evaluate_rubric(task_output="Good output.", task_context="skill")

    assert result is True


def test_no_rubric_middleware_evaluate_returns_true():
    """When no middleware configured, _evaluate_rubric must return True (pass-through)."""
    ex = _make_executor(rubric_middleware=None)
    result = ex._evaluate_rubric(task_output="Any output.", task_context="skill")

    assert result is True


# ── AD3: structural guard ────────────────────────────────────────────────────


def test_executor_has_evaluate_rubric_method():
    """CompoundExecutor must expose _evaluate_rubric() method."""
    ex = _make_executor()
    assert hasattr(ex, "_evaluate_rubric"), "_evaluate_rubric method missing"
    assert callable(ex._evaluate_rubric)


def test_executor_has_rubric_gated_accumulate_method():
    """CompoundExecutor must expose _rubric_gated_accumulate() method."""
    ex = _make_executor()
    assert hasattr(ex, "_rubric_gated_accumulate"), "_rubric_gated_accumulate method missing"
    assert callable(ex._rubric_gated_accumulate)
