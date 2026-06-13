"""Discriminating tests for BudgetEnforcer (V-model audit, iter 7, 2026-06-05).

BudgetEnforcer is the main public class of `cost_optimization` (the #1 test-debt
module — 16 external importers). These tests pin the policy/threshold boundaries and
the circuit-breaker integration, each written to fail a plausible wrong impl
(over-eager blocking, policy ignored, div-by-zero, no breaker escalation).

Status bands (budget=100): <80 OK · [80,90) WARNING · [90,95) CRITICAL ·
[95,100) EXTREME · >=100 BLOCKED.
"""

from __future__ import annotations

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer, BudgetPolicy


def test_under_budget_proceeds() -> None:
    enf = BudgetEnforcer(budget_usd=100.0)
    ok, _ = enf.check_budget(50.0)
    assert ok is True


def test_soft_stop_blocks_only_at_or_over_100pct_not_at_extreme() -> None:
    # Discriminates over-eager blocking: SOFT_STOP must still PROCEED at 99% (EXTREME),
    # and only block at >=100% (BLOCKED).
    enf = BudgetEnforcer(budget_usd=100.0, policy=BudgetPolicy.SOFT_STOP)
    assert enf.check_budget(99.0)[0] is True  # EXTREME -> still allowed
    enf.reset()
    blocked, reason = enf.check_budget(100.0)  # BLOCKED -> denied
    assert blocked is False and "exceeded" in reason.lower()


def test_warning_only_never_blocks_even_far_over_budget() -> None:
    # Discriminates a policy-ignoring impl: WARNING_ONLY must allow 500% utilization.
    enf = BudgetEnforcer(budget_usd=100.0, policy=BudgetPolicy.WARNING_ONLY)
    assert enf.check_budget(500.0)[0] is True


def test_hard_stop_blocks_at_critical_where_soft_stop_would_allow() -> None:
    # Discriminates SOFT vs HARD policy: at 92% (CRITICAL) HARD_STOP denies, SOFT allows.
    hard = BudgetEnforcer(budget_usd=100.0, policy=BudgetPolicy.HARD_STOP)
    soft = BudgetEnforcer(budget_usd=100.0, policy=BudgetPolicy.SOFT_STOP)
    assert hard.check_budget(92.0)[0] is False
    assert soft.check_budget(92.0)[0] is True


def test_zero_budget_does_not_divide_by_zero() -> None:
    # Discriminates a missing guard: budget 0 must not raise ZeroDivisionError.
    enf = BudgetEnforcer(budget_usd=0.0)
    ok, _ = enf.check_budget(10.0)
    assert isinstance(ok, bool)
    assert enf.get_budget_state(10.0).utilization_pct == 0


def test_get_budget_state_computes_utilization_and_remaining() -> None:
    state = BudgetEnforcer(budget_usd=100.0).get_budget_state(30.0)
    assert state.utilization_pct == 30.0
    assert state.remaining_budget_usd == 70.0
    assert state.status == "OK"


def test_repeated_soft_stop_blocks_trip_the_circuit_breaker() -> None:
    # Integration: 3 BLOCKED checks under SOFT_STOP record 3 violations -> breaker OPENS,
    # and the next check is denied with the breaker reason (not the budget reason).
    # Discriminates an impl that doesn't escalate repeated violations.
    enf = BudgetEnforcer(budget_usd=100.0, policy=BudgetPolicy.SOFT_STOP)
    for _ in range(3):
        assert enf.check_budget(150.0)[0] is False
    ok, reason = enf.check_budget(10.0)  # well under budget, but breaker is OPEN
    assert ok is False and "circuit breaker" in reason.lower()
