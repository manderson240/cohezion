"""Item 1164: get_windowed_fleet_call_count_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> int
-- per-tool call count within the fleet store window.
Returns int. 0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[3 calls], tool_b=[2 calls]
  count_a=3; kills count_b=2; kills fleet_total=5; kills always-0.
  Composition: sum(count_by_tool(t) for all tools t) == fleet_total_count.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_count_by_tool,
    get_windowed_fleet_latency_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_call_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: count_a=3; kills count_b=2, fleet_total=5, always-0."""
    _reset()
    store = _make_store(
        {
            "fcc_tool_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
            ],
            "fcc_tool_b": [
                (_NOW - 600, 40.0, True),
                (_NOW - 500, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_tool_a", store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 3, f"count_a=3; kills count_b=2/fleet=5/always-0; got {result}"


def test_fleet_call_count_by_tool_sum_equals_fleet_total() -> None:
    """Composition: sum of per-tool counts == fleet total count."""
    _reset()
    store = _make_store(
        {
            "fcc_sum_a": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
            "fcc_sum_b": [(_NOW - float(d), 20.0, True) for d in [600, 500]],
            "fcc_sum_c": [(_NOW - 400, 30.0, True)],
        }
    )
    count_a = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_sum_a", store=store, now_ms=_NOW)
    count_b = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_sum_b", store=store, now_ms=_NOW)
    count_c = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_sum_c", store=store, now_ms=_NOW)
    fleet_total = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert count_a + count_b + count_c == fleet_total, (
        f"sum({count_a}+{count_b}+{count_c}={count_a + count_b + count_c}) != fleet({fleet_total})"
    )


def test_fleet_call_count_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    store = _make_store(
        {
            "fcc_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_call_count_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_call_count_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_call_count_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0


def test_fleet_call_count_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window for that tool -> 0."""
    _reset()
    store = _make_store(
        {
            "fcc_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_old", store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_call_count_by_tool_counts_both_success_and_error() -> None:
    """Counts ALL calls regardless of success/failure flag."""
    _reset()
    store = _make_store(
        {
            "fcc_mixed": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, False),
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, False),
            ],
        }
    )
    result = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_mixed", store=store, now_ms=_NOW)
    assert result == 4, f"4 calls regardless of success/fail; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fcc_rt": [(_NOW - 300, 10.0, True), (_NOW - 200, 20.0, True)],
        }
    )
    result = get_windowed_fleet_call_count_by_tool(_WIN, "fcc_rt", store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2
