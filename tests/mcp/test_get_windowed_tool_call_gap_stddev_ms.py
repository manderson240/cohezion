"""Item 1120: get_windowed_tool_call_gap_stddev_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- population stddev of consecutive call-arrival gaps (ms) in window.
0.0 for <3 calls (need >=2 gaps to compute stddev). Returns float.

PRIMARY DISC.: 4 calls at ts=[-900,-600,-400,-100]ms -> gaps=[300,200,300]ms
  -> mean_gap=800/3=266.67, population_stddev=sqrt(2222.22)=47.14ms
  (PRIMARY DISC.: kills max_gap=300ms (max not stddev);
   kills mean_gap=266.67ms (mean not stddev);
   kills sample_stddev=57.74ms (divides by n-1=2, not population n=3);
   correct: population stddev, divide by n=3, return float~47.14).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_gap_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_gap_stddev_primary_discriminator() -> None:
    """PRIMARY DISC.: gaps=[300,200,300]ms -> pop_stddev=47.14ms.

    Kills max=300; kills mean=266.67; kills sample_stddev=57.74.
    """
    _reset()
    store = _make_store(
        {
            "gs_disc": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 10.0, True),
                (_NOW - 400, 10.0, True),
                (_NOW - 100, 10.0, True),
            ],
        }
    )
    # gaps = [300, 200, 300]; mean = 266.667; population variance = 2222.22
    expected = math.sqrt(2222.2222222)
    result = get_windowed_tool_call_gap_stddev_ms("gs_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - expected) < 0.01, (
        f"pop_stddev~47.14ms; kills max=300; kills mean=266.67; kills sample=57.74; got {result}"
    )


def test_gap_stddev_uniform_gaps_returns_zero() -> None:
    """All gaps equal -> stddev=0.0."""
    _reset()
    store = _make_store(
        {
            "gs_uniform": [
                (_NOW - 600, 10.0, True),
                (_NOW - 400, 10.0, True),
                (_NOW - 200, 10.0, True),
            ],
        }
    )
    # gaps = [200, 200]; mean=200; all deviations=0; stddev=0
    result = get_windowed_tool_call_gap_stddev_ms("gs_uniform", _WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"uniform gaps -> 0.0; got {result}"


def test_gap_stddev_less_than_three_calls_returns_zero() -> None:
    """Fewer than 3 calls (<2 gaps) -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gs_two": [(_NOW - 500, 10.0, True), (_NOW - 200, 10.0, True)],
        }
    )
    assert get_windowed_tool_call_gap_stddev_ms("gs_two", _WIN, store=store, now_ms=_NOW) == 0.0
    # single call
    store2 = _make_store({"gs_one": [(_NOW - 100, 10.0, True)]})
    assert get_windowed_tool_call_gap_stddev_ms("gs_one", _WIN, store=store2, now_ms=_NOW) == 0.0


def test_gap_stddev_empty_window_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_tool_call_gap_stddev_ms("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_gap_stddev_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gs_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_tool_call_gap_stddev_ms("gs_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_gap_stddev_known_two_gaps() -> None:
    """3 calls, two gaps of [100, 300]ms -> pop_stddev=100.0."""
    _reset()
    store = _make_store(
        {
            "gs_known": [
                (_NOW - 500, 10.0, True),  # gap to next: 300ms
                (_NOW - 200, 10.0, True),  # gap to next: 100ms
                (_NOW - 100, 10.0, True),
            ],
        }
    )
    # gaps=[300,100]; mean=200; deviations=[100,-100]; var=10000; stddev=100
    result = get_windowed_tool_call_gap_stddev_ms("gs_known", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"stddev=100ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "gs_rt": [
                (_NOW - 600, 10.0, True),
                (_NOW - 400, 10.0, True),
                (_NOW - 200, 10.0, True),
            ],
        }
    )
    result = get_windowed_tool_call_gap_stddev_ms("gs_rt", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
