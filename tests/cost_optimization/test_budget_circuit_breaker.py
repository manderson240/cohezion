"""Discriminating tests for BudgetCircuitBreaker (V-model audit 2026-06-05).

`cost_optimization` was the codebase's #1 test-debt module (18 external importers,
26 public defs, 0 tests). BudgetCircuitBreaker is its highest-stakes logic — it
blocks runaway spend — so each test below is *discriminating*: written to FAIL the
most plausible wrong implementation (off-by-one strike count, inverted open/closed
return, no auto-reset), not merely to prove the method fires.
"""

from __future__ import annotations

import time

from cohezion.cost_optimization.budget_enforcer import BudgetCircuitBreaker


def test_opens_exactly_at_strike_limit_not_before() -> None:
    # Default 3-strike rule. Discriminates off-by-one: an impl that opens at 2 or 4 fails.
    cb = BudgetCircuitBreaker(strike_limit=3)
    assert cb.record_violation() is False and not cb.is_open  # strike 1
    assert cb.record_violation() is False and not cb.is_open  # strike 2
    assert cb.record_violation() is True and cb.is_open  # strike 3 -> OPEN


def test_record_violation_returns_true_whenever_at_or_past_limit() -> None:
    # ACTUAL contract (not the docstring's "opened"): returns True iff strike_count
    # >= strike_limit, so it stays True on calls past the limit. Discriminates an impl
    # that returns True only on the transition and False afterward.
    cb = BudgetCircuitBreaker(strike_limit=2)
    assert cb.record_violation() is False  # strike 1: below limit
    assert cb.record_violation() is True  # strike 2: reaches limit -> open
    assert cb.record_violation() is True  # strike 3: still at/past limit -> still True


def test_strike_limit_one_opens_immediately() -> None:
    # Discriminates a strict `>` (vs `>=`) bug: with limit=1 the first strike must open.
    cb = BudgetCircuitBreaker(strike_limit=1)
    assert cb.record_violation() is True and cb.is_open


def test_check_state_true_only_while_open() -> None:
    # check_state(): True == currently blocking. Discriminates an inverted return.
    cb = BudgetCircuitBreaker(strike_limit=1)
    assert cb.check_state() is False  # fresh -> not blocking
    cb.record_violation()
    assert cb.check_state() is True  # open -> blocking


def test_manual_reset_closes_and_clears_strikes() -> None:
    cb = BudgetCircuitBreaker(strike_limit=1)
    cb.record_violation()
    assert cb.is_open
    cb.reset()
    assert not cb.is_open and cb.strike_count == 0 and cb.check_state() is False


def test_auto_reset_after_timeout_elapses() -> None:
    # Discriminates a missing auto-reset: backdate open_time past reset_timeout_sec.
    cb = BudgetCircuitBreaker(strike_limit=1)
    cb.record_violation()
    assert cb.check_state() is True
    cb.open_time = time.time() - (cb.reset_timeout_sec + 1)
    assert cb.check_state() is False  # auto-reset
    assert not cb.is_open and cb.strike_count == 0
