"""Item 1023: get_windowed_tool_latency_above_budget_ms() — excess latency above SLA.

get_windowed_tool_latency_above_budget_ms(
    tool_name, window_ms, budget_ms, *, store=None, now_ms=None
) -> float

Sum of max(0, latency_ms - budget_ms) for all calls in window.
0.0 for no calls or all below budget.
Measures cumulative latency "debt" above SLA in the window.

Discriminating tests:
  1. PRIMARY DISC.: lats [50, 150, 300] budget=100 -> excess=[0, 50, 200], sum=250.0
       (kills count_above=2 int; kills sum_all=500.0 float; correct excess_sum=250.0)
  2. All below budget -> 0.0 (not negative)
  3. All above budget -> sum of (lat - budget) for each
  4. Exactly at budget -> 0.0 (not strictly above -> no excess)
  5. Old calls excluded
  6. Unknown tool -> 0.0
  7. Returns float (not int)
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_latency_above_budget_ms,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent(offset: float = 0.0) -> float:
    return NOW_MS - 500.0 + offset


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_excess_sum_not_count_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [50, 150, 300] budget=100 -> excess_sum=250.0.

    Kills impl returning count_above_budget=2 (int).
    Kills impl returning sum_all_lats=500.0 (float).
    Kills impl returning max_excess=200.0 (float).
    """
    store: dict = {}
    for i, lat in enumerate([50.0, 150.0, 300.0]):
        _add(store, "ab_t", lat, _recent(float(i)))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_t", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )

    assert isinstance(result, float)
    assert abs(result - 250.0) < 1e-9, (
        f"excess_sum=250.0; kills count=2 or sum_all=500; got {result}"
    )


def test_all_below_budget_returns_zero() -> None:
    """All latencies below budget -> 0.0 (no excess, not negative)."""
    store: dict = {}
    for i, lat in enumerate([10.0, 20.0, 50.0]):
        _add(store, "ab_below", lat, _recent(float(i)))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_below", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"All below budget -> 0.0; got {result}"


def test_at_budget_is_zero_excess() -> None:
    """Latency exactly equal to budget -> 0.0 excess (not strictly above budget)."""
    store: dict = {}
    _add(store, "ab_eq", 100.0, _recent(0.0))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_eq", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"lat==budget -> 0.0 excess; got {result}"


def test_all_above_budget() -> None:
    """All latencies above budget -> sum of individual excesses."""
    store: dict = {}
    # lats [200, 300] budget=100 -> excess=[100, 200] -> sum=300.0
    for i, lat in enumerate([200.0, 300.0]):
        _add(store, "ab_all", lat, _recent(float(i)))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_all", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert abs(result - 300.0) < 1e-9, f"All above: sum excess=300.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    result = get_windowed_tool_latency_above_budget_ms(
        "no_such", WINDOW_MS, 100.0, store={}, now_ms=NOW_MS
    )
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not contribute to excess sum."""
    store: dict = {}
    # Old calls with huge latency — must be excluded
    for _ in range(5):
        _add(store, "ab_old", 999999.0, _old())
    # Recent calls all below budget
    for i in range(3):
        _add(store, "ab_old", 50.0, _recent(float(i)))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_old", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"Old excluded; recent below budget -> 0.0; got {result}"


def test_returns_float_not_int() -> None:
    """Return type must be float even for integer-valued excess."""
    store: dict = {}
    _add(store, "ab_rt", 200.0, _recent(0.0))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_rt", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, float), f"Must return float; got {type(result)}"


def test_mixed_above_below_budget() -> None:
    """Mixed lats: only excess from above-budget calls counted."""
    store: dict = {}
    # lats [20, 80, 120, 200] budget=100 -> excess=[0, 0, 20, 100] -> sum=120.0
    for i, lat in enumerate([20.0, 80.0, 120.0, 200.0]):
        _add(store, "ab_mix", lat, _recent(float(i)))

    result = get_windowed_tool_latency_above_budget_ms(
        "ab_mix", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert abs(result - 120.0) < 1e-9, f"Mixed: excess_sum=120.0; got {result}"
