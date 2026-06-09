"""Item 990: get_windowed_tool_p50_ms() -- per-tool p50 (median) latency shortcut.

get_windowed_tool_p50_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

Convenience shortcut for get_windowed_latency_percentile(tool, 50, ...).
0.0 for unknown tool or no recent calls.
Consistent with get_windowed_latency_percentile(tool, 50, ...).

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 20, 30, 40, 90] -> p50=30.0
     (kills mean=38.0; asymmetric dist ensures p50 != mean).
  2. Even-count interpolation: [10, 20, 30, 40] -> idx=1.5 -> 25.0.
  3. Consistent with get_windowed_latency_percentile(tool, 50, ...).
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_latency_percentile,
    get_windowed_tool_p50_ms,
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


def test_p50_not_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: p50=30.0 for [10,20,30,40,90] (mean=38.0 would be wrong).

    Asymmetric distribution: mean=(10+20+30+40+90)/5=38.0 != p50=30.0.
    idx = 0.50*(5-1) = 2.0 -> sorted[2] = 30.0.
    Kills impl returning mean (38.0) or max (90.0).
    """
    store: dict = {}
    ts = _recent()
    for lat in [90.0, 20.0, 10.0, 40.0, 30.0]:  # unsorted insertion
        _add(store, "t", lat, ts)

    result = get_windowed_tool_p50_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, (
        f"p50([10,20,30,40,90])=30.0; kills mean=38.0 or max=90.0; got {result}"
    )


def test_even_count_interpolation() -> None:
    """Even-count: [10, 20, 30, 40] -> idx=1.5 -> 20 + 0.5*10 = 25.0."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "t", lat, ts)

    result = get_windowed_tool_p50_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 25.0) < 1e-9, (
        f"p50([10,20,30,40]): idx=1.5 -> 25.0; got {result}"
    )


def test_consistent_with_latency_percentile() -> None:
    """Must equal get_windowed_latency_percentile(tool, 50.0, ...)."""
    store: dict = {}
    ts = _recent()
    for lat in [5.0, 15.0, 25.0, 35.0, 45.0, 80.0]:
        _add(store, "t", lat, ts)

    shortcut = get_windowed_tool_p50_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_latency_percentile("t", 50.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(shortcut - full) < 1e-9, (
        f"shortcut={shortcut} must equal latency_percentile(50)={full}"
    )


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_p50_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Latencies outside the window must not affect p50."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 9999.0, _old())   # huge old latencies
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "t", lat, _recent())

    result = get_windowed_tool_p50_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 20.0) < 1e-9, (
        f"Old excluded; p50([10,20,30])=20.0; got {result}"
    )


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_tool_p50_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
