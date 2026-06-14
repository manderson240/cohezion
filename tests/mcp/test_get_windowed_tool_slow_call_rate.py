"""Item 1004: get_windowed_tool_slow_call_rate(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> float
-- fraction of calls with latency_ms > threshold_ms in window.

SLO violation rate: slow_call_count / total_call_count. Returns float in [0.0, 1.0].
0.0 for unknown/no-recent. Strictly greater than (not >=) for the slow predicate.

PRIMARY DISC.: lats [10, 50, 200, 300] with threshold=100 -> 0.5
  (2 slow / 4 total = 0.5; kills slow_count=2; kills total_count=4; rate=0.5 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_slow_call_rate,
    get_windowed_tool_slow_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_slow_call_rate_primary_discriminator() -> None:
    """FALSIFIABLE: [10,50,200,300] threshold=100 -> 0.5 (not 2, not 4, not 0.25).

    2 slow / 4 total = 0.5.
    Kills impl returning slow_count int (=2).
    Kills impl returning total_count int (=4).
    """
    _reset()
    store = _make_store(
        {
            "slr_a": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 300]],
        }
    )
    result = get_windowed_tool_slow_call_rate("slr_a", _WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, f"2/4=0.5; kills slow_count=2 or total=4; got {result}"


def test_all_slow_rate_is_one() -> None:
    """All calls slow -> rate=1.0."""
    _reset()
    store = _make_store(
        {
            "slr_b": [(_NOW - 10, float(v), True) for v in [200, 300, 400]],
        }
    )
    result = get_windowed_tool_slow_call_rate("slr_b", _WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"All slow -> 1.0; got {result}"


def test_no_slow_calls_rate_is_zero() -> None:
    """No slow calls -> rate=0.0."""
    _reset()
    store = _make_store(
        {
            "slr_c": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        }
    )
    result = get_windowed_tool_slow_call_rate("slr_c", _WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"No slow calls -> 0.0; got {result}"


def test_strictly_greater_than_threshold() -> None:
    """Latency exactly equal to threshold is NOT slow (strictly >).

    lats [50, 50, 200], threshold=50 -> 1/3 ≈ 0.333 (only 200 > 50).
    Kills >= impl which would return 3/3=1.0.
    """
    _reset()
    store = _make_store(
        {
            "slr_d": [
                (_NOW - 10, 50.0, True),
                (_NOW - 10, 50.0, True),
                (_NOW - 10, 200.0, True),
            ],
        }
    )
    result = get_windowed_tool_slow_call_rate("slr_d", _WIN, 50.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0 / 3.0) < 1e-9, (
        f"threshold=50: 1 slow (200>50) / 3 total = 1/3; kills >=impl=1.0; got {result}"
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_slow_call_rate("no_such_slr", _WIN, 50.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "slr_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
        }
    )
    assert get_windowed_tool_slow_call_rate("slr_old", _WIN, 50.0, store=store, now_ms=_NOW) == 0.0


def test_rate_in_zero_one_range() -> None:
    """Rate is always in [0.0, 1.0]."""
    _reset()
    store = _make_store(
        {
            "slr_rng": [(_NOW - 10, float(v), True) for v in range(10, 110, 10)],
        }
    )
    result = get_windowed_tool_slow_call_rate("slr_rng", _WIN, 50.0, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0


def test_consistent_with_slow_count_and_call_count() -> None:
    """rate == slow_count / call_count."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_call_count

    _reset()
    store = _make_store(
        {
            "slr_cons": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 300, 500]],
        }
    )
    rate = get_windowed_tool_slow_call_rate("slr_cons", _WIN, 100.0, store=store, now_ms=_NOW)
    slow = get_windowed_tool_slow_call_count("slr_cons", _WIN, 100.0, store=store, now_ms=_NOW)
    total = get_windowed_tool_call_count("slr_cons", _WIN, store=store, now_ms=_NOW)
    assert abs(rate - slow / total) < 1e-9, (
        f"rate={rate} must equal slow/total={slow}/{total}={slow / total}"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"slr_rt": [(_NOW - 10, 200.0, True)] * 3})
    assert isinstance(
        get_windowed_tool_slow_call_rate("slr_rt", _WIN, 100.0, store=store, now_ms=_NOW), float
    )
