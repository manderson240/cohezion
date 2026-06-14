"""Item 1083: get_windowed_tool_latency_burst_count(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> int
-- count of consecutive runs of high-latency calls (runs where latency > burst_threshold_ms).
Each unbroken run of above-threshold calls = 1 burst.
0 if no calls or no above-threshold calls.

PRIMARY DISC.: lats=[10,80,90,20,70,85,95,15] with threshold=50
  -> runs=[80,90],[70,85,95] -> burst_count=2
  (PRIMARY DISC.: kills total-above-threshold count=5 (individual calls, not runs);
   kills above-threshold-fraction=5/8 (fraction, not burst count);
   correct burst_count=2).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_burst_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_burst_count_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,80,90,20,70,85,95,15] threshold=50 -> 2 bursts.

    Kills total-above-threshold=5 (individual calls, not runs).
    Kills fraction=5/8 (wrong metric).
    Correct: burst_count=2.
    """
    _reset()
    lats = [10.0, 80.0, 90.0, 20.0, 70.0, 85.0, 95.0, 15.0]
    store = _make_store(
        {
            "burst_disc": [
                (_NOW - (len(lats) - 1 - i) * 50.0, lat, True) for i, lat in enumerate(lats)
            ],
        }
    )
    result = get_windowed_tool_latency_burst_count(
        "burst_disc", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 2, (
        f"[10,80,90,20,70,85,95,15] threshold=50 -> 2 bursts; total-above=5; got {result}"
    )


def test_burst_count_single_sustained_run() -> None:
    """One unbroken sequence of high latency = 1 burst regardless of length."""
    _reset()
    store = _make_store(
        {
            "burst_sus": [
                (_NOW - float((5 - i) * 50), lat, True)
                for i, lat in enumerate([100.0, 120.0, 90.0, 110.0, 80.0])
            ],
        }
    )
    result = get_windowed_tool_latency_burst_count(
        "burst_sus", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 1, f"one sustained run -> 1 burst; got {result}"


def test_burst_count_no_above_threshold_calls_returns_zero() -> None:
    """All latencies below threshold -> 0 bursts."""
    _reset()
    store = _make_store(
        {
            "burst_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
        }
    )
    assert (
        get_windowed_tool_latency_burst_count("burst_none", _WIN, 50.0, store=store, now_ms=_NOW)
        == 0
    )


def test_burst_count_empty_window_returns_zero() -> None:
    """Empty window -> 0."""
    _reset()
    assert get_windowed_tool_latency_burst_count("no_tool", _WIN, 50.0, store={}, now_ms=_NOW) == 0


def test_burst_count_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "burst_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_burst_count("burst_old", _WIN, 50.0, store=store, now_ms=_NOW)
        == 0
    )


def test_burst_count_each_isolated_call_is_own_burst() -> None:
    """Alternating: each high call separated by low = each is its own burst."""
    _reset()
    # [10,80,10,80,10,80] threshold=50 -> 3 separate bursts
    lats = [10.0, 80.0, 10.0, 80.0, 10.0, 80.0]
    store = _make_store(
        {
            "burst_alt": [
                (_NOW - (len(lats) - 1 - i) * 50.0, lat, True) for i, lat in enumerate(lats)
            ],
        }
    )
    result = get_windowed_tool_latency_burst_count(
        "burst_alt", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 3, f"alternating -> 3 bursts; got {result}"


def test_burst_count_threshold_boundary_exclusive() -> None:
    """Calls at EXACTLY threshold are NOT counted (strictly > threshold required)."""
    _reset()
    # threshold=50; lat=50 should NOT count as above
    store = _make_store(
        {
            "burst_bound": [
                (_NOW - 200, 50.0, True),  # exactly at threshold -- not a burst
                (_NOW - 100, 51.0, True),  # above threshold -- 1 burst
                (_NOW - 0, 50.0, True),  # exactly at threshold -- not a burst
            ],
        }
    )
    result = get_windowed_tool_latency_burst_count(
        "burst_bound", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert result == 1, f"only 51.0 is above 50 -> 1 burst; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "burst_rt": [
                (_NOW - float(d), float(v), True)
                for d, v in [(400, 10), (300, 80), (200, 90), (100, 20), (0, 70)]
            ],
        }
    )
    result = get_windowed_tool_latency_burst_count("burst_rt", _WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
