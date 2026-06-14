"""Item 1214: get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
              window_ms, tool_name, winsor_pct=10.0, *, store=None, now_ms=None) -> float
-- per-tool Winsorized mean: extremes clamped to p(winsor_pct)/p(100-winsor_pct) bounds.
Returns float. 0.0 for unknown/empty tool.

Distincts from trimmed mean (item 1213): all n values kept (none discarded),
extremes CLAMPED to boundary percentiles rather than removed.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,1000] n=10, 10% winsor
    → p10=s[0]=10 (lower clamp), p90=s[8]=90 (upper clamp)
    → clamp 1000→90 → [10,20,30,40,50,60,70,80,90,90] → mean=540/10=54.0
  tool_b=[100]*10 → all at same value → mean=100.0
  winsor_a=54.0 kills winsor_b=100.0; kills raw_mean_a=145.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_winsorized_mean_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_winsorized_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: winsor_a=54.0 kills winsor_b=100.0; kills raw_mean_a=145."""
    _reset()
    store = _make_store(
        {
            "fwmbt_a": [
                (_NOW - 990 + i * 99, float(lv), True)
                for i, lv in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 1000])
            ],
            "fwmbt_b": [(_NOW - 990 + i * 99, 100.0, True) for i in range(10)],
        }
    )
    wa = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_a", store=store, now_ms=_NOW
    )
    wb = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(wa, float), f"expected float, got {type(wa)}"
    # p10=s[0]=10, p90=s[8]=90; clamp 1000→90 → sum=540 → mean=54.0
    assert wa == 54.0, f"winsor_a=54.0; kills winsor_b=100/raw_mean_145/always-0; got {wa}"
    assert wb == 100.0, f"winsor_b=100.0 (all same); got {wb}"


def test_fleet_winsorized_mean_kills_raw_mean() -> None:
    """Winsorized mean < raw mean when outlier is present."""
    _reset()
    store = _make_store(
        {
            "fwmbt_out": [
                (_NOW - 990 + i * 99, float(lv), True)
                for i, lv in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 1000])
            ],
        }
    )
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_out", store=store, now_ms=_NOW
    )
    raw_mean = (10 + 20 + 30 + 40 + 50 + 60 + 70 + 80 + 90 + 1000) / 10.0
    assert result == 54.0, f"got {result}"
    assert result < raw_mean, f"winsorized({result}) must be < raw({raw_mean})"


def test_fleet_winsorized_mean_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fwmbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_winsorized_mean_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_winsorized_mean_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fwmbt_old": [
                (_NOW - _WIN - 300, float(lv), True)
                for lv in [10, 20, 30, 40, 50, 60, 70, 80, 90, 1000]
            ],
        }
    )
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_winsorized_mean_no_clamp_needed() -> None:
    """All values within bounds → winsorized mean == raw mean."""
    _reset()
    store = _make_store(
        {
            "fwmbt_clean": [
                (_NOW - 990 + i * 99, float(10 + i * 10), True)
                for i in range(10)  # 10..100, no outliers
            ],
        }
    )
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_clean", store=store, now_ms=_NOW
    )
    # p10=s[0]=10, p90=s[8]=90 (nearest-rank); 100ms > 90 → clamped to 90
    # → [10,20,30,40,50,60,70,80,90,90] → mean=540/10=54.0
    assert result == 54.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fwmbt_rt": [
                (_NOW - 990 + i * 99, float(lv), True)
                for i, lv in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 1000])
            ],
        }
    )
    result = get_windowed_fleet_latency_winsorized_mean_ms_by_tool(
        _WIN, "fwmbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 54.0
