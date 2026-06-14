"""Item 1175: get_windowed_fleet_latency_iqr_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool IQR (P75 - P25 nearest-rank) latency.
Returns float. 0.0 for unknown/empty tool.
Composition: p75_by_tool - p25_by_tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
    P25=30ms (index 2), P75=80ms (index 7), IQR=50ms
  tool_b=[5,5,5] n=3 → P25=5ms, P75=5ms, IQR=0ms
  fleet IQR pools 13 values → different from both tool IQRs.
  iqr_a=50ms kills iqr_b=0ms; kills fleet_iqr; kills always-0.
  Composition: iqr_by_tool == p75_by_tool - p25_by_tool.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_iqr_ms_by_tool,
    get_windowed_fleet_latency_p75_ms_by_tool,
    get_windowed_fleet_latency_p25_ms_by_tool,
    get_windowed_fleet_latency_iqr_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_iqr_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: iqr_a=50ms kills iqr_b=0ms; kills fleet_iqr; kills always-0."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fiqrbt_a": [
                (_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)
            ],
            "fiqrbt_b": [(_NOW - float(600 - j * 100), 5.0, True) for j in range(3)],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms_by_tool(_WIN, "fiqrbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    # P25=30ms (index 2), P75=80ms (index 7), IQR=50ms
    assert abs(result - 50.0) < 1e-9, (
        f"iqr_a=50ms; kills iqr_b=0ms/fleet_iqr/always-0; got {result}"
    )


def test_fleet_iqr_by_tool_composition_p75_minus_p25() -> None:
    """Composition: iqr_by_tool == p75_by_tool - p25_by_tool."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fiqrbt_comp": [
                (_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)
            ],
        }
    )
    iqr = get_windowed_fleet_latency_iqr_ms_by_tool(_WIN, "fiqrbt_comp", store=store, now_ms=_NOW)
    p75 = get_windowed_fleet_latency_p75_ms_by_tool(_WIN, "fiqrbt_comp", store=store, now_ms=_NOW)
    p25 = get_windowed_fleet_latency_p25_ms_by_tool(_WIN, "fiqrbt_comp", store=store, now_ms=_NOW)
    assert abs(iqr - (p75 - p25)) < 1e-9, f"iqr({iqr}) != p75({p75})-p25({p25})={p75 - p25}"


def test_fleet_iqr_by_tool_differs_from_fleet_iqr() -> None:
    """Per-tool IQR differs from fleet IQR (pooled)."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fiqrbt_diff_a": [
                (_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)
            ],
            "fiqrbt_diff_b": [(_NOW - float(600 - j * 100), 5.0, True) for j in range(3)],
        }
    )
    tool_iqr = get_windowed_fleet_latency_iqr_ms_by_tool(
        _WIN, "fiqrbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_iqr = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_iqr - fleet_iqr) > 1.0, (
        f"per-tool({tool_iqr}) should differ from fleet({fleet_iqr})"
    )


def test_fleet_iqr_by_tool_uniform_returns_zero() -> None:
    """All same latency -> IQR == 0.0."""
    _reset()
    store = _make_store(
        {
            "fiqrbt_same": [(_NOW - float(d), 5.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms_by_tool(
        _WIN, "fiqrbt_same", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_iqr_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fiqrbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_iqr_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_iqr_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_iqr_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fiqrbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms_by_tool(_WIN, "fiqrbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fiqrbt_rt": [
                (_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)
            ],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms_by_tool(_WIN, "fiqrbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
