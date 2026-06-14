"""Item 1025: get_windowed_tool_above_budget_call_rate(tool_name, window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- fraction of calls exceeding budget in window.

rate = count(lat > budget_ms) / total_count
0.0 for unknown/empty tool. Injectable store. Pure function.
Complements item-1023 (excess sum) with a rate/fraction view of SLA breaches.
Strictly > (not >=): boundary calls at exactly budget_ms do NOT count as violations.

PRIMARY DISC.: lats [50, 150, 200, 300] budget=100
  above = [150, 200, 300] -> 3 of 4 -> rate=0.75
  (kills count=3 int; kills excess_sum=350 float; correct rate=0.75 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_above_budget_call_rate,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_above_budget_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: [50, 150, 200, 300] budget=100 -> rate=0.75.

    Kills count=3 (int, wrong type).
    Kills excess_sum=350.0 (float but wrong value).
    Correct: 3/4 = 0.75.
    """
    _reset()
    store = _make_store(
        {
            "abr_a": [(_NOW - 10, float(v), True) for v in [50, 150, 200, 300]],
        }
    )
    result = get_windowed_tool_above_budget_call_rate(
        "abr_a", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 0.75) < 1e-9, (
        f"rate=0.75 (3/4 above budget); kills count=3 or excess=350; got {result}"
    )


def test_none_above_budget_returns_zero() -> None:
    """All lats at/below budget -> 0.0 (0/N)."""
    _reset()
    store = _make_store(
        {
            "abr_below": [(_NOW - 10, float(v), True) for v in [10, 50, 99, 100]],
        }
    )
    result = get_windowed_tool_above_budget_call_rate(
        "abr_below", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"all at/below budget -> rate=0.0; got {result}"


def test_exactly_at_budget_boundary_not_counted() -> None:
    """Calls exactly at budget_ms are NOT above budget (strictly >)."""
    _reset()
    store = _make_store(
        {
            "abr_exact": [(_NOW - 10, 100.0, True), (_NOW - 20, 200.0, True)],
        }
    )
    result = get_windowed_tool_above_budget_call_rate(
        "abr_exact", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 0.5) < 1e-9, f"only 200>100: rate=0.5; got {result}"


def test_all_above_budget_returns_one() -> None:
    """All calls above budget -> rate=1.0."""
    _reset()
    store = _make_store(
        {
            "abr_all": [(_NOW - 10, float(v), True) for v in [200, 300, 400]],
        }
    )
    result = get_windowed_tool_above_budget_call_rate(
        "abr_all", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all above budget -> rate=1.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_above_budget_call_rate("no_such_abr", _WIN, 100.0, store={}, now_ms=_NOW)
        == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "abr_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_above_budget_call_rate("abr_old", _WIN, 100.0, store=store, now_ms=_NOW)
        == 0.0
    )


def test_includes_failed_calls_in_denominator() -> None:
    """Failed calls count toward total (rate = above/total regardless of success)."""
    _reset()
    store = _make_store(
        {
            "abr_fail": [
                (_NOW - 10, 50.0, True),  # below budget
                (_NOW - 20, 200.0, False),  # above budget AND failed
                (_NOW - 30, 300.0, True),  # above budget
            ],
        }
    )
    result = get_windowed_tool_above_budget_call_rate(
        "abr_fail", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 2.0 / 3.0) < 1e-9, f"2/3 above budget (includes failed); got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"abr_rt": [(_NOW - 10, float(v), True) for v in [50, 150, 200]]})
    assert isinstance(
        get_windowed_tool_above_budget_call_rate("abr_rt", _WIN, 100.0, store=store, now_ms=_NOW),
        float,
    )
