"""Item 1216: get_windowed_fleet_latency_percentile_p99_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool 99th-percentile latency within window. Thin wrapper over
   get_windowed_fleet_latency_percentile_ms_by_tool(..., 99, ...).
Nearest-rank: sorted_lats[ceil(0.99*n)-1]. Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
    → ceil(0.99*10)-1 = ceil(9.9)-1 = 10-1 = 9 → sorted[9]=100.0
  tool_b=[100,200,300,400,500,600,700,800,900,1000] n=10
    → sorted[9]=1000.0
  p99_a=100.0 kills p99_b=1000.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_p99_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p99_primary_discriminator() -> None:
    """PRIMARY DISC.: p99_a=100.0 kills p99_b=1000.0; kills always-0."""
    _reset()
    store = _make_store({
        "fp99bt_a": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10,20,30,40,50,60,70,80,90,100
        ],
        "fp99bt_b": [
            (_NOW - 990 + i * 99, float(100 + i * 100), True)
            for i in range(10)  # 100,200,...,1000
        ],
    })
    pa = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_a", store=store, now_ms=_NOW
    )
    pb = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_b", store=store, now_ms=_NOW
    )
    assert isinstance(pa, float), f"expected float, got {type(pa)}"
    # n=10, ceil(0.99*10)-1 = ceil(9.9)-1 = 10-1 = 9 → sorted[9]=100.0
    assert pa == 100.0, (
        f"p99_a=100.0; kills p99_b=1000.0/always-0; got {pa}"
    )
    assert pb == 1000.0, f"p99_b=1000.0 (highest of 100..1000); got {pb}"


def test_fleet_p99_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fp99bt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_p99_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p99_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fp99bt_old": [
            (_NOW - _WIN - 300, float(10 + i * 10), True)
            for i in range(10)
        ],
    })
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p99_single_call() -> None:
    """Single call → that call's latency."""
    _reset()
    store = _make_store({
        "fp99bt_one": [(_NOW - 500, 42.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_one", store=store, now_ms=_NOW
    )
    # n=1: ceil(0.99*1)-1 = ceil(0.99)-1 = 1-1 = 0 → sorted[0]=42.0
    assert result == 42.0


def test_fleet_p99_is_maximum_for_small_n() -> None:
    """For small n, p99 = maximum (ceil(0.99*n)=n for n<=100)."""
    _reset()
    store = _make_store({
        "fp99bt_max": [
            (_NOW - 900 + i * 100, float(v), True)
            for i, v in enumerate([50, 10, 80, 30, 70])
        ],
    })
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_max", store=store, now_ms=_NOW
    )
    # n=5: ceil(0.99*5)-1=ceil(4.95)-1=5-1=4 → sorted[4]=80.0
    assert result == 80.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp99bt_rt": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)
        ],
    })
    result = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fp99bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 100.0
