"""Item 1183: get_windowed_fleet_latency_cv_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool coefficient of variation (stddev / mean) of latency.
Returns float. 0.0 for unknown/empty tool or when mean == 0.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → mean=30ms, population_stddev=14.142ms, cv≈0.4714
  tool_b=[100,100,100]    → mean=100ms, stddev=0ms, cv=0.0
  cv_a≈0.4714 kills cv_b=0.0; kills always-0.
  CV is dimensionless: stddev / mean.
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_cv_by_tool,
    get_windowed_fleet_latency_stddev_ms_by_tool,
    get_windowed_fleet_latency_mean_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_cv_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: cv_a≈0.4714 kills cv_b=0.0; kills always-0."""
    _reset()
    store = _make_store({
        "fcvbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
            (_NOW - 600, 40.0, True),
            (_NOW - 500, 50.0, True),
        ],
        "fcvbt_b": [
            (_NOW - 400, 100.0, True),
            (_NOW - 300, 100.0, True),
            (_NOW - 200, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    # mean=30, population stddev = sqrt(((10-30)^2+(20-30)^2+(30-30)^2+(40-30)^2+(50-30)^2)/5)
    # = sqrt((400+100+0+100+400)/5) = sqrt(200) = 14.142...
    expected = math.sqrt(200.0) / 30.0
    assert abs(result - expected) < 1e-9, (
        f"cv_a≈{expected:.4f}; kills cv_b=0.0/always-0; got {result}"
    )


def test_fleet_cv_by_tool_composition_stddev_over_mean() -> None:
    """Composition: cv == stddev / mean (when mean > 0)."""
    _reset()
    store = _make_store({
        "fcvbt_comp": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
            (_NOW - 600, 40.0, True),
        ],
    })
    cv = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_comp", store=store, now_ms=_NOW)
    stddev = get_windowed_fleet_latency_stddev_ms_by_tool(_WIN, "fcvbt_comp", store=store, now_ms=_NOW)
    mean = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fcvbt_comp", store=store, now_ms=_NOW)
    assert mean > 0
    assert abs(cv - stddev / mean) < 1e-9, (
        f"cv({cv}) != stddev({stddev})/mean({mean})={stddev/mean}"
    )


def test_fleet_cv_by_tool_uniform_returns_zero() -> None:
    """All same latency → stddev=0 → cv=0.0."""
    _reset()
    store = _make_store({
        "fcvbt_same": [(_NOW - float(d), 100.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_same", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_cv_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fcvbt_other": [(_NOW - 500, 10.0, True)],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_cv_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_cv_by_tool_single_record_returns_zero() -> None:
    """Single record: stddev=0 (< 2 required) → cv=0.0."""
    _reset()
    store = _make_store({
        "fcvbt_one": [(_NOW - 500, 75.0, True)],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_one", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_cv_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fcvbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fcvbt_rt": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
    })
    result = get_windowed_fleet_latency_cv_by_tool(_WIN, "fcvbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # mean=20, stddev=sqrt(((10-20)^2+(20-20)^2+(30-20)^2)/3)=sqrt(200/3)
    expected = math.sqrt(200.0 / 3.0) / 20.0
    assert abs(result - expected) < 1e-9
