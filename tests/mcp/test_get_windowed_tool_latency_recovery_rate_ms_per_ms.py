"""Item 1085: get_windowed_tool_latency_recovery_rate_ms_per_ms(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- average rate of latency decrease (ms/ms wall-time) from burst peak to first
recovery call after each burst.

For each burst ending at ts_end with peak latency p, followed by first
below-threshold call at ts_next with latency l_next:
  recovery_rate = (p - l_next) / (ts_next - ts_end)
Average over all such burst-to-recovery transitions.
0.0 if no burst-to-recovery transitions exist.

PRIMARY DISC.: lats=[10@t-300, 100@t-200, 20@t-100, 80@t-50, 10@t-0] threshold=50
  burst1: peak=100 ends@t-200, recovery@t-100 lat=20 -> rate=(100-20)/100=0.8 ms/ms
  burst2: peak=80 ends@t-50, recovery@t-0 lat=10 -> rate=(80-10)/50=1.4 ms/ms
  avg=1.1 ms/ms
  (PRIMARY DISC.: kills avg_below_threshold_latency=15ms -- latency level not rate;
   kills slope=negative (trend not recovery rate);
   correct avg_recovery_rate=1.1 ms/ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_recovery_rate_ms_per_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_recovery_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: 2-burst sequence -> avg recovery_rate=1.1 ms/ms.

    Kills avg_below_latency=15ms (level, not rate).
    Kills OLS slope (trend, not recovery rate).
    Correct: avg_recovery_rate=1.1 ms/ms.
    """
    _reset()
    store = _make_store(
        {
            "rrate_disc": [
                (_NOW - 300, 10.0, True),  # below threshold
                (_NOW - 200, 100.0, True),  # burst 1: peak=100, ends here
                (_NOW - 100, 20.0, True),  # recovery 1: rate=(100-20)/100=0.8
                (_NOW - 50, 80.0, True),  # burst 2: peak=80, ends here
                (_NOW - 0, 10.0, True),  # recovery 2: rate=(80-10)/50=1.4
            ],
        }
    )
    result = get_windowed_tool_latency_recovery_rate_ms_per_ms(
        "rrate_disc", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 1.1) < 1e-9, (
        f"avg_recovery_rate=1.1; kills latency_level=15ms; kills slope; got {result}"
    )


def test_recovery_rate_no_burst_returns_zero() -> None:
    """No above-threshold calls -> no transitions -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rrate_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
        }
    )
    assert (
        get_windowed_tool_latency_recovery_rate_ms_per_ms(
            "rrate_none", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_recovery_rate_burst_at_end_no_recovery_returns_zero() -> None:
    """Burst ends at last call with no following recovery -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rrate_end": [
                (_NOW - 200, 10.0, True),
                (_NOW - 100, 80.0, True),  # above threshold
                (_NOW - 0, 90.0, True),  # above threshold -- burst continues to window edge
            ],
        }
    )
    assert (
        get_windowed_tool_latency_recovery_rate_ms_per_ms(
            "rrate_end", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_recovery_rate_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_recovery_rate_ms_per_ms(
            "no_tool", _WIN, 50.0, store={}, now_ms=_NOW
        )
        == 0.0
    )


def test_recovery_rate_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rrate_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_recovery_rate_ms_per_ms(
            "rrate_old", _WIN, 50.0, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_recovery_rate_single_transition() -> None:
    """Single burst-to-recovery transition -> that one rate is returned."""
    _reset()
    # burst peak=200@t-100, recovery=10@t-0 -> rate=(200-10)/100=1.9
    store = _make_store(
        {
            "rrate_single": [
                (_NOW - 100, 200.0, True),
                (_NOW - 0, 10.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_recovery_rate_ms_per_ms(
        "rrate_single", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.9) < 1e-9, f"single transition: (200-10)/100=1.9; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "rrate_rt": [
                (_NOW - 200, 10.0, True),
                (_NOW - 100, 80.0, True),
                (_NOW - 0, 20.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_recovery_rate_ms_per_ms(
        "rrate_rt", _WIN, 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
