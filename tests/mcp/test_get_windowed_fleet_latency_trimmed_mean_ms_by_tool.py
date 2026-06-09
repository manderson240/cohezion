"""Item 1213: get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
              window_ms, tool_name, trim_pct=10.0, *, store=None, now_ms=None) -> float
-- per-tool trimmed mean: mean after removing bottom+top trim_pct% of calls.
Returns float. 0.0 for unknown/empty tool or <2 remaining after trim.
Default trim_pct=10.0 (10% each end = 80% trimmed mean).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] trim=10%
    → remove 1 from each end → [20..90] n=8 → mean=55.0
  tool_b=[10,10,...,10,1000] trim=10%
    → removes 1000 (outlier) → trimmed=[10]*8 → mean=10.0
  trimmed_a=55.0 kills trimmed_b=10.0; kills untrimmed_a≈55 (actually ==55 here);
  kills always-0. Outlier guard: raw mean of b = 109 vs trimmed_b = 10.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_trimmed_mean_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_trimmed_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: trimmed_a=55.0 kills trimmed_b=10.0; kills outlier-inflated b_raw."""
    _reset()
    store = _make_store({
        "ftmbt_a": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10ms, 20ms, ... 100ms
        ],
        "ftmbt_b": [
            (_NOW - 990 + i * 99, 10.0, True)
            for i in range(9)  # nine 10ms calls
        ] + [(_NOW - 99, 1000.0, True)],  # one 1000ms outlier
    })
    ta = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_a", store=store, now_ms=_NOW
    )
    tb = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ta, float), f"expected float, got {type(ta)}"
    # n=10, 10% trim → k=1, remove [10ms] + [100ms] → [20..90] mean=55.0
    assert ta == 55.0, (
        f"trimmed_a=55.0; kills trimmed_b=10.0/always-0; got {ta}"
    )
    # n=10, trim removes 1000ms outlier → [10]*8 mean=10.0
    assert tb == 10.0, f"trimmed_b=10.0 (outlier removed); got {tb}"


def test_fleet_trimmed_mean_outlier_removal() -> None:
    """Trimming removes the outlier → trimmed mean << raw mean."""
    _reset()
    store = _make_store({
        "ftmbt_out": [
            (_NOW - 990 + i * 99, 10.0, True)
            for i in range(9)
        ] + [(_NOW - 99, 9999.0, True)],  # massive outlier
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_out", store=store, now_ms=_NOW
    )
    # trim removes 9999 → [10]*8 → mean=10.0
    assert result == 10.0, f"outlier trimmed; got {result}"
    assert result < 100.0, "trimmed mean must be << raw mean (1008ms)"


def test_fleet_trimmed_mean_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "ftmbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_trimmed_mean_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_trimmed_mean_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "ftmbt_old": [
            (_NOW - _WIN - 300, float(10 + i * 10), True)
            for i in range(10)
        ],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_trimmed_mean_custom_trim_pct() -> None:
    """Custom trim_pct=20% removes 2 from each end of n=10."""
    _reset()
    store = _make_store({
        "ftmbt_cust": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)  # 10..100
        ],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_cust", trim_pct=20.0, store=store, now_ms=_NOW
    )
    # 20% of 10 = 2; remove [10,20] + [90,100] → [30,40,50,60,70,80] mean=55.0
    assert result == 55.0, f"20% trim; mean of [30..80]=55.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "ftmbt_rt": [
            (_NOW - 990 + i * 99, float(10 + i * 10), True)
            for i in range(10)
        ],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms_by_tool(
        _WIN, "ftmbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 55.0
