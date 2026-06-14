"""Item 1018: get_windowed_tool_call_rate_per_sec(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool call rate in calls/second over the window.

Semantic alias for get_windowed_tool_throughput_per_sec.
0.0 for unknown/empty tool. Injectable store. Pure function.

PRIMARY DISC.: 10 calls in window_ms=2000 -> 10/(2000/1000) = 5.0 calls/sec.
  (kills call_count=10 int; kills calls/ms=0.005; correct calls/sec=5.0 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_rate_per_sec,
    get_windowed_tool_throughput_per_sec,
)

_NOW = 1_000_000.0
_WIN = 2000.0  # 2 seconds for easy arithmetic


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_call_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: 10 calls in 2000ms window -> 5.0 calls/sec.

    Kills call_count=10 (int, wrong units).
    Kills calls/ms=0.005 (per-millisecond instead of per-second).
    Correct: 10 / (2000/1000) = 5.0 calls/sec.
    """
    _reset()
    store = _make_store(
        {
            "cr_a": [(_NOW - (i * 100), 10.0, True) for i in range(1, 11)],  # 10 calls
        }
    )
    result = get_windowed_tool_call_rate_per_sec("cr_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 5.0) < 1e-9, (
        f"10 calls / 2s = 5.0 calls/sec; kills count=10 or calls/ms=0.005; got {result}"
    )


def test_alias_equals_throughput_per_sec() -> None:
    """call_rate_per_sec == throughput_per_sec (they are the same metric)."""
    _reset()
    store = _make_store(
        {
            "cr_eq": [(_NOW - (i * 50), float(i * 10), True) for i in range(1, 8)],
        }
    )
    rate = get_windowed_tool_call_rate_per_sec("cr_eq", _WIN, store=store, now_ms=_NOW)
    throughput = get_windowed_tool_throughput_per_sec("cr_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(rate - throughput) < 1e-9, f"call_rate={rate} must equal throughput={throughput}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_call_rate_per_sec("no_such_cr", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "cr_old": [(_NOW - _WIN - 100, 10.0, True)] * 5,
        }
    )
    assert get_windowed_tool_call_rate_per_sec("cr_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"cr_rt": [(_NOW - 100, 10.0, True)] * 3})
    assert isinstance(
        get_windowed_tool_call_rate_per_sec("cr_rt", _WIN, store=store, now_ms=_NOW), float
    )
