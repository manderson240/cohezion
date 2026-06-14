"""Item 922: get_tool_windowed_p95_ms(tool_name, window_ms, *, now_ms=None) -> float.

PRIMARY DISC.: 5 recent calls [10,20,30,40,100]ms -> windowed_p95 > 60
  (kills p50=30 impl); old call at 500ms outside window -> excluded;
unknown tool -> 0.0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_tool_windowed_p95_ms,
)

NOW = 20_000.0


def _reset():
    clear_telemetry_stores()


def test_p95_not_p50_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,30,40,100]ms -> p95 > 60, NOT p50=30."""
    _reset()
    store: dict = {
        "p95_wind": [(NOW - i * 100, lat, True) for i, lat in enumerate([10, 20, 30, 40, 100])]
    }
    result = get_tool_windowed_p95_ms("p95_wind", window_ms=10_000.0, store=store, now_ms=NOW)
    assert result > 60.0
    assert abs(result - 30.0) > 5.0  # not p50


def test_old_call_excluded_from_window() -> None:
    """Call outside window must NOT contribute to p95."""
    _reset()
    store: dict = {
        "win_tool": [
            (NOW - 500, 10.0, True),  # in window
            (NOW - 9000, 500.0, True),  # OUTSIDE window (500ms window)
        ]
    }
    result = get_tool_windowed_p95_ms("win_tool", window_ms=1000.0, store=store, now_ms=NOW)
    assert result < 100.0  # 500ms call excluded


def test_unknown_tool_returns_zero_float() -> None:
    _reset()
    store: dict = {}
    result = get_tool_windowed_p95_ms("unknown", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 0.0
    assert isinstance(result, float)


def test_single_call_p95_equals_latency() -> None:
    _reset()
    store: dict = {"single": [(NOW - 100, 42.0, True)]}
    result = get_tool_windowed_p95_ms("single", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result - 42.0) < 0.001


def test_returns_float() -> None:
    _reset()
    store: dict = {"typed": [(NOW - 100, 15.0, True)]}
    assert isinstance(
        get_tool_windowed_p95_ms("typed", window_ms=5000.0, store=store, now_ms=NOW), float
    )
