"""Item 1194: get_windowed_fleet_latency_spread_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency spread (IQR: p75 - p25) within the window.
Returns float. 0.0 for unknown/empty tool or fewer than 2 calls.

Nearest-rank percentiles (ceil(p/100 * n) - 1, 0-based).
For [10,20,30,40,50] (n=5): p25→idx1=20, p75→idx3=40 → IQR=20.0.
For [100,100,100,100,100]: p25=p75=100 → IQR=0.0.

PRIMARY DISC.:
  spread_a=20.0 kills spread_b=0.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_spread_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_spread_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: spread_a=20.0 kills spread_b=0.0; kills always-0."""
    _reset()
    store = _make_store({
        "fspbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 700, 20.0, True),
            (_NOW - 500, 30.0, True),
            (_NOW - 300, 40.0, True),
            (_NOW - 100, 50.0, True),
        ],
        "fspbt_b": [
            (_NOW - float(d), 100.0, True) for d in [900, 700, 500, 300, 100]
        ],
    })
    spread_a = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_a", store=store, now_ms=_NOW
    )
    spread_b = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(spread_a, float), f"expected float, got {type(spread_a)}"
    assert spread_a == 20.0, (
        f"spread_a=20.0 (p75=40-p25=20); kills spread_b=0/always-0; got {spread_a}"
    )
    assert spread_b == 0.0, f"flat latency → IQR=0; got {spread_b}"


def test_fleet_spread_by_tool_single_call_returns_zero() -> None:
    """Single call → fewer than 2 points → 0.0."""
    _reset()
    store = _make_store({
        "fspbt_one": [(_NOW - 500, 50.0, True)],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_one", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_spread_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fspbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_spread_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_spread_by_tool_two_calls() -> None:
    """Two calls: p25 and p75 pick the lower and higher values."""
    _reset()
    # n=2: p25 → ceil(0.25*2)-1 = ceil(0.5)-1 = 1-1 = 0 → sorted[0]=10
    #       p75 → ceil(0.75*2)-1 = ceil(1.5)-1 = 2-1 = 1 → sorted[1]=90
    # IQR = 90 - 10 = 80
    store = _make_store({
        "fspbt_two": [
            (_NOW - 400, 90.0, True),
            (_NOW - 200, 10.0, True),
        ],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_two", store=store, now_ms=_NOW
    )
    assert result == 80.0, f"IQR of [10,90] = 80; got {result}"


def test_fleet_spread_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fspbt_old": [
            (_NOW - _WIN - 300, 10.0, True),
            (_NOW - _WIN - 100, 200.0, True),
        ],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_spread_by_tool_non_negative() -> None:
    """IQR is always >= 0.0."""
    _reset()
    store = _make_store({
        "fspbt_check": [(_NOW - float(d), float(v), True) for d, v in
                        [(900, 50), (700, 30), (500, 80), (300, 10), (100, 60)]],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_check", store=store, now_ms=_NOW
    )
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fspbt_rt": [
            (_NOW - float(d), float(v), True) for d, v in
            [(900, 10), (700, 20), (500, 30), (300, 40), (100, 50)]
        ],
    })
    result = get_windowed_fleet_latency_spread_ms_by_tool(
        _WIN, "fspbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 20.0
