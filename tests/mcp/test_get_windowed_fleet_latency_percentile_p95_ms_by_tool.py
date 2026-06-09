"""Item 1210: get_windowed_fleet_latency_percentile_p95_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool 95th-percentile latency within window.
Returns float. 0.0 for unknown/empty tool.
Nearest-rank: sorted_lats[ceil(0.95*n)-1].

PRIMARY DISC.:
  tool_a=[10..100] n=10 → ceil(0.95*10)-1=9 → sorted[9]=100.0
  tool_b=[100..1000] n=10 → sorted[9]=1000.0
  p95_a=100.0 kills p95_b=1000.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_p5_ms_by_tool,
    get_windowed_fleet_latency_percentile_p95_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p95_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: p95_a=100.0 kills p95_b=1000.0; kills always-0."""
    _reset()
    store = _make_store({
        "fp95bt_a": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10ms, 20ms, ... 100ms
        ],
        "fp95bt_b": [
            (_NOW - 990 + i * 99, float(100 + i * 100), True)
            for i in range(10)  # 100ms, 200ms, ... 1000ms
        ],
    })
    p95_a = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_a", store=store, now_ms=_NOW
    )
    p95_b = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_b", store=store, now_ms=_NOW
    )
    assert isinstance(p95_a, float), f"expected float, got {type(p95_a)}"
    # n=10, ceil(0.95*10)-1 = ceil(9.5)-1 = 10-1 = 9 → sorted[9]
    assert p95_a == 100.0, (
        f"p95_a=100.0 (highest value); kills p95_b=1000/always-0; got {p95_a}"
    )
    assert p95_b == 1000.0, f"p95_b=1000.0; got {p95_b}"


def test_fleet_p95_single_call() -> None:
    """Single call → its latency is p95."""
    _reset()
    store = _make_store({
        "fp95bt_one": [(_NOW - 500, 77.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_one", store=store, now_ms=_NOW
    )
    assert result == 77.0


def test_fleet_p95_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fp95bt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_p95_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p95_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fp95bt_old": [
            (_NOW - _WIN - 300, 10.0, True),
            (_NOW - _WIN - 100, 20.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p95_ipr90_composition() -> None:
    """IPR90 = p95 - p5 (composition identity)."""
    _reset()
    store = _make_store({
        "fp95bt_ipr": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10..100
        ],
    })
    p5 = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fp95bt_ipr", store=store, now_ms=_NOW
    )
    p95 = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_ipr", store=store, now_ms=_NOW
    )
    # p5=10.0, p95=100.0, IPR90=90.0
    assert p5 == 10.0, f"p5={p5}"
    assert p95 == 100.0, f"p95={p95}"
    assert p95 - p5 == 90.0, f"IPR90={p95-p5}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp95bt_rt": [
            (_NOW - 400, 30.0, True),
            (_NOW - 200, 50.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fp95bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    # n=2, ceil(0.95*2)-1=ceil(1.9)-1=2-1=1 → sorted[1]=50.0
    assert result == 50.0
