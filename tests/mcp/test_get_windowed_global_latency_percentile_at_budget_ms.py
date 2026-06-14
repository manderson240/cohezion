"""Item 1065: get_windowed_global_latency_percentile_at_budget_ms(window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- fleet-wide fraction of calls within budget (pooled empirical CDF at budget_ms).

Pools ALL tool calls, returns fraction with latency <= budget_ms.
0.0 for empty pool. Injectable store. Pure function. Fleet dual of item 1064.

PRIMARY DISC.: tool_a=[10,20,30,40]+tool_b=[90,100] -> pooled n=6, budget_ms=50
  count_within=4 (10,20,30,40), fraction=4/6=2/3≈0.6667
  (PRIMARY DISC.: kills per-tool fraction avg:
     tool_a=4/4=1.0, tool_b=0/2=0.0, avg=0.5 != pooled 2/3;
   correct pooled fraction=4/6=2/3≈0.6667).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_percentile_at_budget_ms,
    get_windowed_tool_latency_percentile_at_budget_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_percentile_at_budget_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,20,30,40]+tool_b=[90,100] -> pooled fraction=2/3.

    Kills per-tool fraction avg: (1.0+0.0)/2=0.5 != 2/3.
    Correct: pooled count=4/6=2/3≈0.6667.
    """
    _reset()
    store = _make_store(
        {
            "gpab_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40]],
            "gpab_b": [(_NOW - 10, float(v), True) for v in [90, 100]],
        }
    )
    result = get_windowed_global_latency_percentile_at_budget_ms(
        _WIN, 50.0, store=store, now_ms=_NOW
    )
    per_a = get_windowed_tool_latency_percentile_at_budget_ms(
        "gpab_a", _WIN, 50.0, store=store, now_ms=_NOW
    )
    per_b = get_windowed_tool_latency_percentile_at_budget_ms(
        "gpab_b", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert abs((per_a + per_b) / 2 - 0.5) < 1e-9, "per-tool avg should be 0.5"
    assert isinstance(result, float)
    assert abs(result - 2 / 3) < 1e-9, f"pooled fraction=2/3; kills per-tool-avg=0.5; got {result}"


def test_all_within_budget_returns_one() -> None:
    """All pooled lats <= budget -> 1.0."""
    _reset()
    store = _make_store(
        {
            "gpab_all": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_global_latency_percentile_at_budget_ms(
        _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all within -> 1.0; got {result}"


def test_none_within_budget_returns_zero_fraction() -> None:
    """All lats > budget -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gpab_none": [(_NOW - 10, 200.0, True)] * 4,
        }
    )
    result = get_windowed_global_latency_percentile_at_budget_ms(
        _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"none within -> 0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert (
        get_windowed_global_latency_percentile_at_budget_ms(_WIN, 100.0, store={}, now_ms=_NOW)
        == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gpab_old": [(_NOW - _WIN - 100, 10.0, True)] * 4,
        }
    )
    assert (
        get_windowed_global_latency_percentile_at_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW)
        == 0.0
    )


def test_fraction_in_range_zero_to_one() -> None:
    """Result always in [0, 1]."""
    _reset()
    store = _make_store(
        {
            "gpab_range_a": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
            "gpab_range_b": [(_NOW - 10, float(v), True) for v in [200, 500]],
        }
    )
    result = get_windowed_global_latency_percentile_at_budget_ms(
        _WIN, 75.0, store=store, now_ms=_NOW
    )
    assert 0.0 <= result <= 1.0, f"fraction must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gpab_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_global_latency_percentile_at_budget_ms(_WIN, 35.0, store=store, now_ms=_NOW),
        float,
    )
