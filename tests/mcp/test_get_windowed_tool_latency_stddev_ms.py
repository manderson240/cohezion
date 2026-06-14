"""Item 979: get_windowed_tool_latency_stddev_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- population standard deviation of latencies in window for a single tool.

PRIMARY DISC.: lats [10, 20, 30] -> stddev≈8.165 (not range=20.0, not mean=20.0, not 0.0).
single call -> 0.0; all same -> 0.0; unknown -> 0.0; returns float.
Uses population stddev (divide by n, not n-1) — we measure the full observed window.
"""

from __future__ import annotations

import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_stddev_primary_discriminator() -> None:
    """FALSIFIABLE: lats [10, 20, 30] -> population stddev≈8.165 (not range=20.0, not mean=20.0)."""
    _reset()
    store = _make_store(
        {
            "wstddev_a": [
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    result = get_windowed_tool_latency_stddev_ms("wstddev_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # population stddev: mean=20, deviations=[-10,0,10], variance=200/3, stddev=sqrt(200/3)
    expected = math.sqrt(200.0 / 3.0)  # ≈ 8.165
    assert abs(result - expected) < 0.001  # not 20.0 (range or mean), not 0.0


def test_single_call_returns_zero() -> None:
    """Single call -> stddev is 0.0 (no spread from a single measurement)."""
    store = _make_store({"wstddev_single": [(_NOW - 10, 42.0, True)]})
    assert (
        abs(get_windowed_tool_latency_stddev_ms("wstddev_single", _WIN, store=store, now_ms=_NOW))
        < 0.001
    )


def test_all_same_returns_zero() -> None:
    """All same latency -> stddev is 0.0."""
    store = _make_store({"wstddev_same": [(_NOW - 10, 15.0, True)] * 5})
    assert (
        abs(get_windowed_tool_latency_stddev_ms("wstddev_same", _WIN, store=store, now_ms=_NOW))
        < 0.001
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_stddev_ms("no_such_wstddev", _WIN, store={}, now_ms=_NOW) == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "wstddev_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
        }
    )
    assert get_windowed_tool_latency_stddev_ms("wstddev_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_old_extreme_excluded() -> None:
    """Old extreme excluded; stddev computed from windowed calls only."""
    store = _make_store(
        {
            "wstddev_mix": [
                (_NOW - _WIN - 100, 9999.0, True),  # old, excluded
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    result = get_windowed_tool_latency_stddev_ms("wstddev_mix", _WIN, store=store, now_ms=_NOW)
    expected = math.sqrt(200.0 / 3.0)  # from [10, 20, 30] only
    assert abs(result - expected) < 0.001  # not stddev of [9999, 10, 20, 30]


def test_two_calls_stddev() -> None:
    """Two calls: population stddev = |a - b| / 2."""
    store = _make_store({"wstddev_two": [(_NOW - 10, 10.0, True), (_NOW - 10, 30.0, True)]})
    result = get_windowed_tool_latency_stddev_ms("wstddev_two", _WIN, store=store, now_ms=_NOW)
    # mean=20, deviations=[-10, 10], variance=100, stddev=10.0
    assert abs(result - 10.0) < 0.001


def test_failures_included_in_stddev() -> None:
    """Failed calls contribute their latency to the stddev calculation."""
    store = _make_store(
        {
            "wstddev_fail": [
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 30.0, False),  # failure still counted
            ]
        }
    )
    result = get_windowed_tool_latency_stddev_ms("wstddev_fail", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 10.0) < 0.001  # same as two_calls test: stddev of [10, 30] = 10.0


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wstddev": [(_NOW - 10, 5.0, True), (_NOW - 10, 15.0, True)]})
    assert isinstance(
        get_windowed_tool_latency_stddev_ms("rtype_wstddev", _WIN, store=store, now_ms=_NOW),
        float,
    )
