"""Item 1198: get_windowed_fleet_latency_p10_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool 10th-percentile latency within the window.
Returns float. 0.0 for unknown/empty tool or all calls outside window.
Thin wrapper: get_windowed_fleet_latency_percentile_ms_by_tool(..., 10, ...).
Nearest-rank: ceil(0.10 * n) - 1 (0-based index).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → p10=10.0 (idx=0)
  tool_b=[100,200,300,400,500] → p10=100.0 (idx=0)
  p10_a=10.0 kills p10_b=100.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p10_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p10_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: p10_a=10.0 kills p10_b=100.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fp10bt_a": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
            "fp10bt_b": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([100, 200, 300, 400, 500])
            ],
        }
    )
    p10_a = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_a", store=store, now_ms=_NOW)
    p10_b = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_b", store=store, now_ms=_NOW)
    assert isinstance(p10_a, float), f"expected float, got {type(p10_a)}"
    assert p10_a == 10.0, (
        f"p10_a=10.0 (idx=0 of [10,20,30,40,50]); kills p10_b=100/always-0; got {p10_a}"
    )
    assert p10_b == 100.0, f"p10_b=100.0; got {p10_b}"


def test_fleet_p10_by_tool_single_call() -> None:
    """Single call → that latency is p10."""
    _reset()
    store = _make_store(
        {
            "fp10bt_one": [(_NOW - 500, 77.0, True)],
        }
    )
    result = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_one", store=store, now_ms=_NOW)
    assert result == 77.0


def test_fleet_p10_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fp10bt_other": [(_NOW - 500, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_p10_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_p10_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_p10_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fp10bt_old": [
                (_NOW - _WIN - 200, 5.0, True),
                (_NOW - _WIN - 100, 10.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_old", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_p10_picks_lowest_decile() -> None:
    """p10 is below the median (sanity: p10 < p50)."""
    _reset()
    store = _make_store(
        {
            "fp10bt_cmp": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    p10 = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_cmp", store=store, now_ms=_NOW)
    # p50 = ceil(0.5*5)-1 = 2 → sorted[2] = 30.0
    assert p10 < 30.0, f"p10 should be below median=30; got {p10}"


def test_fleet_p10_by_tool_all_same_latency() -> None:
    """All same latency → p10 == that value."""
    _reset()
    store = _make_store(
        {
            "fp10bt_flat": [(_NOW - float(d), 42.0, True) for d in [900, 600, 300]],
        }
    )
    result = get_windowed_fleet_latency_p10_ms_by_tool(
        _WIN, "fp10bt_flat", store=store, now_ms=_NOW
    )
    assert result == 42.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fp10bt_rt": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    result = get_windowed_fleet_latency_p10_ms_by_tool(_WIN, "fp10bt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 10.0
