"""Item 1170: get_windowed_fleet_success_count_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> int
-- per-tool count of successful (success=True) calls in the window.
Returns int. 0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[T,T,F,T] → success_count_a=3
  tool_b=[F,F,F]   → success_count_b=0
  fleet_success_count=3
  count_a=3 kills count_b=0; count_a=3 also == fleet total (by design)
  so DISC. test uses a store where fleet total > count_a to kill fleet equality.
  DISC. store: tool_a=[T,T,F] → 2 successes; tool_b=[T,F] → 1 success.
  success_a=2 kills success_b=1; fleet_success=3; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_success_count_by_tool,
    get_windowed_fleet_success_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_success_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: success_a=2 kills success_b=1; kills fleet_success=3; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fscbt_tool_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, False),
            ],
            "fscbt_tool_b": [
                (_NOW - 600, 40.0, True),
                (_NOW - 500, 50.0, False),
            ],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(
        _WIN, "fscbt_tool_a", store=store, now_ms=_NOW
    )
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 2, f"success_a=2; kills success_b=1/fleet_success=3/always-0; got {result}"


def test_fleet_success_count_by_tool_all_success() -> None:
    """All successes -> count == len(records)."""
    _reset()
    store = _make_store(
        {
            "fscbt_all_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700, 600]],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(
        _WIN, "fscbt_all_ok", store=store, now_ms=_NOW
    )
    assert result == 4


def test_fleet_success_count_by_tool_all_errors() -> None:
    """All failures -> 0."""
    _reset()
    store = _make_store(
        {
            "fscbt_all_fail": [(_NOW - float(d), 10.0, False) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(
        _WIN, "fscbt_all_fail", store=store, now_ms=_NOW
    )
    assert result == 0
    assert isinstance(result, int)


def test_fleet_success_count_by_tool_differs_from_fleet_success_count() -> None:
    """Per-tool success count < fleet success count when tool_b also has successes."""
    _reset()
    store = _make_store(
        {
            "fscbt_diff_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
            ],
            "fscbt_diff_b": [
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, True),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    count_a = get_windowed_fleet_success_count_by_tool(
        _WIN, "fscbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_count = get_windowed_fleet_success_count(_WIN, store=store, now_ms=_NOW)
    # count_a=1; fleet=4 (1+3)
    assert count_a < fleet_count, f"per-tool({count_a}) should be < fleet({fleet_count})"


def test_fleet_success_count_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    store = _make_store(
        {
            "fscbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_success_count_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_success_count_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0


def test_fleet_success_count_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fscbt_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(_WIN, "fscbt_old", store=store, now_ms=_NOW)
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fscbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, False),
                (_NOW - 200, 30.0, True),
            ],
        }
    )
    result = get_windowed_fleet_success_count_by_tool(_WIN, "fscbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2
