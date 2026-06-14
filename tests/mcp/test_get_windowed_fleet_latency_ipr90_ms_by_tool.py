"""Item 1211: get_windowed_fleet_latency_ipr90_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool 90th-interpercentile range (p95 - p5) within window.
Returns float. 0.0 for unknown/empty tool or uniform distribution.
Formula: p95 - p5.

PRIMARY DISC.:
  tool_a=[10..100] n=10 → p5=10.0, p95=100.0 → IPR90=90.0
  tool_b=[100,100,...,100] n=10 → p5=p95=100 → IPR90=0.0
  IPR90_a=90.0 kills IPR90_b=0.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_ipr90_ms_by_tool,
    get_windowed_fleet_latency_percentile_p5_ms_by_tool,
    get_windowed_fleet_latency_percentile_p95_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_ipr90_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: IPR90_a=90.0 kills IPR90_b=0.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fi90bt_a": [
                (_NOW - 990 + i * 99, float(10 + i * 10), True)
                for i in range(10)  # 10ms, 20ms, ... 100ms
            ],
            "fi90bt_b": [
                (_NOW - 990 + i * 99, 100.0, True)
                for i in range(10)  # all 100ms (uniform)
            ],
        }
    )
    ipr90_a = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "fi90bt_a", store=store, now_ms=_NOW
    )
    ipr90_b = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "fi90bt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ipr90_a, float), f"expected float, got {type(ipr90_a)}"
    assert ipr90_a == 90.0, f"IPR90_a=90.0 (100.0-10.0); kills IPR90_b=0/always-0; got {ipr90_a}"
    assert ipr90_b == 0.0, f"IPR90_b=0.0 (uniform); got {ipr90_b}"


def test_fleet_ipr90_composition_identity() -> None:
    """ipr90 == p95 - p5."""
    _reset()
    store = _make_store(
        {
            "fi90bt_comp": [(_NOW - 990 + i * 99, float(10 + i * 10), True) for i in range(10)],
        }
    )
    p5 = get_windowed_fleet_latency_percentile_p5_ms_by_tool(
        _WIN, "fi90bt_comp", store=store, now_ms=_NOW
    )
    p95 = get_windowed_fleet_latency_percentile_p95_ms_by_tool(
        _WIN, "fi90bt_comp", store=store, now_ms=_NOW
    )
    ipr90 = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "fi90bt_comp", store=store, now_ms=_NOW
    )
    assert ipr90 == p95 - p5, f"ipr90={ipr90} != p95({p95})-p5({p5})"
    assert ipr90 == 90.0


def test_fleet_ipr90_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fi90bt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_ipr90_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_ipr90_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_ipr90_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fi90bt_old": [
                (_NOW - _WIN - 300, 10.0, True),
                (_NOW - _WIN - 100, 100.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "fi90bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fi90bt_rt": [(_NOW - 990 + i * 99, float(10 + i * 10), True) for i in range(10)],
        }
    )
    result = get_windowed_fleet_latency_ipr90_ms_by_tool(
        _WIN, "fi90bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 90.0
