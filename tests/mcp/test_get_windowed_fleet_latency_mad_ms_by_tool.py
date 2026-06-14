"""Item 1202: get_windowed_fleet_latency_mad_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool Median Absolute Deviation (MAD) of latency within window.
Returns float. 0.0 for unknown/empty tool or fewer than 2 calls.
Formula: median(|lat_i - median(lats)|).
Robust scale estimator: outliers do not inflate MAD unless they exceed
more than half the distribution.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → median=30, deviations=[20,10,0,10,20] → MAD=10.0
  tool_b=[10,10,10,10,100] → median=10, deviations=[0,0,0,0,90] → MAD=0.0
  MAD_a=10.0 kills MAD_b=0.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mad_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mad_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: MAD_a=10.0 kills MAD_b=0.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fmad_a": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
            "fmad_b": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 10, 10, 10, 100])
            ],
        }
    )
    mad_a = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_a", store=store, now_ms=_NOW)
    mad_b = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_b", store=store, now_ms=_NOW)
    assert isinstance(mad_a, float), f"expected float, got {type(mad_a)}"
    assert mad_a == 10.0, (
        f"MAD_a=10.0 (median_dev of [20,10,0,10,20]=10); kills MAD_b=0/always-0; got {mad_a}"
    )
    assert mad_b == 0.0, f"MAD_b=0.0 (4 zeros dominate median of devs); got {mad_b}"


def test_fleet_mad_by_tool_single_call_returns_zero() -> None:
    """Single call → fewer than 2 points → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_one": [(_NOW - 500, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_one", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_mad_by_tool_uniform_returns_zero() -> None:
    """All same latency → all deviations=0 → MAD=0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_flat": [(_NOW - float(d), 42.0, True) for d in [900, 600, 300]],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_flat", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_mad_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_mad_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_mad_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_old": [
                (_NOW - _WIN - 200, 10.0, True),
                (_NOW - _WIN - 100, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_old", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_mad_non_negative() -> None:
    """MAD is always >= 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_check": [
                (_NOW - float(d), float(v), True)
                for d, v in [(900, 50), (700, 30), (500, 80), (300, 10), (100, 60)]
            ],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_check", store=store, now_ms=_NOW)
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmad_rt": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    result = get_windowed_fleet_latency_mad_ms_by_tool(_WIN, "fmad_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 10.0
