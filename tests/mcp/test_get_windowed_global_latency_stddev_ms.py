"""Item 983: get_windowed_global_latency_stddev_ms(window_ms, *, store=None, now_ms=None) -> float
-- population standard deviation of ALL windowed latencies fleet-wide.

PRIMARY DISC.: tool_a [10] + tool_b [10, 10, 90] -> pooled [10,10,10,90]
  population stddev = sqrt(((10-30)^2 + (10-30)^2 + (10-30)^2 + (90-30)^2)/4)
                    = sqrt((400+400+400+3600)/4) = sqrt(4800/4) = sqrt(1200) ≈ 34.641
  NOT per-tool stddev avg: (0 + sqrt((20/3)*2/2)) complicated; kills per-tool avg approach.
  NOT per-tool mean avg: (10 + 36.67)/2 = 23.33 (already tested in item 978 pool fixture).
empty -> 0.0; single call fleet-wide -> 0.0; all-same -> 0.0; returns float.
"""
from __future__ import annotations

import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_stddev_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a [10] + tool_b [10,10,90] -> pooled stddev≈34.641 (NOT per-tool avg)."""
    _reset()
    store = _make_store({
        "gsd_a": [(_NOW - 10, 10.0, True)],
        "gsd_b": [(_NOW - 10, 10.0, True), (_NOW - 10, 10.0, True), (_NOW - 10, 90.0, True)],
    })
    result = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # pooled [10,10,10,90]: mean=30, var=((10-30)^2*3+(90-30)^2)/4=(400*3+3600)/4=4800/4=1200
    expected = math.sqrt(1200.0)   # ≈ 34.641
    assert abs(result - expected) < 0.001


def test_single_fleet_call_returns_zero() -> None:
    """Single call across fleet -> stddev=0.0."""
    store = _make_store({"gsd_single": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)) < 0.001


def test_all_same_latency_returns_zero() -> None:
    """All calls at same latency -> stddev=0.0."""
    store = _make_store({
        "gsd_s1": [(_NOW - 10, 20.0, True)] * 3,
        "gsd_s2": [(_NOW - 10, 20.0, True)] * 2,
    })
    assert abs(get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)) < 0.001


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_stddev_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "gsd_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_two_calls_stddev() -> None:
    """Two calls across fleet (possibly different tools): |a-b|/2."""
    store = _make_store({
        "gsd_t1": [(_NOW - 10, 10.0, True)],
        "gsd_t2": [(_NOW - 10, 30.0, True)],
    })
    result = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    # mean=20, var=((10-20)^2+(30-20)^2)/2=100, stddev=10.0
    assert abs(result - 10.0) < 0.001


def test_single_tool_equals_per_tool_stddev() -> None:
    """With a single tool, global stddev == per-tool stddev."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_latency_stddev_ms
    store = _make_store({
        "gsd_one": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    per_tool = get_windowed_tool_latency_stddev_ms("gsd_one", _WIN, store=store, now_ms=_NOW)
    global_sd = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(per_tool - global_sd) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_gsd": [(_NOW - 10, 5.0, True), (_NOW - 10, 15.0, True)]})
    assert isinstance(
        get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW),
        float,
    )
