"""Item 1182: get_windowed_fleet_total_call_count_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> int
-- per-tool total call count (success + error) within the fleet store window.
Returns int. 0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a has 4 calls (2T+2F) in window → count_a=4
  tool_b has 2 calls (0T+2F)           → count_b=2
  fleet count pools both = 6
  count_a=4 kills count_b=2; kills fleet_count=6; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_total_call_count_by_tool,
    get_windowed_fleet_success_count_by_tool,
    get_windowed_fleet_error_count_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_total_call_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: count_a=4 kills count_b=2; kills fleet_count=6; kills always-0."""
    _reset()
    store = _make_store(
        {
            "ftccbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, False),
                (_NOW - 600, 40.0, False),
            ],
            "ftccbt_b": [
                (_NOW - 500, 50.0, False),
                (_NOW - 400, 60.0, False),
            ],
        }
    )
    result = get_windowed_fleet_total_call_count_by_tool(_WIN, "ftccbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 4, f"count_a=4; kills count_b=2/fleet_count=6/always-0; got {result}"


def test_fleet_total_call_count_by_tool_equals_success_plus_error() -> None:
    """Composition: total_count == success_count + error_count."""
    _reset()
    store = _make_store(
        {
            "ftccbt_comp": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, False),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    total = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "ftccbt_comp", store=store, now_ms=_NOW
    )
    success = get_windowed_fleet_success_count_by_tool(
        _WIN, "ftccbt_comp", store=store, now_ms=_NOW
    )
    error = get_windowed_fleet_error_count_by_tool(_WIN, "ftccbt_comp", store=store, now_ms=_NOW)
    assert total == success + error, f"total({total}) != success({success}) + error({error})"


def test_fleet_total_call_count_by_tool_counts_both_outcomes() -> None:
    """Counts both True and False calls."""
    _reset()
    store = _make_store(
        {
            "ftccbt_mixed": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, True),
            ],
        }
    )
    result = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "ftccbt_mixed", store=store, now_ms=_NOW
    )
    assert result == 3


def test_fleet_total_call_count_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0."""
    _reset()
    store = _make_store(
        {
            "ftccbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0
    assert isinstance(result, int)


def test_fleet_total_call_count_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0."""
    _reset()
    result = get_windowed_fleet_total_call_count_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0


def test_fleet_total_call_count_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0."""
    _reset()
    store = _make_store(
        {
            "ftccbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "ftccbt_old", store=store, now_ms=_NOW
    )
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "ftccbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, False),
                (_NOW - 200, 30.0, True),
            ],
        }
    )
    result = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "ftccbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 3
