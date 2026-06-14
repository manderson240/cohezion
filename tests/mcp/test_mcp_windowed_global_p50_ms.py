"""Item 994: get_windowed_global_p50_ms() -- fleet-wide p50 (median) latency.

get_windowed_global_p50_ms(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent latencies from all tools and computes the 50th percentile.
Fleet-wide dual of get_windowed_tool_p50_ms (item 990).
PRE-COVERED from item 956 (line 1301 in compound_mcp_telemetry.py).
These are supplemental discriminating tests.

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10,50] + tool_b [20,30]
       -> pooled [10,20,30,50] idx=0.5*3=1.5, p50=20+0.5*(30-20)=25.0
       (kills mean=27.5; kills avg-of-per-tool-p50=(30+25)/2=27.5).
  2. Consistent with get_windowed_global_latency_percentile(50.0, ...).
  3. Empty store -> 0.0.
  4. Old calls excluded.
  5. Returns float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_latency_percentile,
    get_windowed_global_p50_ms,
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


def test_pooled_p50_not_mean_not_avg_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled p50 != mean and != avg(per-tool p50).

    tool_a: [10, 50] -> p50_a = 30.0, mean_a = 30.0
    tool_b: [20, 30] -> p50_b = 25.0, mean_b = 25.0
    avg-of-per-tool-p50 = (30.0 + 25.0) / 2 = 27.5  (WRONG -- coincides with mean)
    pooled [10,20,30,50]: idx=0.5*3=1.5, p50=20+0.5*(30-20)=25.0  (CORRECT)

    25.0 != 27.5 -- kills avg-of-per-tool-p50.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts)
    _add(store, "tool_a", 50.0, ts)
    _add(store, "tool_b", 20.0, ts)
    _add(store, "tool_b", 30.0, ts)

    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 25.0) < 1e-9, (
        f"pooled p50=25.0; kills avg-of-per-tool=27.5 or mean=27.5; got {result}"
    )


def test_consistent_with_global_latency_percentile() -> None:
    """Must equal get_windowed_global_latency_percentile(50.0, ...)."""
    store: dict = {}
    ts = _recent()
    for tool, lats in [("a", [5.0, 15.0, 25.0, 35.0]), ("b", [45.0, 80.0])]:
        for lat in lats:
            _add(store, tool, lat, ts)

    shortcut = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_global_latency_percentile(50.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(shortcut - full) < 1e-9, (
        f"global_p50={shortcut} must equal global_latency_percentile(50)={full}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_p50_ms(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old latencies outside the window must not pollute p50."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0]:
        _add(store, "t", lat, _recent())

    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    # [10,20,30,40]: idx=0.5*3=1.5 -> 20+0.5*10=25.0
    assert abs(result - 25.0) < 1e-9, f"Old excluded; p50([10,20,30,40])=25.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_global_p50_ms(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
