"""Item 997: get_windowed_global_throughput_per_sec(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide windowed throughput in calls per second.

Formula: total_call_count_across_all_tools / (window_ms / 1000.0)
Counts ALL calls (success + failures) from ALL tools in window.
0.0 when no recent calls. Returns float.

PRIMARY DISC.: tool_a 3 calls + tool_b 2 calls in 1000ms -> 5.0/sec
  (kills avg-of-per-tool-throughput=(3.0+2.0)/2=2.5; kills max-per-tool=3.0; pooled=5.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_throughput_per_sec,
    get_windowed_tool_throughput_per_sec,
)

_NOW = 1_000_000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_throughput_primary_discriminator() -> None:
    """FALSIFIABLE: 3+2 calls in 1000ms -> 5.0/sec (not avg=2.5, not max-per-tool=3.0).

    tool_a 3 calls: per-tool throughput = 3.0/sec
    tool_b 2 calls: per-tool throughput = 2.0/sec
    avg-of-per-tool = (3.0+2.0)/2 = 2.5/sec  -> WRONG
    max-per-tool    = 3.0/sec                 -> WRONG
    pooled = (3+2) calls / 1.0 sec = 5.0/sec  -> CORRECT
    """
    _reset()
    win = 1000.0
    store = _make_store(
        {
            "gtp_a": [(_NOW - 100, 10.0, True)] * 3,
            "gtp_b": [(_NOW - 100, 20.0, True)] * 2,
        }
    )
    result = get_windowed_global_throughput_per_sec(win, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 5.0) < 1e-9, (
        f"pooled 5 calls in 1000ms -> 5.0/sec; kills avg=2.5 or max=3.0; got {result}"
    )
    # not avg-of-per-tool
    assert abs(result - 2.5) > 1.0
    # not max-per-tool
    assert abs(result - 3.0) > 1.0


def test_single_tool_matches_per_tool_throughput() -> None:
    """With one tool, global throughput == per-tool throughput."""
    _reset()
    win = 2000.0
    store = _make_store(
        {
            "gtp_one": [(_NOW - 100, 10.0, True)] * 6,
        }
    )
    global_tp = get_windowed_global_throughput_per_sec(win, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_throughput_per_sec("gtp_one", win, store=store, now_ms=_NOW)
    assert abs(global_tp - per_tool) < 1e-9, (
        f"single tool: global={global_tp} must equal per-tool={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_throughput_per_sec(1000.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    win = 500.0
    store = _make_store(
        {
            "gtp_old": [(_NOW - win - 100, 10.0, True)] * 5,
        }
    )
    assert get_windowed_global_throughput_per_sec(win, store=store, now_ms=_NOW) == 0.0


def test_counts_failures_too() -> None:
    """Failed calls count toward total throughput (total call rate).

    5 successes + 3 failures in 1000ms -> 8.0/sec (not 5.0/sec if only successes).
    """
    _reset()
    win = 1000.0
    store = _make_store(
        {
            "gtp_fail": [(_NOW - 100, 10.0, True)] * 5 + [(_NOW - 100, 20.0, False)] * 3,
        }
    )
    result = get_windowed_global_throughput_per_sec(win, store=store, now_ms=_NOW)
    assert abs(result - 8.0) < 1e-9, (
        f"5 success + 3 failure in 1000ms -> 8.0/sec; kills success-only=5.0; got {result}"
    )


def test_window_scaling() -> None:
    """10 calls in 500ms window -> 20.0/sec (not 10.0)."""
    _reset()
    win = 500.0
    store = _make_store(
        {
            "gtp_scale": [(_NOW - 100, 5.0, True)] * 10,
        }
    )
    result = get_windowed_global_throughput_per_sec(win, store=store, now_ms=_NOW)
    # 10 / 0.5 = 20.0/sec
    assert abs(result - 20.0) < 1e-9, f"10 calls in 500ms -> 20.0/sec; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gtp_rtype": [(_NOW - 100, 5.0, True)] * 3})
    result = get_windowed_global_throughput_per_sec(1000.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
