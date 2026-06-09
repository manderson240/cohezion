"""Item 1184: get_windowed_fleet_latency_skewness_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency skewness (third standardised moment).
Returns float. 0.0 for unknown/empty tool or when stddev == 0.
Formula: sum((x - mean)^3) / (n * stddev^3).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → symmetric → skewness_a = 0.0
  tool_b=[10,10,10,100]   → right-skewed → skewness_b ≈ 1.1547
  skewness_b > 0 kills skewness_a = 0.0; kills always-0.
  Positive skew = rare slow outliers dominating the tail.
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_skewness_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_skewness_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: skewness_b≈1.1547 kills skewness_a=0.0; kills always-0."""
    _reset()
    store = _make_store({
        "fskwbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
            (_NOW - 600, 40.0, True),
            (_NOW - 500, 50.0, True),
        ],
        "fskwbt_b": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 10.0, True),
            (_NOW - 200, 10.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    result_b = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_b", store=store, now_ms=_NOW)
    assert isinstance(result_b, float), f"expected float, got {type(result_b)}"
    # skewness_b ≈ 1.1547
    assert result_b > 0.5, (
        f"tool_b is right-skewed: skewness_b should be >0.5; got {result_b}"
    )
    result_a = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_a", store=store, now_ms=_NOW)
    assert abs(result_a) < 1e-9, (
        f"tool_a is symmetric: skewness_a should be 0.0; got {result_a}"
    )


def test_fleet_skewness_by_tool_exact_value_right_skewed() -> None:
    """Right-skewed [10,10,10,100] → exact skewness ≈ 1.154700538."""
    _reset()
    store = _make_store({
        "fskwbt_exact": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 10.0, True),
            (_NOW - 200, 10.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_exact", store=store, now_ms=_NOW)
    expected = 1.1547005383792515  # computed: sum((x-32.5)^3) / (4 * stddev^3)
    assert abs(result - expected) < 1e-9, f"exact skewness; got {result}"


def test_fleet_skewness_by_tool_symmetric_returns_zero() -> None:
    """Symmetric distribution [10,20,30,40,50] → skewness == 0.0."""
    _reset()
    store = _make_store({
        "fskwbt_sym": [
            (_NOW - float(d), float(lat), True)
            for d, lat in zip([900, 800, 700, 600, 500], [10, 20, 30, 40, 50])
        ],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_sym", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"symmetric → 0.0; got {result}"


def test_fleet_skewness_by_tool_uniform_returns_zero() -> None:
    """Uniform latencies → stddev=0 → skewness=0.0 (guard)."""
    _reset()
    store = _make_store({
        "fskwbt_uni": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_uni", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_skewness_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fskwbt_other": [(_NOW - 500, 10.0, True)],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_skewness_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_skewness_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_skewness_by_tool_left_skewed_is_negative() -> None:
    """Left-skewed distribution [10,100,100,100] → skewness < 0."""
    _reset()
    store = _make_store({
        "fskwbt_left": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 100.0, True),
            (_NOW - 200, 100.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(
        _WIN, "fskwbt_left", store=store, now_ms=_NOW
    )
    assert result < -0.5, f"left-skewed → negative skewness; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fskwbt_rt": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 10.0, True),
            (_NOW - 200, 10.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_skewness_by_tool(_WIN, "fskwbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
