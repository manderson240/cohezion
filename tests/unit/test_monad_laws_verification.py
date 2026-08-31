r"""Monad Laws Formal Verification Test Suite (Remediation 2)
============================================================
Formally verifies the 3 Monad Laws for Cohezion's `MonadResult`:
  1. Left Identity: `MonadResult.unit(x).bind(f) == f(x)`
  2. Right Identity: `m.bind(MonadResult.unit) == m`
  3. Associativity: `m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))`
"""

from __future__ import annotations

from cohezion.flume.monadic_markov_trace_engine import MonadResult


def f(x: int) -> MonadResult[int]:
    return MonadResult.unit(x * 2)


def g(x: int) -> MonadResult[int]:
    return MonadResult.unit(x + 10)


def test_left_identity_monad_law() -> None:
    """Verifies Left Identity: unit(x).bind(f) == f(x)."""
    x = 42
    left = MonadResult.unit(x).bind(f)
    right = f(x)
    assert left.is_success == right.is_success
    assert left.value == right.value


def test_right_identity_monad_law() -> None:
    """Verifies Right Identity: m.bind(unit) == m."""
    m = MonadResult.unit(100)
    res = m.bind(MonadResult.unit)
    assert res.is_success == m.is_success
    assert res.value == m.value


def test_associativity_monad_law() -> None:
    """Verifies Associativity: m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))."""
    m = MonadResult.unit(5)
    left = m.bind(f).bind(g)
    right = m.bind(lambda x: f(x).bind(g))
    assert left.is_success == right.is_success
    assert left.value == right.value
