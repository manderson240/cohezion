"""Item 1171: get_windowed_fleet_error_count_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> int
-- per-tool count of error (success=False) calls in the window.
Returns int. 0 for unknown/empty tool or all-success tool.

PRIMARY DISC.:
  tool_a=[T,F,F] → error_count_a=2
  tool_b=[T,T]   → error_count_b=0
  fleet_error_count=2
  error_a=2 kills error_b=0; kills fleet_count (can be equal — use tool_c to break).
  Symmetry: success_count_by_tool(t) + error_count_by_tool(t) == call_count_by_tool(t).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_error_count_by_tool,
    get_windowed_fleet_success_count_by_tool,
    get_windowed_fleet_call_count_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_error_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: error_a=2 kills error_b=0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fecbt_tool_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, False),
            ],
            "fecbt_tool_b": [
                (_NOW - 600, 40.0, True),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(_WIN, "fecbt_tool_a", store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 2, f"error_a=2; kills error_b=0/always-0; got {result}"


def test_fleet_error_count_by_tool_all_success() -> None:
    """All successes -> error count == 0."""
    _reset()
    store = _make_store(
        {
            "fecbt_all_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(_WIN, "fecbt_all_ok", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_error_count_by_tool_all_errors() -> None:
    """All failures -> error count == len(records)."""
    _reset()
    store = _make_store(
        {
            "fecbt_all_fail": [(_NOW - float(d), 10.0, False) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(
        _WIN, "fecbt_all_fail", store=store, now_ms=_NOW
    )
    assert result == 3


def test_fleet_error_count_by_tool_symmetry_with_success_and_call_count() -> None:
    """success_count + error_count == call_count for same tool."""
    _reset()
    store = _make_store(
        {
            "fecbt_sym": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, False),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    success = get_windowed_fleet_success_count_by_tool(_WIN, "fecbt_sym", store=store, now_ms=_NOW)
    errors = get_windowed_fleet_error_count_by_tool(_WIN, "fecbt_sym", store=store, now_ms=_NOW)
    total = get_windowed_fleet_call_count_by_tool(_WIN, "fecbt_sym", store=store, now_ms=_NOW)
    assert success + errors == total, (
        f"success({success}) + errors({errors}) should equal call_count({total})"
    )


def test_fleet_error_count_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    store = _make_store(
        {
            "fecbt_other": [(_NOW - 500, 10.0, False)],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_error_count_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_error_count_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0


def test_fleet_error_count_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fecbt_old": [(_NOW - _WIN - float(d), 10.0, False) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(_WIN, "fecbt_old", store=store, now_ms=_NOW)
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fecbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, False),
                (_NOW - 200, 30.0, False),
            ],
        }
    )
    result = get_windowed_fleet_error_count_by_tool(_WIN, "fecbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2
