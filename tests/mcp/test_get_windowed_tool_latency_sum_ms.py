"""Item 1019: get_windowed_tool_latency_sum_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- sum of all latency values in the window.

total_latency_ms = sum(latency_ms for all calls in window).
0.0 for unknown/empty tool. Injectable store. Pure function.
Enables mean recomputation: mean = sum / count.

PRIMARY DISC.: lats [10, 50, 200] -> sum=260.0.
  (kills count=3 int; kills mean=86.67; kills max=200; correct sum=260.0 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_sum_ms,
    get_windowed_tool_call_count,
    get_windowed_tool_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_latency_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: [10, 50, 200] -> 260.0.

    Kills count=3 (int wrong value).
    Kills mean=86.67 (float but wrong value).
    Kills max=200 (float but wrong value).
    Correct: 10+50+200 = 260.0.
    """
    _reset()
    store = _make_store(
        {
            "ls_a": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        }
    )
    result = get_windowed_tool_latency_sum_ms("ls_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 260.0) < 1e-9, (
        f"sum=260.0; kills mean=86.67 or count=3 or max=200; got {result}"
    )


def test_sum_equals_mean_times_count() -> None:
    """sum == mean * count (cross-function consistency).

    mean = sum / count, so sum = mean * count must hold.
    """
    _reset()
    store = _make_store(
        {
            "ls_cons": [(_NOW - 10, float(v), True) for v in [20, 40, 60, 80, 100]],
        }
    )
    total_sum = get_windowed_tool_latency_sum_ms("ls_cons", _WIN, store=store, now_ms=_NOW)
    count = get_windowed_tool_call_count("ls_cons", _WIN, store=store, now_ms=_NOW)
    mean = get_windowed_tool_mean_latency_ms("ls_cons", _WIN, store=store, now_ms=_NOW)
    assert abs(total_sum - mean * count) < 1e-9, (
        f"sum={total_sum} must equal mean*count={mean}*{count}={mean * count}"
    )


def test_single_call_sum_equals_its_latency() -> None:
    """Single call -> sum == that call's latency."""
    _reset()
    store = _make_store(
        {
            "ls_one": [(_NOW - 10, 137.0, True)],
        }
    )
    result = get_windowed_tool_latency_sum_ms("ls_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 137.0) < 1e-9, f"single call -> sum=137.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_sum_ms("no_such_ls", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "ls_old": [(_NOW - _WIN - 100, 999.0, True)] * 5,
        }
    )
    assert get_windowed_tool_latency_sum_ms("ls_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_sum_includes_failed_calls() -> None:
    """Sum counts latency of failed calls too (all calls regardless of success flag)."""
    _reset()
    store = _make_store(
        {
            "ls_fail": [
                (_NOW - 10, 50.0, True),
                (_NOW - 20, 100.0, False),  # failed call
                (_NOW - 30, 200.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_sum_ms("ls_fail", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 350.0) < 1e-9, f"sum includes failed calls: 50+100+200=350.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"ls_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100]]})
    assert isinstance(
        get_windowed_tool_latency_sum_ms("ls_rt", _WIN, store=store, now_ms=_NOW), float
    )
