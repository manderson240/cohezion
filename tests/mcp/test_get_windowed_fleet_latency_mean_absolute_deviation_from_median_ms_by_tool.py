"""Item 1212: get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool Mean Absolute Deviation from the median (MADM) within window.
Formula: sum(|lat_i - median(lats)|) / n.
Distinct from MAD (item 1202 = MEDIAN of abs devs).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50]: median=30, devs=[20,10,0,10,20] → MADM=60/5=12.0
  tool_b=[100,100,100,100,100]: median=100, devs=[0,0,0,0,0] → MADM=0.0
  MADM_a=12.0 kills MADM_b=0.0; kills MAD_a=10.0 (different formula); kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_madm_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: MADM_a=12.0 kills MADM_b=0.0; kills MAD_a=10.0; kills always-0."""
    _reset()
    store = _make_store({
        "fmadmbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 700, 20.0, True),
            (_NOW - 500, 30.0, True),
            (_NOW - 300, 40.0, True),
            (_NOW - 100, 50.0, True),
        ],
        "fmadmbt_b": [
            (_NOW - 900, 100.0, True),
            (_NOW - 700, 100.0, True),
            (_NOW - 500, 100.0, True),
            (_NOW - 300, 100.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    madm_a = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_a", store=store, now_ms=_NOW
    )
    madm_b = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(madm_a, float), f"expected float, got {type(madm_a)}"
    # median([10,20,30,40,50])=30; devs=[20,10,0,10,20]; MADM=60/5=12.0
    assert madm_a == 12.0, (
        f"MADM_a=12.0 (mean of abs devs); kills MADM_b=0/MAD_a=10/always-0; got {madm_a}"
    )
    assert madm_b == 0.0, f"MADM_b=0.0 (uniform); got {madm_b}"


def test_fleet_madm_differs_from_mad() -> None:
    """MADM (mean of |devs|) != MAD (median of |devs|) for asymmetric distributions."""
    _reset()
    store = _make_store({
        "fmadmbt_diff": [
            (_NOW - 900, 10.0, True),
            (_NOW - 700, 20.0, True),
            (_NOW - 500, 30.0, True),
            (_NOW - 300, 40.0, True),
            (_NOW - 100, 50.0, True),
        ],
    })
    madm = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_diff", store=store, now_ms=_NOW
    )
    # MADM=12.0, MAD=10.0 (item 1202) — they differ because mean != median of devs
    assert madm == 12.0, f"MADM=12.0, not 10.0 (which would be MAD); got {madm}"


def test_fleet_madm_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fmadmbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_madm_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_madm_single_call_returns_zero() -> None:
    """Single call → deviation from itself = 0.0."""
    _reset()
    store = _make_store({
        "fmadmbt_one": [(_NOW - 500, 50.0, True)],
    })
    result = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_one", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_madm_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fmadmbt_old": [
            (_NOW - _WIN - 300, 10.0, True),
            (_NOW - _WIN - 100, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fmadmbt_rt": [
            (_NOW - 600, 10.0, True),
            (_NOW - 400, 30.0, True),
            (_NOW - 200, 50.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_absolute_deviation_from_median_ms_by_tool(
        _WIN, "fmadmbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    # median=30; devs=[20,0,20]; MADM=40/3≈13.333...
    expected = 40.0 / 3.0
    assert abs(result - expected) < 1e-9, f"expected {expected}, got {result}"
