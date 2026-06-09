"""Item 1209: get_windowed_fleet_latency_percentile_p5_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool 5th-percentile latency within window.
Returns float. 0.0 for unknown/empty tool.
Nearest-rank: sorted_lats[ceil(0.05*n)-1].

PRIMARY DISC.:
  tool_a=[10..100] n=10 → ceil(0.05*10)-1=0 → sorted[0]=10.0
  tool_b=[100..1000] n=10 → sorted[0]=100.0
  p5_a=10.0 kills p5_b=100.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_p5_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p5_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: p5_a=10.0 kills p5_b=100.0; kills always-0."""
    _reset()
    # 10 evenly-spaced latency values for each tool
    store = _make_store({
        "fp5bt_a": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10ms, 20ms, ... 100ms
        ],
        "fp5bt_b": [
            (_NOW - 990 + i * 99, float(100 + i * 100), True)
            for i in range(10)  # 100ms, 200ms, ... 1000ms
        ],
    })
    p5_a = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_a", store=store, now_ms=_NOW
    )
    p5_b = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_b", store=store, now_ms=_NOW
    )
    assert isinstance(p5_a, float), f"expected float, got {type(p5_a)}"
    # n=10, ceil(0.05*10)-1 = ceil(0.5)-1 = 1-1 = 0 → sorted[0]
    assert p5_a == 10.0, (
        f"p5_a=10.0 (lowest value, nearest-rank); kills p5_b=100/always-0; got {p5_a}"
    )
    assert p5_b == 100.0, f"p5_b=100.0; got {p5_b}"


def test_fleet_p5_single_call() -> None:
    """Single call → its latency is p5."""
    _reset()
    store = _make_store({
        "fp5bt_one": [(_NOW - 500, 42.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_one", store=store, now_ms=_NOW
    )
    assert result == 42.0


def test_fleet_p5_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fp5bt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_p5_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p5_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fp5bt_old": [
            (_NOW - _WIN - 300, 10.0, True),
            (_NOW - _WIN - 100, 20.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p5_is_minimum_for_small_n() -> None:
    """For small n, p5 == min (all floor to index 0)."""
    _reset()
    store = _make_store({
        "fp5bt_min": [
            (_NOW - 800, 5.0, True),
            (_NOW - 600, 10.0, True),
            (_NOW - 400, 15.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_min", store=store, now_ms=_NOW
    )
    # n=3, ceil(0.05*3)-1=ceil(0.15)-1=1-1=0 → sorted[0]=5.0
    assert result == 5.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp5bt_rt": [
            (_NOW - 400, 30.0, True),
            (_NOW - 200, 50.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp5bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    # n=2, ceil(0.05*2)-1=ceil(0.1)-1=1-1=0 → sorted[0]=30.0
    assert result == 30.0
