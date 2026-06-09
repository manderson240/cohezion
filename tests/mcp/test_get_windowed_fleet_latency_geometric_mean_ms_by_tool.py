"""Item 1218: get_windowed_fleet_latency_geometric_mean_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool geometric mean latency within window.
Formula: exp(sum(log(lat_i)) / n). Returns float. 0.0 for unknown/empty tool.
Appropriate for log-normal latency distributions (multiplicative processes).
Always <= arithmetic mean (equality iff all values identical).
0-latency values guarded (return 0.0).

PRIMARY DISC.:
  tool_a=[1,10,100] → geo = (1*10*100)^(1/3) = 10.0
  tool_b=[100,100,100] → geo = 100.0
  geo_a=10.0 kills geo_b=100.0; kills arith_mean_a=37.0; kills always-0.
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_geometric_mean_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_geometric_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: geo_a=10.0 kills geo_b=100.0; kills arith_mean_a=37.0; kills always-0."""
    _reset()
    store = _make_store({
        "fgmbt_a": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 10.0, True),
            (_NOW - 300, 100.0, True),
        ],
        "fgmbt_b": [
            (_NOW - 700, 100.0, True),
            (_NOW - 500, 100.0, True),
            (_NOW - 300, 100.0, True),
        ],
    })
    ga = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_a", store=store, now_ms=_NOW
    )
    gb = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ga, float), f"expected float, got {type(ga)}"
    # (1*10*100)^(1/3) = 1000^(1/3) = 10.0
    assert abs(ga - 10.0) < 1e-9, (
        f"geo_a=10.0; kills geo_b=100.0/arith=37.0/always-0; got {ga}"
    )
    assert abs(gb - 100.0) < 1e-9, f"geo_b=100.0 (uniform); got {gb}"


def test_fleet_geometric_mean_less_than_arithmetic() -> None:
    """Geometric mean <= arithmetic mean for non-uniform distributions."""
    _reset()
    store = _make_store({
        "fgmbt_cmp": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 10.0, True),
            (_NOW - 300, 100.0, True),
        ],
    })
    geo = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_cmp", store=store, now_ms=_NOW
    )
    arith = (1.0 + 10.0 + 100.0) / 3.0  # 37.0
    assert geo < arith, f"geo({geo}) must be < arith({arith})"
    assert abs(geo - 10.0) < 1e-9


def test_fleet_geometric_mean_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fgmbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_geometric_mean_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_geometric_mean_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fgmbt_old": [
            (_NOW - _WIN - 300, float(v), True)
            for v in [1.0, 10.0, 100.0]
        ],
    })
    result = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_geometric_mean_single_call() -> None:
    """Single call → that latency (geo mean of 1 value = the value itself)."""
    _reset()
    store = _make_store({
        "fgmbt_one": [(_NOW - 500, 42.0, True)],
    })
    result = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_one", store=store, now_ms=_NOW
    )
    assert abs(result - 42.0) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fgmbt_rt": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 10.0, True),
            (_NOW - 300, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_geometric_mean_ms_by_tool(
        _WIN, "fgmbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9
