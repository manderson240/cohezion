"""Item 1219: get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool harmonic mean latency within window.
Formula: n / sum(1/lat_i). Returns float. 0.0 for unknown/empty tool or any lat==0.
Always <= geometric mean <= arithmetic mean (equality iff all values identical).

PRIMARY DISC.:
  tool_a=[1,2,4] → harm = 3/(1 + 0.5 + 0.25) = 3/1.75 ≈ 1.714...
  tool_b=[100,100,100] → harm=100.0
  harm_a≈1.714 kills harm_b=100.0; kills arith_mean_a≈2.333; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_harmonic_mean_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_harmonic_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: harm_a≈1.714 kills harm_b=100.0; kills arith_mean_a≈2.333; kills always-0."""
    _reset()
    store = _make_store({
        "fhmbt_a": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 2.0, True),
            (_NOW - 300, 4.0, True),
        ],
        "fhmbt_b": [
            (_NOW - 700, 100.0, True),
            (_NOW - 500, 100.0, True),
            (_NOW - 300, 100.0, True),
        ],
    })
    ha = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_a", store=store, now_ms=_NOW
    )
    hb = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ha, float), f"expected float, got {type(ha)}"
    # 3/(1+0.5+0.25) = 3/1.75 = 12/7
    expected_a = 12.0 / 7.0
    assert abs(ha - expected_a) < 1e-9, (
        f"harm_a={expected_a:.6f}; kills harm_b=100.0/arith=2.333/always-0; got {ha}"
    )
    assert abs(hb - 100.0) < 1e-9, f"harm_b=100.0 (uniform); got {hb}"


def test_fleet_harmonic_mean_less_than_arithmetic() -> None:
    """Harmonic mean < arithmetic mean for non-uniform distributions."""
    _reset()
    store = _make_store({
        "fhmbt_cmp": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 2.0, True),
            (_NOW - 300, 4.0, True),
        ],
    })
    harm = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_cmp", store=store, now_ms=_NOW
    )
    arith = (1.0 + 2.0 + 4.0) / 3.0
    assert harm < arith, f"harm({harm}) must be < arith({arith})"


def test_fleet_harmonic_mean_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fhmbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_harmonic_mean_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_harmonic_mean_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fhmbt_old": [
            (_NOW - _WIN - 300, float(v), True)
            for v in [1.0, 2.0, 4.0]
        ],
    })
    result = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_harmonic_mean_single_call() -> None:
    """Single call → that latency."""
    _reset()
    store = _make_store({
        "fhmbt_one": [(_NOW - 500, 42.0, True)],
    })
    result = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_one", store=store, now_ms=_NOW
    )
    assert abs(result - 42.0) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fhmbt_rt": [
            (_NOW - 700, 1.0, True),
            (_NOW - 500, 2.0, True),
            (_NOW - 300, 4.0, True),
        ],
    })
    result = get_windowed_fleet_latency_harmonic_mean_ms_by_tool(
        _WIN, "fhmbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    expected = 12.0 / 7.0
    assert abs(result - expected) < 1e-9, f"expected {expected}, got {result}"
