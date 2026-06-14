"""Item 1008: get_windowed_tool_p75_ms() — per-tool 75th-percentile latency.

get_windowed_tool_p75_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

Named convenience alias for get_windowed_latency_percentile(tool_name, 75.0, window_ms, ...).
Completes the named-percentile quartet (p50/p75/p95/p99).

Discriminating tests:
  1. PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8) -> 350.0
       idx=75/100*(8-1)=5.25 -> 300+0.25*(500-300)=350.0
       (kills floor=300.0; kills ceil=500.0; correct interpolated=350.0)
  2. ORDER CONSTRAINT: p75 >= p50 >= p25 for any non-empty window.
  3. Consistent with get_windowed_latency_percentile(tool, 75.0, ...).
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_p75_ms,
    get_windowed_latency_percentile,
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


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_interpolated_not_floor_not_ceil_primary_discriminator() -> None:
    """PRIMARY DISC.: n=8 lats [10,20,50,100,200,300,500,1000] -> p75=350.0.

    idx = 0.75 * (8-1) = 5.25
    sorted[5] = 300, sorted[6] = 500
    interpolated = 300 + 0.25 * (500 - 300) = 350.0

    Kills floor=300.0 (int index, no interpolation).
    Kills ceil=500.0 (rounding up to next value).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 50.0, 100.0, 200.0, 300.0, 500.0, 1000.0]:
        _add(store, "p75_t", lat, ts)

    result = get_windowed_tool_p75_ms("p75_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 350.0) < 1e-9, (
        f"n=8: idx=5.25 -> 300+0.25*200=350.0; kills floor=300.0 or ceil=500.0; got {result}"
    )


def test_consistent_with_percentile_75() -> None:
    """p75_ms == get_windowed_latency_percentile(tool, 75.0, ...)."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 30.0, 50.0, 70.0, 90.0]:
        _add(store, "p75_c", lat, ts)

    direct = get_windowed_tool_p75_ms("p75_c", WINDOW_MS, store=store, now_ms=NOW_MS)
    via_pct = get_windowed_latency_percentile("p75_c", 75.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(direct - via_pct) < 1e-9, f"p75_ms={direct} must equal percentile(75.0)={via_pct}"


def test_order_constraint_p75_gte_p50() -> None:
    """p75 >= p50 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p50_ms

    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "p75_ord", lat, ts)

    p75 = get_windowed_tool_p75_ms("p75_ord", WINDOW_MS, store=store, now_ms=NOW_MS)
    p50 = get_windowed_tool_p50_ms("p75_ord", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert p75 >= p50, f"p75={p75} must be >= p50={p50}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_p75_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not affect p75."""
    store: dict = {}
    for _ in range(5):
        _add(store, "p75_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "p75_old", lat, _recent())

    result = get_windowed_tool_p75_ms("p75_old", WINDOW_MS, store=store, now_ms=NOW_MS)
    # p75 of [10,20,30,40,50]: idx=0.75*4=3.0 -> 40.0
    assert abs(result - 40.0) < 1e-9, f"Old excluded; p75([10,20,30,40,50])=40.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "p75_rt", lat, _recent())
    result = get_windowed_tool_p75_ms("p75_rt", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
