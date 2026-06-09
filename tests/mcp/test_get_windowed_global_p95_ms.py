"""Item 952: get_windowed_global_p95_ms(window_ms, *, store=None, now_ms=None) -> float
-- pooled p95 across ALL tools in the recent window.

PRIMARY DISC.: tool A=[10]*3, tool B=[100]*1 in window.
naive avg-of-per-tool-p95s = (10+100)/2 = 55 WRONG.
pooled [10,10,10,100] p95 = 86.5 (correct, using linear interpolation).
Kills impl that averages per-tool p95 values.
empty / no-recent-calls -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_p95_ms,
)

_NOW = 1_000_000.0  # fixed "now" in ms for deterministic tests
_WIN = 500.0        # 500 ms window


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    """Build an injectable windowed store.  Each entry: (ts_ms, lat_ms, success)."""
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


# ─── Primary discriminator ────────────────────────────────────────────────────

def test_pooled_not_avg_of_per_tool_p95s_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=[10]*3 + tool B=[100]*1 in window.
    avg-of-p95s = (10+100)/2 = 55 WRONG.
    pooled [10,10,10,100] p95 ≈ 86.5 (linear interp).  Kills avg-per-tool impl."""
    _reset()
    store = _make_store({
        "gw95_a": [(_NOW - 10, 10.0, True)] * 3,
        "gw95_b": [(_NOW - 10, 100.0, True)],
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    # Pooled [10, 10, 10, 100] with linear interpolation:
    # idx = 0.95 * 3 = 2.85  -> 10 + 0.85*(100-10) = 86.5
    assert abs(result - 86.5) < 0.5   # pooled p95
    assert abs(result - 55.0) > 1.0   # not naive avg-of-p95s


# ─── Edge cases ───────────────────────────────────────────────────────────────

def test_empty_store_returns_zero() -> None:
    """No windowed calls -> 0.0."""
    _reset()
    assert get_windowed_global_p95_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    store = _make_store({"ft_gw95": [(_NOW - 1, 5.0, True)]})
    assert isinstance(get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW), float)


def test_calls_outside_window_excluded() -> None:
    """Calls older than window_ms are excluded."""
    store = _make_store({
        "gw95_old": [
            (_NOW - _WIN - 1, 1000.0, True),   # outside window
            (_NOW - 10, 20.0, True),             # inside window
        ]
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    # Only 20ms inside window -> p95 = 20.0
    assert abs(result - 20.0) < 0.001


def test_all_calls_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "gw95_exp": [(_NOW - _WIN - 100, 50.0, True)],
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_single_recent_call_p95_equals_latency() -> None:
    """Single recent call -> p95 == that latency."""
    store = _make_store({"gw95_single": [(_NOW - 1, 77.0, True)]})
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 77.0) < 0.001


def test_single_tool_consistent_with_per_tool_windowed_p95() -> None:
    """Single tool: global windowed p95 equals per-tool windowed p95."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_windowed_p95_ms
    store = _make_store({
        "consist_gw95": [
            (_NOW - 10, lat, True) for lat in [10.0, 20.0, 30.0, 40.0, 50.0]
        ]
    })
    global_p95 = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    tool_p95 = get_tool_windowed_p95_ms("consist_gw95", _WIN, store=store, now_ms=_NOW)
    assert abs(global_p95 - tool_p95) < 0.001


def test_multiple_tools_all_recent_pooled() -> None:
    """Three tools — all calls recent — pools all latencies."""
    store = _make_store({
        "mt_a": [(_NOW - 5, lat, True) for lat in [1.0, 2.0, 3.0]],
        "mt_b": [(_NOW - 5, lat, True) for lat in [100.0, 200.0]],
        "mt_c": [(_NOW - 5, 50.0, True)],
    })
    result = get_windowed_global_p95_ms(_WIN, store=store, now_ms=_NOW)
    # Pooled sorted: [1, 2, 3, 50, 100, 200] -> p95 = idx=0.95*5=4.75 -> 100+0.75*(200-100)=175.0
    assert isinstance(result, float)
    assert result > 0.0
    # Sanity: must be between min and max of all values
    assert 1.0 <= result <= 200.0
