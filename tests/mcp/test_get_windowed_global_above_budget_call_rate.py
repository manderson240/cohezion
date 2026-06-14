"""Item 1026: get_windowed_global_above_budget_call_rate(window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- fleet-wide SLA breach rate.

global_rate = count(lat > budget_ms across ALL tools) / total_count_across_all_tools

0.0 for empty store. Injectable store. Pure function.
Fleet-wide dual of item-1025 (per-tool above-budget rate).
Pools ALL calls (not average of per-tool rates).

PRIMARY DISC.: tool_a lats [100, 200] + tool_b lats [200] budget=100
  pooled above = [200, 200] -> count=2
  pooled total = [100, 200, 200] -> count=3
  global_rate = 2/3 ≈ 0.6667
  (kills avg-per-tool=(0.5+1.0)/2=0.75; kills count=2 int; correct pooled=0.6667 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_above_budget_call_rate,
    get_windowed_tool_above_budget_call_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_above_budget_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[100,200] + tool_b[200] budget=100 -> global_rate=2/3≈0.6667.

    Kills avg-per-tool=(0.5+1.0)/2=0.75 (naive average, not pooled).
    Kills count=2 (int, wrong type).
    Correct: pooled above=2, pooled total=3 -> 0.6667.
    """
    _reset()
    store = _make_store(
        {
            "gbr_a": [(_NOW - 10, float(v), True) for v in [100, 200]],
            "gbr_b": [(_NOW - 10, 200.0, True)],
        }
    )
    result = get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 2.0 / 3.0) < 1e-9, (
        f"global_rate=2/3≈0.6667; kills avg-per-tool=0.75 or count=2; got {result}"
    )


def test_single_tool_matches_per_tool_rate() -> None:
    """With one tool, global rate == per-tool rate."""
    _reset()
    store = _make_store(
        {
            "gbr_one": [(_NOW - 10, float(v), True) for v in [50, 150, 200, 300]],
        }
    )
    global_rate = get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    per_tool_rate = get_windowed_tool_above_budget_call_rate(
        "gbr_one", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(global_rate - per_tool_rate) < 1e-9, (
        f"single tool: global={global_rate} must equal per_tool={per_tool_rate}"
    )


def test_all_below_budget_returns_zero() -> None:
    """All lats at/below budget across all tools -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gbr_low1": [(_NOW - 10, 80.0, True), (_NOW - 10, 100.0, True)],
            "gbr_low2": [(_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0.0, f"all at/below budget -> rate=0.0; got {result}"


def test_all_above_budget_returns_one() -> None:
    """All calls above budget -> rate=1.0."""
    _reset()
    store = _make_store(
        {
            "gbr_all1": [(_NOW - 10, 200.0, True), (_NOW - 10, 300.0, True)],
            "gbr_all2": [(_NOW - 10, 500.0, True)],
        }
    )
    result = get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all above budget -> rate=1.0; got {result}"


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_above_budget_call_rate(_WIN, 100.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gbr_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
        }
    )
    assert get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gbr_rt": [(_NOW - 10, float(v), True) for v in [50, 200, 300]]})
    assert isinstance(
        get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW), float
    )


def test_pooled_vs_naive_average_differ() -> None:
    """Pooled rate != naive average of per-tool rates when tools have different call counts."""
    _reset()
    # tool_c has 9 calls all below budget (rate=0.0)
    # tool_d has 1 call above budget (rate=1.0)
    # naive average = (0.0+1.0)/2 = 0.5
    # pooled: 1 above / 10 total = 0.1
    store = _make_store(
        {
            "gbr_c": [(_NOW - 10, 50.0, True)] * 9,
            "gbr_d": [(_NOW - 10, 200.0, True)],
        }
    )
    result = get_windowed_global_above_budget_call_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 0.1) < 1e-9, (
        f"pooled=0.1 (not naive_avg=0.5); validates pooling; got {result}"
    )
