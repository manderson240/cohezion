"""Item 996: get_windowed_tool_throughput_per_sec(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool windowed throughput in calls per second.

Formula: call_count_in_window / (window_ms / 1000.0)
Counts ALL calls (success + failures) in window.
0.0 for unknown tools or empty window. Returns float.

PRIMARY DISC.: 5 calls in window_ms=1000 -> 5.0 calls/sec
  (kills raw call count=5 int; kills calls/window_ms=0.005; correct=5.0).
SECONDARY DISC.: 3 calls in window_ms=500 -> 6.0 calls/sec
  (kills calls/window_ms=0.006; kills call_count=3; correct=6.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_throughput_per_sec,
)

_NOW = 1_000_000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_throughput_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls in 1000ms -> 5.0/sec (not 5 int, not 0.005).

    Kills impl returning raw call count (=5).
    Kills impl returning calls/window_ms (=0.005).
    """
    _reset()
    win = 1000.0  # 1 second window
    store = _make_store({
        "tp_a": [(_NOW - 100, 10.0, True)] * 5,  # 5 calls, all recent
    })
    result = get_windowed_tool_throughput_per_sec("tp_a", win, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # 5 calls / 1.0 second = 5.0 calls/sec
    assert abs(result - 5.0) < 1e-9, (
        f"5 calls in 1000ms window -> 5.0/sec; kills raw=5 or per-ms=0.005; got {result}"
    )


def test_throughput_secondary_discriminator() -> None:
    """FALSIFIABLE: 3 calls in 500ms -> 6.0/sec (not 3, not 0.006).

    Kills impl returning raw count.
    Kills impl returning calls/window_ms.
    """
    _reset()
    win = 500.0  # 0.5 second window
    store = _make_store({
        "tp_b": [(_NOW - 100, 20.0, True)] * 3,
    })
    result = get_windowed_tool_throughput_per_sec("tp_b", win, store=store, now_ms=_NOW)
    # 3 calls / 0.5 seconds = 6.0 calls/sec
    assert abs(result - 6.0) < 1e-9, (
        f"3 calls in 500ms -> 6.0/sec; kills raw=3 or per-ms=0.006; got {result}"
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_throughput_per_sec("no_such_tp", 1000.0, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    win = 500.0
    store = _make_store({
        "tp_old": [(_NOW - win - 100, 20.0, True)] * 5,  # all outside window
    })
    assert get_windowed_tool_throughput_per_sec("tp_old", win, store=store, now_ms=_NOW) == 0.0


def test_counts_both_success_and_failures() -> None:
    """Throughput includes failed calls (total call rate, not success rate).

    3 successes + 2 failures in 1000ms -> 5.0/sec.
    Kills impl counting only successes (would give 3.0/sec).
    """
    _reset()
    win = 1000.0
    store = _make_store({
        "tp_c": [
            (_NOW - 100, 10.0, True),
            (_NOW - 100, 20.0, True),
            (_NOW - 100, 30.0, True),
            (_NOW - 100, 40.0, False),  # failure
            (_NOW - 100, 50.0, False),  # failure
        ],
    })
    result = get_windowed_tool_throughput_per_sec("tp_c", win, store=store, now_ms=_NOW)
    # 5 total calls / 1.0 sec = 5.0/sec (NOT 3.0 if only successes counted)
    assert abs(result - 5.0) < 1e-9, (
        f"3 success + 2 failure in 1000ms -> 5.0/sec; kills success-only=3.0; got {result}"
    )


def test_single_call_returns_non_zero() -> None:
    """Single call in window -> positive throughput."""
    _reset()
    win = 2000.0
    store = _make_store({"tp_one": [(_NOW - 100, 42.0, True)]})
    result = get_windowed_tool_throughput_per_sec("tp_one", win, store=store, now_ms=_NOW)
    # 1 call / 2.0 seconds = 0.5/sec
    assert abs(result - 0.5) < 1e-9, f"1 call in 2000ms -> 0.5/sec; got {result}"


def test_returns_float_type() -> None:
    """Return type is always float."""
    _reset()
    store = _make_store({"tp_rtype": [(_NOW - 100, 5.0, True)] * 4})
    result = get_windowed_tool_throughput_per_sec("tp_rtype", 1000.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
