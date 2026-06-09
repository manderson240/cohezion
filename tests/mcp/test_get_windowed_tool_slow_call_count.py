"""Item 1003: get_windowed_tool_slow_call_count(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- count of calls with latency_ms > threshold_ms in the window.

SLO compliance check: "how many calls exceeded the threshold?"
Strictly greater than (not >=). Returns int. 0 for unknown/no-recent.

PRIMARY DISC.: lats [10, 50, 200, 300] with threshold=100 -> 2
  (kills count-all=4; kills count->50=3 if >= were used; correct: 200>100 and 300>100 -> 2).
STRICT GREATER THAN: threshold=50 on lats [10, 50, 200] -> 1 (50 is NOT > 50).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_slow_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_slow_call_count_primary_discriminator() -> None:
    """FALSIFIABLE: lats [10,50,200,300], threshold=100 -> 2 (not 4, not 3).

    Kills impl counting all calls (=4).
    Kills impl using >= instead of > (threshold=100 with lats [10,50,100,200,300] would give 3 not 2).
    """
    _reset()
    store = _make_store({
        "slow_a": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 300]],
    })
    result = get_windowed_tool_slow_call_count("slow_a", _WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2, (
        f"lats [10,50,200,300] with threshold=100 -> 2; kills all=4 or >=count=3; got {result}"
    )


def test_strictly_greater_than_threshold() -> None:
    """Latency exactly equal to threshold does NOT count (strictly >).

    lats [10, 50, 200], threshold=50 -> 1 (only 200 > 50; 50 is not > 50).
    Kills >= impl which would return 2.
    """
    _reset()
    store = _make_store({
        "slow_b": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
    })
    result = get_windowed_tool_slow_call_count("slow_b", _WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 1, (
        f"threshold=50, lats [10,50,200]: only 200>50 -> 1; kills >=impl=2; got {result}"
    )


def test_all_calls_above_threshold() -> None:
    """All calls above threshold -> count == total calls in window."""
    _reset()
    store = _make_store({
        "slow_c": [(_NOW - 10, float(v), True) for v in [200, 300, 400]],
    })
    result = get_windowed_tool_slow_call_count("slow_c", _WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 3, f"All 3 calls > 100 -> 3; got {result}"


def test_no_calls_above_threshold() -> None:
    """All calls below threshold -> 0."""
    _reset()
    store = _make_store({
        "slow_d": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
    })
    result = get_windowed_tool_slow_call_count("slow_d", _WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0, f"All calls < 100 -> 0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert get_windowed_tool_slow_call_count("no_such_slow", _WIN, 50.0, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store({
        "slow_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
    })
    assert get_windowed_tool_slow_call_count("slow_old", _WIN, 50.0, store=store, now_ms=_NOW) == 0


def test_counts_both_success_and_failure_slow_calls() -> None:
    """Failed calls are also counted if they're slow (total slow, not just slow-successes)."""
    _reset()
    store = _make_store({
        "slow_e": [
            (_NOW - 10, 200.0, True),   # slow success
            (_NOW - 10, 300.0, False),  # slow failure -- must be counted
            (_NOW - 10, 10.0, False),   # fast failure -- not slow
        ],
    })
    result = get_windowed_tool_slow_call_count("slow_e", _WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 2, (
        f"2 slow calls (success+failure) > 100ms -> 2; kills success-only=1; got {result}"
    )


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({"slow_rt": [(_NOW - 10, 200.0, True)] * 3})
    result = get_windowed_tool_slow_call_count("slow_rt", _WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
