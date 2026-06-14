"""Item 968: get_windowed_latency_percentile() -- arbitrary-percentile windowed latency.

get_windowed_latency_percentile(tool_name, percentile, window_ms, *, store=None, now_ms=None)
    -> float

Generalizes p50/p95 to ANY percentile in [0, 100].
Returns 0.0 for unknown tool or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 5 calls [10,20,30,40,50], percentile=80 -> 46.0
     (kills impl always returning p50; kills impl returning p100=50 without interpolation).
  2. percentile=50 agrees with get_windowed_tool_telemetry_full() p50_ms.
  3. percentile=95 agrees with p95.
  4. 0 recent calls -> 0.0.
  5. Unknown tool -> 0.0.
  6. Returns float.
  7. Old calls excluded.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_latency_percentile,
    get_windowed_tool_telemetry_full,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lats: list[float], ts: float) -> None:
    for lat in lats:
        store.setdefault(tool, []).append((ts, lat, True))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_p80_interpolated_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50], percentile=80 -> 42.0 (linear interpolation).

    _percentile uses idx=(p/100)*(n-1): 0.8*4=3.2 -> 40 + 0.2*(50-40) = 42.0.
    Kills impl always returning p50 (=30.0); kills impl returning sorted[-1]=50.0.
    """
    store: dict = {}
    _add(store, "t", [10.0, 20.0, 30.0, 40.0, 50.0], _recent())

    result = get_windowed_latency_percentile("t", 80.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 42.0) < 1e-6, (
        f"p80 of [10,20,30,40,50] = 42.0 (0.8*4=3.2 -> interp); got {result}"
    )


def test_p50_matches_windowed_full_profile() -> None:
    """percentile=50 must agree with get_windowed_tool_telemetry_full().p50_ms."""
    store: dict = {}
    _add(store, "t", [10.0, 20.0, 30.0, 40.0, 50.0], _recent())

    p50_direct = get_windowed_latency_percentile("t", 50.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    p50_from_full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)[
        "p50_ms"
    ]

    assert abs(p50_direct - p50_from_full) < 1e-9, (
        f"p50_direct={p50_direct} != p50_from_full={p50_from_full}"
    )


def test_p95_matches_windowed_full_profile() -> None:
    """percentile=95 must agree with get_windowed_tool_telemetry_full().p95_ms."""
    store: dict = {}
    _add(store, "t", [10.0, 20.0, 30.0, 40.0, 50.0], _recent())

    p95_direct = get_windowed_latency_percentile("t", 95.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    p95_from_full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)[
        "p95_ms"
    ]

    assert abs(p95_direct - p95_from_full) < 1e-9, (
        f"p95_direct={p95_direct} != p95_from_full={p95_from_full}"
    )


def test_no_recent_calls_returns_zero() -> None:
    result = get_windowed_latency_percentile("unknown", 50.0, WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Calls outside window must not affect the percentile."""
    store: dict = {}
    _add(store, "t", [1000.0], _old())  # huge latency, outside window
    _add(store, "t", [10.0], _recent())  # only this should count

    result = get_windowed_latency_percentile("t", 50.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 10.0) < 1e-9, f"Only recent call matters; p50=10.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", [25.0], _recent())
    result = get_windowed_latency_percentile("t", 50.0, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float)
