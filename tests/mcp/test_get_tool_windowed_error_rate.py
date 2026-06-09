"""Item 923: get_tool_windowed_error_rate(tool_name, window_ms, ...) -> float.

PRIMARY DISC.: 2 fail + 2 success in window -> 0.5
  (kills impl returning count=2 or ignoring window boundary);
unknown tool -> 0.0; old calls outside window excluded.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_tool_windowed_error_rate,
)

NOW = 30_000.0


def _reset():
    clear_telemetry_stores()


def test_rate_not_count_primary_discriminator() -> None:
    """FALSIFIABLE: 2 fail + 2 success -> 0.5, NOT 2 (count).
    Kills impl returning error_count instead of rate."""
    _reset()
    store: dict = {
        "rate_tool": [
            (NOW - 500, 10.0, True),
            (NOW - 400, 10.0, True),
            (NOW - 300, 10.0, False),
            (NOW - 200, 10.0, False),
        ]
    }
    result = get_tool_windowed_error_rate("rate_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result - 0.5) < 0.001
    assert isinstance(result, float)


def test_old_call_excluded_from_window() -> None:
    """Old failure outside window must not inflate error rate."""
    _reset()
    store: dict = {
        "win_err": [
            (NOW - 500, 10.0, True),    # in window (success)
            (NOW - 9000, 10.0, False),   # OUTSIDE window (failure — must not count)
        ]
    }
    result = get_tool_windowed_error_rate("win_err", window_ms=1000.0, store=store, now_ms=NOW)
    assert result == 0.0  # only the success is in window


def test_unknown_tool_returns_zero_float() -> None:
    _reset()
    store: dict = {}
    result = get_tool_windowed_error_rate("unknown", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 0.0
    assert isinstance(result, float)


def test_all_success_returns_zero() -> None:
    _reset()
    store: dict = {"ok_tool": [(NOW - 100, 5.0, True) for _ in range(5)]}
    result = get_tool_windowed_error_rate("ok_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 0.0


def test_all_fail_returns_one() -> None:
    _reset()
    store: dict = {"bad_tool": [(NOW - i * 100, 5.0, False) for i in range(1, 4)]}
    result = get_tool_windowed_error_rate("bad_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result - 1.0) < 0.001
