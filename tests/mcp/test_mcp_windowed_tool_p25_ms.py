"""Item 1010: get_windowed_tool_p25_ms() — per-tool 25th-percentile latency.

get_windowed_tool_p25_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

Named convenience alias for get_windowed_latency_percentile(tool_name, 25.0, window_ms, ...).
Completes the p25/p50/p75/p95/p99 named-percentile quintet.
p25 is the lower quartile; IQR = p75 - p25.

Discriminating tests:
  1. PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8) -> 42.5
       idx=25/100*(8-1)=1.75 -> 20+0.75*(50-20)=42.5
       (kills floor=20.0; kills ceil=50.0; correct interpolated=42.5)
  2. ORDER CONSTRAINT: p25 <= p50 <= p75 for any non-empty window.
  3. Consistent with get_windowed_latency_percentile(tool, 25.0, ...).
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_p25_ms,
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
    """PRIMARY DISC.: n=8 lats [10,20,50,100,200,300,500,1000] -> p25=42.5.

    idx = 0.25 * (8-1) = 1.75
    sorted[1] = 20, sorted[2] = 50
    interpolated = 20 + 0.75 * (50 - 20) = 42.5

    Kills floor=20.0 (int index, no interpolation).
    Kills ceil=50.0 (rounding up to next value).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 50.0, 100.0, 200.0, 300.0, 500.0, 1000.0]:
        _add(store, "p25_t", lat, ts)

    result = get_windowed_tool_p25_ms("p25_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 42.5) < 1e-9, (
        f"n=8: idx=1.75 -> 20+0.75*30=42.5; kills floor=20.0 or ceil=50.0; got {result}"
    )


def test_consistent_with_percentile_25() -> None:
    """p25_ms == get_windowed_latency_percentile(tool, 25.0, ...)."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 30.0, 50.0, 70.0, 90.0]:
        _add(store, "p25_c", lat, ts)

    direct = get_windowed_tool_p25_ms("p25_c", WINDOW_MS, store=store, now_ms=NOW_MS)
    via_pct = get_windowed_latency_percentile("p25_c", 25.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(direct - via_pct) < 1e-9, (
        f"p25_ms={direct} must equal percentile(25.0)={via_pct}"
    )


def test_order_constraint_p25_lte_p75() -> None:
    """p25 <= p75 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p75_ms
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "p25_ord", lat, ts)

    p25 = get_windowed_tool_p25_ms("p25_ord", WINDOW_MS, store=store, now_ms=NOW_MS)
    p75 = get_windowed_tool_p75_ms("p25_ord", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert p25 <= p75, f"p25={p25} must be <= p75={p75}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_p25_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not affect p25."""
    store: dict = {}
    for _ in range(5):
        _add(store, "p25_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "p25_old", lat, _recent())

    result = get_windowed_tool_p25_ms("p25_old", WINDOW_MS, store=store, now_ms=NOW_MS)
    # p25 of [10,20,30,40,50]: idx=0.25*4=1.0 -> 20.0
    assert abs(result - 20.0) < 1e-9, (
        f"Old excluded; p25([10,20,30,40,50])=20.0; got {result}"
    )


def test_returns_float() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "p25_rt", lat, _recent())
    result = get_windowed_tool_p25_ms("p25_rt", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
