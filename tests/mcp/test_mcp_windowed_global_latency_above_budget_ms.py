"""Item 1024: get_windowed_global_latency_above_budget_ms() — fleet-wide excess latency.

get_windowed_global_latency_above_budget_ms(
    window_ms, budget_ms, *, store=None, now_ms=None
) -> float

Fleet-wide sum of max(0, lat - budget_ms) pooled across ALL tools in window.
0.0 for empty. Fleet-wide dual of item-1023 (per-tool budget excess).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [50,150] + tool_b [200,300] budget=100
       -> excess=[0,50]+[100,200] -> global=350.0
       (kills per-tool-a=50.0; kills per-tool-b=300.0; correct pooled=350.0)
  2. Empty store -> 0.0
  3. All below budget -> 0.0
  4. Old calls excluded
  5. Returns float
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_above_budget_ms,
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


def test_pooled_not_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a [50,150] + tool_b [200,300] budget=100 -> 350.0.

    Kills per-tool-a excess = 50.0.
    Kills per-tool-b excess = 300.0.
    Kills max-per-tool = 300.0.
    """
    store: dict = {}
    for i, lat in enumerate([50.0, 150.0]):
        _add(store, "gab_a", lat, _recent(float(i)))
    for i, lat in enumerate([200.0, 300.0]):
        _add(store, "gab_b", lat, _recent(float(i + 2)))

    result = get_windowed_global_latency_above_budget_ms(
        WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )

    assert isinstance(result, float)
    # tool_a: max(0,50-100)+max(0,150-100) = 0+50 = 50
    # tool_b: max(0,200-100)+max(0,300-100) = 100+200 = 300
    # total: 50 + 300 = 350
    assert abs(result - 350.0) < 1e-9, (
        f"pooled_excess=350.0; kills per-tool-a=50.0 or per-tool-b=300.0; got {result}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_latency_above_budget_ms(
        WINDOW_MS, 100.0, store={}, now_ms=NOW_MS
    )
    assert result == 0.0


def test_all_below_budget_returns_zero() -> None:
    """All latencies at or below budget -> 0.0."""
    store: dict = {}
    for i, lat in enumerate([10.0, 50.0, 100.0]):
        _add(store, "gab_low", lat, _recent(float(i)))

    result = get_windowed_global_latency_above_budget_ms(
        WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"All at/below budget -> 0.0; got {result}"


def test_old_calls_excluded() -> None:
    """Old calls outside window must not contribute to excess."""
    store: dict = {}
    for _ in range(5):
        _add(store, "gab_old", 99999.0, _old())
    # Recent call below budget
    _add(store, "gab_old", 50.0, _recent(0.0))

    result = get_windowed_global_latency_above_budget_ms(
        WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0.0, f"Old excluded; recent below budget -> 0.0; got {result}"


def test_returns_float_not_int() -> None:
    store: dict = {}
    _add(store, "gab_rt", 200.0, _recent(0.0))

    result = get_windowed_global_latency_above_budget_ms(
        WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, float)
