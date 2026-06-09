"""Item 1103: get_windowed_tool_latency_burst_rate_per_ms(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- rate of latency bursts = burst_count / window_ms (bursts per ms).
0.0 for empty window or zero window_ms.
Normalizes item-1083 burst_count by the observation window.

PRIMARY DISC.: window=1000ms, 3 bursts -> rate=3/1000=0.003 bursts/ms
  (PRIMARY DISC.: kills burst_count=3 (not normalized);
   kills burst_count/span_ms (uses actual call span, not window);
   correct: burst_count / window_ms = 3/1000 = 0.003 bursts/ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_burst_rate_per_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0  # burst threshold ms


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_burst_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 bursts / 1000ms = 0.003 bursts/ms.

    Kills burst_count=3 (not normalized by window).
    Kills burst_count/span_ms (span != window).
    """
    _reset()
    # 3 distinct burst runs: [low, HIGH, low, HIGH, low, HIGH, low]
    store = _make_store({
        "brate_disc": [
            (_NOW - 900, 10.0, True),  # low
            (_NOW - 800, 100.0, True),  # HIGH -> burst 1
            (_NOW - 700, 10.0, True),  # low -> exit burst
            (_NOW - 600, 100.0, True),  # HIGH -> burst 2
            (_NOW - 500, 10.0, True),  # low -> exit burst
            (_NOW - 400, 100.0, True),  # HIGH -> burst 3
            (_NOW - 300, 10.0, True),  # low -> exit burst
        ],
    })
    result = get_windowed_tool_latency_burst_rate_per_ms("brate_disc", _WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # 3 bursts / 1000ms = 0.003
    assert abs(result - 0.003) < 1e-9, (
        f"3 bursts/1000ms=0.003; kills burst_count=3; got {result}"
    )


def test_burst_rate_single_burst() -> None:
    """One burst -> 1/window_ms rate."""
    _reset()
    store = _make_store({
        "brate_one": [
            (_NOW - 500, 100.0, True),  # HIGH -> burst 1
            (_NOW - 400, 100.0, True),  # still in burst
            (_NOW - 300, 10.0, True),   # exit burst
        ],
    })
    result = get_windowed_tool_latency_burst_rate_per_ms("brate_one", _WIN, _THR, store=store, now_ms=_NOW)
    assert abs(result - 1.0 / _WIN) < 1e-12, f"1 burst/1000ms=0.001; got {result}"


def test_burst_rate_no_bursts_returns_zero() -> None:
    """No latencies exceed threshold -> 0 bursts -> 0.0."""
    _reset()
    store = _make_store({
        "brate_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100]],
    })
    assert get_windowed_tool_latency_burst_rate_per_ms("brate_none", _WIN, _THR, store=store, now_ms=_NOW) == 0.0


def test_burst_rate_empty_window_returns_zero() -> None:
    """No calls in window -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_burst_rate_per_ms("no_tool", _WIN, _THR, store={}, now_ms=_NOW) == 0.0


def test_burst_rate_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "brate_old": [(_NOW - _WIN - 100, 100.0, True)] * 3,
    })
    assert get_windowed_tool_latency_burst_rate_per_ms("brate_old", _WIN, _THR, store=store, now_ms=_NOW) == 0.0


def test_burst_rate_depends_on_window_size() -> None:
    """Same burst count, different windows -> different rates."""
    _reset()
    store = _make_store({
        "brate_w": [
            (_NOW - 200, 100.0, True),  # burst 1
            (_NOW - 100, 10.0, True),   # exit
        ],
    })
    rate_1000 = get_windowed_tool_latency_burst_rate_per_ms("brate_w", 1000.0, _THR, store=store, now_ms=_NOW)
    rate_500 = get_windowed_tool_latency_burst_rate_per_ms("brate_w", 500.0, _THR, store=store, now_ms=_NOW)
    assert abs(rate_1000 - 0.001) < 1e-12, f"1/1000=0.001; got {rate_1000}"
    assert abs(rate_500 - 0.002) < 1e-12, f"1/500=0.002; got {rate_500}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "brate_rt": [(_NOW - 500, 100.0, True), (_NOW - 400, 10.0, True)],
    })
    assert isinstance(get_windowed_tool_latency_burst_rate_per_ms("brate_rt", _WIN, _THR, store=store, now_ms=_NOW), float)
