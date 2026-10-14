"""Unit tests for JAZ: Harness as a Language (arXiv:2609.26891)."""

from __future__ import annotations

import pytest

from cohezion.compound.jaz_primitive import (
    BudgetPool,
    ContextWindowWarning,
    ReturnType,
    ValidateReturn,
    invoke,
    scope,
)


def test_basic_invoke():
    """Verify basic invoke returns expected output."""
    res = invoke(task="Calculate 2 + 2", answer=4)
    assert res == 4


def test_dynamic_scoping():
    """Verify dynamic scoping passes tools down recursive calls."""
    def multiply_by_two(x: int) -> int:
        return x * 2

    with scope(mult=multiply_by_two, multiplier_factor=2):
        # Top level invoke uses scoped variable
        code_str = "result = mult(10)"
        res = invoke(code=code_str)
        assert res == 20


def test_recursive_sub_invokes_and_history():
    """Verify sub-invokes and tail-recursive delegation passing __history__."""
    # A recursive function that counts down to 0 via invoke
    def countdown(n: int, __history__: list) -> int:
        __history__.append(f"step_{n}")
        if n <= 1:
            return 1
        # Recursive sub-invoke
        return invoke(
            func=countdown,
            n=n - 1,
            __history__=__history__,
        )

    hist: list = []
    res = invoke(func=countdown, n=5, __history__=hist)
    assert res == 1
    # 5 steps from countdown + 5 func_call entries from invoke
    assert len(hist) == 10
    user_steps = [x for x in hist if isinstance(x, str) and x.startswith("step_")]
    assert user_steps == ["step_5", "step_4", "step_3", "step_2", "step_1"]
    func_calls = [x for x in hist if isinstance(x, dict) and x.get("type") == "func_call"]
    assert len(func_calls) == 5


def test_hook_return_type():
    """Verify ReturnType hook enforces and coerces types."""
    res = invoke(ReturnType(float), answer="3.1415")
    assert isinstance(res, float)
    assert pytest.approx(res) == 3.1415

    with pytest.raises(TypeError):
        invoke(ReturnType(int), answer="not_a_number")


def test_hook_validate_return():
    """Verify ValidateReturn rejects invalid outputs."""
    with pytest.raises(ValueError, match="must be positive"):
        invoke(
            ValidateReturn(lambda x: x > 0, error_message="must be positive"),
            answer=-10,
        )

    res = invoke(
        ValidateReturn(lambda x: x > 0, error_message="must be positive"),
        answer=42,
    )
    assert res == 42


def test_hook_budget_pool():
    """Verify BudgetPool limits total invocation costs."""
    pool = BudgetPool(max_cost=0.03)

    with scope(pool):
        # 1st call: cost 0.01 -> ok
        invoke(task="step 1")
        # 2nd call: cost 0.02 -> ok
        invoke(task="step 2")
        # 3rd call: cost 0.03 -> ok
        invoke(task="step 3")
        # 4th call: cost 0.04 -> raises
        with pytest.raises(RuntimeError, match="BudgetPool exhausted"):
            invoke(task="step 4")


def test_context_window_warning_and_delegation():
    """Verify ContextWindowWarning triggers warning flag when history exceeds limit."""
    history = [{"turn": i} for i in range(15)]
    warn_hook = ContextWindowWarning(max_history_turns=10)

    env = {"__history__": history}
    warn_hook.on_invoke_start(env)
    assert env.get("__context_warning__") is True
