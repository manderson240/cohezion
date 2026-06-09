"""Item 1023: get_windowed_tool_latency_above_budget_ms(tool_name, window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- total excess latency above SLA budget.

excess_sum = sum(max(0, latency_ms - budget_ms) for all calls in window)
0.0 for empty/unknown tool or all calls at/below budget.
Injectable store. Pure function.
Measures total latency "debt" above SLA — not just count of violating calls.

PRIMARY DISC.: lats [50, 150, 300] budget=100
  excess = [max(0,50-100), max(0,150-100), max(0,300-100)] = [0, 50, 200]
  sum = 250.0
  (kills count_above_budget=2 int; kills sum_all_lats=500 float;
   kills max_lat=300 float; correct excess_sum=250.0 float).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_above_budget_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_above_budget_primary_discriminator() -> None:
    """PRIMARY DISC.: [50, 150, 300] budget=100 -> excess_sum=250.0.

    Kills count_above_budget=2 (int, wrong value).
    Kills sum_all_lats=500 (float, wrong value).
    Kills max_lat=300 (float, wrong value).
    Correct: 0+50+200 = 250.0.
    """
    _reset()
    store = _make_store({
        "ab_a": [(_NOW - 10, float(v), True) for v in [50, 150, 300]],
    })
    result = get_windowed_tool_latency_above_budget_ms("ab_a", _WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 250.0) < 1e-9, (
        f"excess_sum=250.0; kills count=2 or total=500 or max=300; got {result}"
    )


def test_all_below_budget_returns_zero() -> None:
    """All lats at or below budget -> 0.0 (no debt)."""
    _reset()
    store = _make_store({
        "ab_below": [(_NOW - 10, float(v), True) for v in [10, 50, 99, 100]],
    })
    result = get_windowed_tool_latency_above_budget_ms("ab_below", _WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0.0, f"all at/below budget -> 0.0; got {result}"


def test_exactly_at_budget_boundary_is_not_excess() -> None:
    """Latency exactly equal to budget_ms contributes 0 excess (not strictly above)."""
    _reset()
    store = _make_store({
        "ab_exact": [(_NOW - 10, 100.0, True)],
    })
    result = get_windowed_tool_latency_above_budget_ms("ab_exact", _WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0.0, f"lat==budget -> 0 excess; got {result}"


def test_single_violation_returns_exact_excess() -> None:
    """Single call above budget -> exact excess."""
    _reset()
    store = _make_store({
        "ab_one": [(_NOW - 10, 350.0, True)],
    })
    result = get_windowed_tool_latency_above_budget_ms("ab_one", _WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 250.0) < 1e-9, f"350-100=250.0 excess; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_above_budget_ms("no_such_ab", _WIN, 100.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "ab_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
    })
    assert get_windowed_tool_latency_above_budget_ms("ab_old", _WIN, 100.0, store=store, now_ms=_NOW) == 0.0


def test_includes_failed_calls() -> None:
    """Failed calls also contribute excess latency (budget is about time, not success)."""
    _reset()
    store = _make_store({
        "ab_fail": [
            (_NOW - 10, 50.0, True),    # 0 excess
            (_NOW - 20, 200.0, False),  # 100 excess (failed but slow)
            (_NOW - 30, 400.0, True),   # 300 excess
        ],
    })
    result = get_windowed_tool_latency_above_budget_ms("ab_fail", _WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 400.0) < 1e-9, f"0+100+300=400.0 (includes failed); got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"ab_rt": [(_NOW - 10, float(v), True) for v in [50, 200, 300]]})
    assert isinstance(
        get_windowed_tool_latency_above_budget_ms("ab_rt", _WIN, 100.0, store=store, now_ms=_NOW), float
    )


def test_zero_budget_excess_equals_total_sum() -> None:
    """budget=0.0 -> every latency is excess; excess_sum == total_sum."""
    _reset()
    store = _make_store({
        "ab_zero_budget": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
    })
    result = get_windowed_tool_latency_above_budget_ms(
        "ab_zero_budget", _WIN, 0.0, store=store, now_ms=_NOW
    )
    assert abs(result - 260.0) < 1e-9, f"budget=0: excess==total=260.0; got {result}"
