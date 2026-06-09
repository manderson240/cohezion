"""Item 1025: get_windowed_tool_above_budget_call_rate() — SLA breach rate.

get_windowed_tool_above_budget_call_rate(
    tool_name, window_ms, budget_ms, *, store=None, now_ms=None
) -> float

Fraction of calls exceeding budget_ms in window: above_count / total_count.
0.0 for unknown/empty. Complements item-1023 (excess sum) with a rate view.

Discriminating tests:
  1. PRIMARY DISC.: lats [50, 150, 200, 300] budget=100 -> 3 of 4 above -> 0.75
       (kills count=3 int; kills excess_sum=350.0 float; kills total_count=4 int)
  2. None above budget -> 0.0 rate (not negative)
  3. All above budget -> 1.0 rate
  4. Exactly at budget -> not above (not counted)
  5. No calls -> 0.0
  6. Returns float
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_above_budget_call_rate,
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


def test_rate_not_count_not_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [50, 150, 200, 300] budget=100 -> rate=0.75.

    Kills impl returning count_above=3 (int).
    Kills impl returning excess_sum=350.0 (float).
    Kills impl returning total_count=4 (int).
    """
    store: dict = {}
    for i, lat in enumerate([50.0, 150.0, 200.0, 300.0]):
        _add(store, "abr_t", lat, _recent(float(i)))

    result = get_windowed_tool_above_budget_call_rate(
        "abr_t", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )

    assert isinstance(result, float)
    assert abs(result - 0.75) < 1e-9, (
        f"rate=0.75; kills count=3 or excess_sum=350.0; got {result}"
    )


def test_none_above_budget_returns_zero() -> None:
    """All latencies at or below budget -> rate=0.0."""
    store: dict = {}
    for i, lat in enumerate([10.0, 50.0, 100.0]):
        _add(store, "abr_low", lat, _recent(float(i)))

    result = get_windowed_tool_above_budget_call_rate(
        "abr_low", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"None above budget -> 0.0; got {result}"


def test_all_above_budget_returns_one() -> None:
    """All calls above budget -> rate=1.0."""
    store: dict = {}
    for i, lat in enumerate([200.0, 300.0, 400.0]):
        _add(store, "abr_all", lat, _recent(float(i)))

    result = get_windowed_tool_above_budget_call_rate(
        "abr_all", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert abs(result - 1.0) < 1e-9, f"All above -> 1.0; got {result}"


def test_at_budget_not_counted_as_above() -> None:
    """Latency exactly equal to budget -> not counted as above budget."""
    store: dict = {}
    _add(store, "abr_eq", 100.0, _recent(0.0))  # exactly at budget
    _add(store, "abr_eq", 50.0, _recent(1.0))   # below budget

    result = get_windowed_tool_above_budget_call_rate(
        "abr_eq", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"Both at/below budget -> 0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_above_budget_call_rate(
        "no_such", WINDOW_MS, 100.0, store={}, now_ms=NOW_MS
    )
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls must not affect rate."""
    store: dict = {}
    # Old calls all above budget — must be excluded
    for _ in range(5):
        _add(store, "abr_old", 999.0, _old())
    # Recent calls all below budget
    for i in range(3):
        _add(store, "abr_old", 50.0, _recent(float(i)))

    result = get_windowed_tool_above_budget_call_rate(
        "abr_old", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"Old excluded; recent all below budget -> 0.0; got {result}"


def test_returns_float_not_int() -> None:
    store: dict = {}
    _add(store, "abr_rt", 200.0, _recent(0.0))
    _add(store, "abr_rt", 50.0, _recent(1.0))

    result = get_windowed_tool_above_budget_call_rate(
        "abr_rt", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, float), f"Must return float; got {type(result)}"
