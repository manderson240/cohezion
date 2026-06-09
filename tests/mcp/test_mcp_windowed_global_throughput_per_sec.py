"""Item 997: get_windowed_global_throughput_per_sec() — fleet-wide calls/sec.

get_windowed_global_throughput_per_sec(window_ms, *, store=None, now_ms=None) -> float

Pools ALL recent calls from all tools and computes fleet throughput (calls/sec).
Fleet-wide dual of get_windowed_tool_throughput_per_sec (item 996).

Discriminating tests:
  1. PRIMARY DISC.: tool_a 3 calls + tool_b 2 calls in 1000ms window
       -> total=5, fleet_tps = 5.0/sec
       (kills avg-of-per-tool = (3+2)/2 = 2.5/sec; kills max-per-tool = 3.0/sec).
  2. Single tool matches per-tool throughput.
  3. Empty store -> 0.0.
  4. Old calls excluded.
  5. Window-scaling: 10 calls in 2000ms -> 5.0/sec.
  6. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_throughput_per_sec,
    get_windowed_tool_throughput_per_sec,
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


def test_fleet_tps_not_avg_not_max_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled fleet tps != avg(per-tool tps) != max(per-tool tps).

    tool_a: 3 calls in 1000ms -> 3.0/sec
    tool_b: 2 calls in 1000ms -> 2.0/sec
    avg-of-per-tool = (3.0 + 2.0) / 2 = 2.5/sec   (WRONG)
    max-of-per-tool = 3.0/sec                       (WRONG)
    fleet = (3+2) / (1000/1000) = 5.0/sec           (CORRECT)

    Kills impl averaging per-tool rates.
    Kills impl taking max per-tool rate.
    """
    store: dict = {}
    window_ms = 1_000.0
    ts = NOW_MS - 100.0
    for _ in range(3):
        _add(store, "gt_a", 1.0, ts)
    for _ in range(2):
        _add(store, "gt_b", 1.0, ts)

    result = get_windowed_global_throughput_per_sec(window_ms, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 5.0) < 1e-9, (
        f"fleet tps=5.0; kills avg=2.5 or max-per-tool=3.0; got {result}"
    )
    # not avg-of-per-tool
    assert abs(result - 2.5) > 1.0, "Should not be avg of per-tool rates"
    # not max-per-tool
    assert abs(result - 3.0) > 1.0, "Should not be max per-tool rate"


def test_single_tool_matches_per_tool_throughput() -> None:
    """With one tool, global throughput == per-tool throughput."""
    store: dict = {}
    ts = _recent()
    for _ in range(4):
        _add(store, "gt_single", 1.0, ts)

    global_tps = get_windowed_global_throughput_per_sec(WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool = get_windowed_tool_throughput_per_sec(
        "gt_single", WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert abs(global_tps - per_tool) < 1e-9, (
        f"single-tool: global_tps={global_tps} must equal per_tool_tps={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_throughput_per_sec(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Old calls outside window must not contribute to fleet tps."""
    store: dict = {}
    for _ in range(100):
        _add(store, "gt_old", 1.0, _old())
    # 4 recent calls in 10s window -> 4/10 = 0.4/sec
    for _ in range(4):
        _add(store, "gt_old", 1.0, _recent())

    result = get_windowed_global_throughput_per_sec(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 0.4) < 1e-9, (
        f"4 recent/10s=0.4/sec; old excluded; got {result}"
    )


def test_window_scaling() -> None:
    """10 calls in 2000ms window -> 5.0/sec."""
    store: dict = {}
    window_ms = 2_000.0
    ts = NOW_MS - 100.0
    for _ in range(10):
        _add(store, "gt_scale", 1.0, ts)

    result = get_windowed_global_throughput_per_sec(window_ms, store=store, now_ms=NOW_MS)
    assert abs(result - 5.0) < 1e-9, (
        f"10 calls/2s = 5.0/sec; got {result}"
    )


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "gt_float", 1.0, _recent())
    result = get_windowed_global_throughput_per_sec(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
