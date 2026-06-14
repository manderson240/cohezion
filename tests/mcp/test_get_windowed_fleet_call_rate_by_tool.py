"""Item 1179: get_windowed_fleet_call_rate_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool call rate (calls per second) within the fleet store window.
Returns float. 0.0 for unknown/empty tool.
Formula: total_calls_in_window / (window_ms / 1000.0).

PRIMARY DISC.:
  tool_a has 6 calls in a 2000ms window → rate_a = 6 / 2.0 = 3.0 calls/s
  tool_b has 2 calls in the same window → rate_b = 2 / 2.0 = 1.0 calls/s
  fleet_rate pools both (8 calls / 2.0s = 4.0 calls/s)
  rate_a=3.0 kills rate_b=1.0; kills fleet_rate=4.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_rate_by_tool,
)

_NOW = 1_000_000.0
_WIN = 2000.0  # 2-second window for easy rate arithmetic


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_call_rate_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: rate_a=3.0 kills rate_b=1.0; kills fleet_rate=4.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_a": [
                (_NOW - 1800, 10.0, True),
                (_NOW - 1600, 20.0, True),
                (_NOW - 1400, 30.0, True),
                (_NOW - 1200, 10.0, True),
                (_NOW - 1000, 20.0, True),
                (_NOW - 800, 30.0, True),
            ],
            "fcrbrt_b": [
                (_NOW - 1500, 50.0, True),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 6.0 / (2000.0 / 1000.0)  # 3.0 calls/s
    assert abs(result - expected) < 1e-9, (
        f"rate_a=3.0; kills rate_b=1.0/fleet_rate=4.0/always-0; got {result}"
    )


def test_fleet_call_rate_by_tool_differs_from_fleet_rate() -> None:
    """Per-tool rate differs from fleet rate (pooled)."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_diff_a": [
                (_NOW - 1800, 10.0, True),
                (_NOW - 1200, 20.0, True),
                (_NOW - 600, 30.0, True),
            ],
            "fcrbrt_diff_b": [
                (_NOW - 1500, 50.0, True),
                (_NOW - 900, 50.0, True),
                (_NOW - 300, 50.0, True),
                (_NOW - 100, 50.0, True),
                (_NOW - 50, 50.0, True),
            ],
        }
    )
    tool_rate = get_windowed_fleet_call_rate_by_tool(
        _WIN, "fcrbrt_diff_a", store=store, now_ms=_NOW
    )
    # fleet rate: 8 calls / 2.0s = 4.0 calls/s; tool_a = 3 calls / 2.0s = 1.5 calls/s
    fleet_total = sum(1 for recs in store.values() for ts, _lat, _ok in recs if ts >= _NOW - _WIN)
    fleet_rate = fleet_total / (_WIN / 1000.0)
    assert abs(tool_rate - fleet_rate) > 0.1, (
        f"per-tool({tool_rate}) should differ from fleet({fleet_rate})"
    )


def test_fleet_call_rate_by_tool_formula_count_over_window() -> None:
    """Formula: rate == count / (window_ms / 1000.0)."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_form": [
                (_NOW - 1900, 10.0, True),
                (_NOW - 1700, 20.0, False),
                (_NOW - 1500, 30.0, True),
                (_NOW - 500, 40.0, True),
            ],
        }
    )
    rate = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_form", store=store, now_ms=_NOW)
    # 4 calls in 2000ms window → 4 / 2.0 = 2.0 calls/s
    expected = 4.0 / (_WIN / 1000.0)
    assert abs(rate - expected) < 1e-9, f"formula: 4/{_WIN / 1000.0}={expected}; got {rate}"


def test_fleet_call_rate_by_tool_counts_both_success_and_error() -> None:
    """Rate counts ALL calls (success + error) within the window."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_mixed": [
                (_NOW - 1000, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 600, 30.0, True),
                (_NOW - 400, 40.0, False),
            ],
        }
    )
    rate = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_mixed", store=store, now_ms=_NOW)
    expected = 4.0 / (_WIN / 1000.0)  # all 4 calls regardless of success flag
    assert abs(rate - expected) < 1e-9


def test_fleet_call_rate_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_call_rate_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_call_rate_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_call_rate_by_tool_single_call_returns_correct_rate() -> None:
    """Single call in window → 1 / (window_ms / 1000.0)."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_single": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_single", store=store, now_ms=_NOW)
    expected = 1.0 / (_WIN / 1000.0)  # 0.5 calls/s for 2s window
    assert abs(result - expected) < 1e-9, f"single call → {expected}; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fcrbrt_rt": [
                (_NOW - 1000, 10.0, True),
                (_NOW - 500, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_rate_by_tool(_WIN, "fcrbrt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = 2.0 / (_WIN / 1000.0)  # 1.0 calls/s
    assert abs(result - expected) < 1e-9
