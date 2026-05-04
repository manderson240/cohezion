"""Tests for RetrospectionEngine HIHO balance metric (Task #15)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cohezion.core.compound.retrospection import RetrospectionEngine


@pytest.fixture()
def engine() -> RetrospectionEngine:
    return RetrospectionEngine()


def test_empty_history_returns_neutral(engine: RetrospectionEngine):
    """Empty execution history → 0.5 (neutral / HIHO equilibrium)."""
    assert engine.compute_hiho_balance([]) == 0.5


def test_all_positive_deltas_returns_one(engine: RetrospectionEngine):
    """All deltas positive → balance == 1.0."""
    history = [{"delta": 0.4}, {"delta": 1.0}, {"delta": 0.01}]
    assert engine.compute_hiho_balance(history) == 1.0


def test_all_non_positive_deltas_returns_zero(engine: RetrospectionEngine):
    """Zero or negative deltas → balance == 0.0 (none counted positive)."""
    history = [{"delta": -0.1}, {"delta": 0.0}, {"delta": -1.0}]
    assert engine.compute_hiho_balance(history) == 0.0


def test_mixed_history_returns_correct_fraction(engine: RetrospectionEngine):
    """Mixed deltas → fraction of strictly positive entries."""
    history = [
        {"delta": 1},
        {"delta": -1},
        {"delta": 0.5},
        {"delta": 0},  # zero is NOT positive
    ]
    # 2 of 4 are > 0 → 0.5
    assert engine.compute_hiho_balance(history) == pytest.approx(0.5)

    # Missing key defaults to 0 (non-positive).
    history_missing = [{"delta": 1}, {}, {"delta": 2}, {"other": 99}]
    assert engine.compute_hiho_balance(history_missing) == pytest.approx(0.5)


def test_analyze_includes_hiho_balance(engine: RetrospectionEngine):
    """analyze() and analyze_execution() must include 'hiho_balance'.

    Exercises both the spec'd entry point (``analyze``) and the
    underlying ``analyze_execution`` to lock in the alias contract.
    """
    # Build a fake execution report: 3 completed, 1 failed → balance 0.75.
    task_results = [
        SimpleNamespace(
            task_id=f"t{i}",
            status="completed" if i < 3 else "failed",
            execution=SimpleNamespace(total_tokens=10),
        )
        for i in range(4)
    ]
    report = SimpleNamespace(
        task_results=task_results,
        total_tokens=40,
        total_duration_ms=100,
        plan_name="test_plan",
    )

    # Spec requirement: analyze() carries the HIHO metric.
    result = engine.analyze(report)
    assert "hiho_balance" in result
    assert result["hiho_balance"] == pytest.approx(0.75)

    # And the underlying method behaves identically (alias contract).
    result_exec = engine.analyze_execution(report)
    assert result_exec["hiho_balance"] == pytest.approx(0.75)
