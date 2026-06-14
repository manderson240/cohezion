"""Item 1024: get_windowed_global_latency_above_budget_ms(window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- fleet-wide total excess latency above SLA budget.

global_excess = sum(max(0, lat - budget_ms) for ALL tools in window)

0.0 for empty store. Injectable store. Pure function.
Fleet-wide dual of item-1023 (per-tool above-budget).

PRIMARY DISC.: tool_a lats [50, 150] + tool_b lats [200, 300], budget=100
  tool_a excess = [0, 50]   -> tool_a_sum = 50
  tool_b excess = [100, 200] -> tool_b_sum = 300
  global_excess = 50 + 300 = 350.0
  (kills per-tool-a=50.0; kills per-tool-b=300.0; correct pooled=350.0 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_above_budget_ms,
    get_windowed_tool_latency_above_budget_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_above_budget_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[50,150] + tool_b[200,300] budget=100 -> global_excess=350.0.

    Kills per-tool-a=50.0 (not pooled).
    Kills per-tool-b=300.0 (not pooled).
    Correct: (0+50) + (100+200) = 350.0.
    """
    _reset()
    store = _make_store(
        {
            "gb_a": [(_NOW - 10, float(v), True) for v in [50, 150]],
            "gb_b": [(_NOW - 10, float(v), True) for v in [200, 300]],
        }
    )
    result = get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 350.0) < 1e-9, (
        f"global_excess=350.0; kills tool_a=50 or tool_b=300; got {result}"
    )


def test_single_tool_matches_per_tool_above_budget() -> None:
    """With one tool, global == per-tool."""
    _reset()
    store = _make_store(
        {
            "gb_one": [(_NOW - 10, float(v), True) for v in [50, 150, 300]],
        }
    )
    global_exc = get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW)
    per_tool_exc = get_windowed_tool_latency_above_budget_ms(
        "gb_one", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(global_exc - per_tool_exc) < 1e-9, (
        f"single tool: global={global_exc} must equal per_tool={per_tool_exc}"
    )


def test_all_below_budget_returns_zero() -> None:
    """All lats across all tools at/below budget -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gb_low1": [(_NOW - 10, 80.0, True), (_NOW - 10, 100.0, True)],
            "gb_low2": [(_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0.0, f"all at/below budget -> 0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gb_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gb_rt": [(_NOW - 10, float(v), True) for v in [50, 200, 300]]})
    assert isinstance(
        get_windowed_global_latency_above_budget_ms(_WIN, 100.0, store=store, now_ms=_NOW), float
    )


def test_zero_budget_equals_global_latency_sum() -> None:
    """budget=0.0 -> every lat is excess; global_excess == global_sum."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_latency_sum_ms

    _reset()
    store = _make_store(
        {
            "gb_zb_a": [(_NOW - 10, float(v), True) for v in [10, 50]],
            "gb_zb_b": [(_NOW - 10, float(v), True) for v in [200, 300]],
        }
    )
    exc = get_windowed_global_latency_above_budget_ms(_WIN, 0.0, store=store, now_ms=_NOW)
    total = get_windowed_global_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(exc - total) < 1e-9, f"budget=0: excess={exc} must equal total_sum={total}"
