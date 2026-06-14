"""Item 1200: get_windowed_fleet_latency_ipr80_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool 80th-interpercentile range (p90 - p10) within window.
Returns float. 0.0 for unknown/empty tool or fewer than 2 calls.
Formula: p90 - p10 (using nearest-rank percentiles).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → p90=50, p10=10 → IPR80=40.0
  tool_b=[100,100,100,100,100] → p90=p10=100 → IPR80=0.0
  IPR80_a=40.0 kills IPR80_b=0.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_ipr80_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_ipr80_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: IPR80_a=40.0 kills IPR80_b=0.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fipr_a": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
            "fipr_b": [(_NOW - float(900 - i * 150), 100.0, True) for i in range(5)],
        }
    )
    ipr_a = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_a", store=store, now_ms=_NOW)
    ipr_b = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_b", store=store, now_ms=_NOW)
    assert isinstance(ipr_a, float), f"expected float, got {type(ipr_a)}"
    assert ipr_a == 40.0, f"IPR80_a=40.0 (p90=50-p10=10); kills IPR80_b=0/always-0; got {ipr_a}"
    assert ipr_b == 0.0, f"flat latency → IPR80=0; got {ipr_b}"


def test_fleet_ipr80_by_tool_single_call_returns_zero() -> None:
    """Single call → fewer than 2 points → 0.0."""
    _reset()
    store = _make_store(
        {
            "fipr_one": [(_NOW - 500, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_one", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_ipr80_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fipr_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_ipr80_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_ipr80_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fipr_old": [
                (_NOW - _WIN - 200, 10.0, True),
                (_NOW - _WIN - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_old", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_ipr80_wider_than_iqr() -> None:
    """IPR80 >= IQR (IPR80 captures more of the distribution)."""
    _reset()
    # [10,20,30,40,50]: IQR=p75-p25=40-20=20; IPR80=p90-p10=50-10=40
    store = _make_store(
        {
            "fipr_cmp": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    ipr80 = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_cmp", store=store, now_ms=_NOW)
    # IQR=20 per earlier test
    assert ipr80 >= 20.0, f"IPR80={ipr80} should be >= IQR=20"


def test_fleet_ipr80_non_negative() -> None:
    """IPR80 is always >= 0.0."""
    _reset()
    store = _make_store(
        {
            "fipr_check": [
                (_NOW - float(d), float(v), True)
                for d, v in [(900, 50), (700, 30), (500, 80), (300, 10), (100, 60)]
            ],
        }
    )
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(
        _WIN, "fipr_check", store=store, now_ms=_NOW
    )
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fipr_rt": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    result = get_windowed_fleet_latency_ipr80_ms_by_tool(_WIN, "fipr_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 40.0
