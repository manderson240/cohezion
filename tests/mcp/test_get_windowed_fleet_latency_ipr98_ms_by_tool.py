"""Item 1217: get_windowed_fleet_latency_ipr98_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool 98th-interpercentile range (p99 - p1) within window.
Returns float. 0.0 for unknown/empty tool.
Formula: p99_by_tool - p1_by_tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
    → p1=10.0 (idx 0), p99=100.0 (idx 9) → IPR98=90.0
  tool_b=[100,100,...,100] n=10
    → p1=p99=100.0 → IPR98=0.0
  IPR98_a=90.0 kills IPR98_b=0.0; kills always-0.
  Composition: ipr98 == p99_by_tool - p1_by_tool.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_ipr98_ms_by_tool,
    get_windowed_fleet_latency_percentile_p1_ms_by_tool,
    get_windowed_fleet_latency_percentile_p99_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_ipr98_primary_discriminator() -> None:
    """PRIMARY DISC.: IPR98_a=90.0 kills IPR98_b=0.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fi98bt_a": [
                (_NOW - 990 + i * 99, float(10 + i * 10), True)
                for i in range(10)  # 10,20,...,100
            ],
            "fi98bt_b": [(_NOW - 990 + i * 99, 100.0, True) for i in range(10)],
        }
    )
    ia = get_windowed_fleet_latency_ipr98_ms_by_tool(_WIN, "fi98bt_a", store=store, now_ms=_NOW)
    ib = get_windowed_fleet_latency_ipr98_ms_by_tool(_WIN, "fi98bt_b", store=store, now_ms=_NOW)
    assert isinstance(ia, float), f"expected float, got {type(ia)}"
    # p1=10.0 (idx 0), p99=100.0 (idx 9) → IPR98=90.0
    assert ia == 90.0, f"IPR98_a=90.0; kills IPR98_b=0.0/always-0; got {ia}"
    assert ib == 0.0, f"IPR98_b=0.0 (uniform); got {ib}"


def test_fleet_ipr98_composition() -> None:
    """IPR98 == p99_by_tool - p1_by_tool."""
    _reset()
    store = _make_store(
        {
            "fi98bt_comp": [(_NOW - 990 + i * 99, float(10 + i * 10), True) for i in range(10)],
        }
    )
    ipr98 = get_windowed_fleet_latency_ipr98_ms_by_tool(
        _WIN, "fi98bt_comp", store=store, now_ms=_NOW
    )
    p1 = get_windowed_fleet_latency_percentile_p1_ms_by_tool(
        _WIN, "fi98bt_comp", store=store, now_ms=_NOW
    )
    p99 = get_windowed_fleet_latency_percentile_p99_ms_by_tool(
        _WIN, "fi98bt_comp", store=store, now_ms=_NOW
    )
    assert abs(ipr98 - (p99 - p1)) < 1e-9, (
        f"ipr98={ipr98} should equal p99({p99})-p1({p1})={p99 - p1}"
    )


def test_fleet_ipr98_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fi98bt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_ipr98_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_ipr98_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_ipr98_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_ipr98_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fi98bt_old": [(_NOW - _WIN - 300, float(10 + i * 10), True) for i in range(10)],
        }
    )
    result = get_windowed_fleet_latency_ipr98_ms_by_tool(
        _WIN, "fi98bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fi98bt_rt": [(_NOW - 990 + i * 99, float(10 + i * 10), True) for i in range(10)],
        }
    )
    result = get_windowed_fleet_latency_ipr98_ms_by_tool(
        _WIN, "fi98bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 90.0
