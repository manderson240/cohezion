"""Item 927: get_tool_windowed_p50_ms(tool_name, window_ms, ...) -> float.

PRIMARY DISC.: [10,20,30,40,50]ms -> windowed_p50=30.0 (kills p95 or mean impl);
old call at 200ms outside 1000ms window -> excluded; unknown -> 0.0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_tool_windowed_p50_ms,
)

NOW = 70_000.0


def _reset():
    clear_telemetry_stores()


def test_p50_not_p95_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,30,40,50]ms -> p50=30.0, NOT p95 or mean.
    Kills impl delegating to p95 or returning mean."""
    _reset()
    store: dict = {
        "p50_wind": [(NOW - (i + 1) * 100, lat, True) for i, lat in enumerate([10, 20, 30, 40, 50])]
    }
    result = get_tool_windowed_p50_ms("p50_wind", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result - 30.0) < 0.001
    assert abs(result - 50.0) > 5.0  # not p95-ish


def test_old_call_excluded_from_window() -> None:
    """Old call at 200ms outside 1000ms window must NOT affect p50."""
    _reset()
    store: dict = {
        "win_p50": [
            (NOW - 100, 10.0, True),  # in window
            (NOW - 9000, 200.0, True),  # outside 1000ms window
        ]
    }
    result = get_tool_windowed_p50_ms("win_p50", window_ms=1000.0, store=store, now_ms=NOW)
    # Only one call in window -> p50 = that call
    assert abs(result - 10.0) < 0.001


def test_unknown_tool_returns_zero_float() -> None:
    _reset()
    store: dict = {}
    result = get_tool_windowed_p50_ms("unknown", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 0.0
    assert isinstance(result, float)


def test_single_call_p50_equals_latency() -> None:
    _reset()
    store: dict = {"single": [(NOW - 50, 88.0, True)]}
    result = get_tool_windowed_p50_ms("single", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result - 88.0) < 0.001


def test_returns_float() -> None:
    _reset()
    store: dict = {"typed": [(NOW - 100, 5.0, True)]}
    assert isinstance(
        get_tool_windowed_p50_ms("typed", window_ms=5000.0, store=store, now_ms=NOW), float
    )
