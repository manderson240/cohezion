"""Item 1064: get_windowed_tool_latency_percentile_at_budget_ms(tool_name, window_ms, budget_ms, *, store=None, now_ms=None) -> float
-- per-tool fraction of calls within budget (empirical CDF at budget_ms).

Returns what fraction [0,1] of windowed calls have latency <= budget_ms.
0.0 for empty window. Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,50,60,70,80,90,100] n=10, budget_ms=50
  count_within = 5 (10,20,30,40,50 -- boundary inclusive)
  fraction = 5/10 = 0.5
  (PRIMARY DISC.: kills count_within=4 (boundary 50 not counted -- wrong);
   kills sum-based=sum(<=50)/sum(all)=150/550≈0.273 (counts latency not calls);
   correct empirical_CDF = 5/10 = 0.5).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_percentile_at_budget_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_percentile_at_budget_primary_discriminator() -> None:
    """PRIMARY DISC.: [10..100] n=10, budget=50 -> fraction=5/10=0.5.

    Kills boundary-exclusive count=4/10=0.4.
    Kills sum-based=150/550≈0.273.
    Correct: boundary-inclusive count=5, fraction=0.5.
    """
    _reset()
    store = _make_store({
        "pab_disc": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
    })
    result = get_windowed_tool_latency_percentile_at_budget_ms(
        "pab_disc", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, (
        f"fraction=5/10=0.5; kills boundary-excl=0.4; kills sum-based≈0.273; got {result}"
    )


def test_all_within_budget_returns_one() -> None:
    """All lats < budget -> fraction=1.0."""
    _reset()
    store = _make_store({
        "pab_all": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
    })
    result = get_windowed_tool_latency_percentile_at_budget_ms(
        "pab_all", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all within -> 1.0; got {result}"


def test_none_within_budget_returns_zero_fraction() -> None:
    """All lats > budget -> fraction=0.0."""
    _reset()
    store = _make_store({
        "pab_none": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_tool_latency_percentile_at_budget_ms(
        "pab_none", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"none within -> 0.0; got {result}"


def test_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_percentile_at_budget_ms(
        "no_tool", _WIN, 100.0, store={}, now_ms=_NOW
    ) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "pab_old": [(_NOW - _WIN - 100, 10.0, True)] * 5,
    })
    assert get_windowed_tool_latency_percentile_at_budget_ms(
        "pab_old", _WIN, 100.0, store=store, now_ms=_NOW
    ) == 0.0


def test_fraction_in_range_zero_to_one() -> None:
    """Result always in [0, 1]."""
    _reset()
    store = _make_store({
        "pab_range": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]],
    })
    result = get_windowed_tool_latency_percentile_at_budget_ms(
        "pab_range", _WIN, 75.0, store=store, now_ms=_NOW
    )
    assert 0.0 <= result <= 1.0, f"fraction must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"pab_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_tool_latency_percentile_at_budget_ms("pab_rt", _WIN, 30.0, store=store, now_ms=_NOW),
        float,
    )
