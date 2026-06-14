"""Item 1125: get_windowed_tool_latency_burst_fraction(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- fraction of windowed calls that are in a multi-call burst (run of >=2 above-threshold calls).
0.0 for empty window. Returns float in [0.0, 1.0].

PRIMARY DISC.: [low,HIGH,HIGH,HIGH,low,HIGH,low] -> burst1(len=3 counted), burst2(len=1 NOT counted)
  -> burst_calls=3, total=7, fraction=3/7=0.4286
  (PRIMARY DISC.: kills above_fraction=4/7=0.571 (counts ALL above-threshold calls);
   kills burst_count=1 (only multi-call bursts, not calls in them);
   correct: count calls in runs>=2, divide by total windowed calls, float=3/7).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_burst_fraction,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_burst_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: burst1=3 calls (multi), burst2=1 call (solo, NOT in burst) -> 3/7."""
    _reset()
    store = _make_store(
        {
            "bf_disc": [
                (_NOW - 900, 10.0, True),  # low (not in burst)
                (_NOW - 800, 80.0, True),  # burst 1 call 1
                (_NOW - 700, 90.0, True),  # burst 1 call 2
                (_NOW - 600, 85.0, True),  # burst 1 call 3 (all 3 are in a multi-call burst)
                (_NOW - 500, 10.0, True),  # low (not in burst)
                (_NOW - 400, 70.0, True),  # solo spike (run=1, NOT in burst)
                (_NOW - 300, 10.0, True),  # low (not in burst)
            ],
        }
    )
    result = get_windowed_tool_latency_burst_fraction(
        "bf_disc", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    expected = 3.0 / 7.0
    assert abs(result - expected) < 1e-9, (
        f"3/7={expected:.4f}; kills above_fraction=4/7; kills burst_count=1; got {result}"
    )


def test_burst_fraction_all_in_one_burst() -> None:
    """All calls are above-threshold in one run -> fraction=1.0."""
    _reset()
    store = _make_store(
        {
            "bf_all": [(_NOW - float(d), 80.0, True) for d in [400, 300, 200, 100]],
        }
    )
    result = get_windowed_tool_latency_burst_fraction(
        "bf_all", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all in burst -> 1.0; got {result}"


def test_burst_fraction_only_solo_spikes_returns_zero() -> None:
    """Only solo above-threshold calls (run=1 each) -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bf_solo": [
                (_NOW - 600, 80.0, True),  # solo spike
                (_NOW - 400, 10.0, True),  # low
                (_NOW - 200, 80.0, True),  # solo spike
                (_NOW - 100, 10.0, True),  # low
            ],
        }
    )
    result = get_windowed_tool_latency_burst_fraction(
        "bf_solo", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"only solos -> 0.0; got {result}"


def test_burst_fraction_no_above_threshold_returns_zero() -> None:
    """No calls above threshold -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bf_none": [(_NOW - float(d), 30.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_burst_fraction("bf_none", _WIN, _THR, store=store, now_ms=_NOW)
        == 0.0
    )


def test_burst_fraction_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_burst_fraction("no_tool", _WIN, _THR, store={}, now_ms=_NOW)
        == 0.0
    )


def test_burst_fraction_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bf_old": [
                (_NOW - _WIN - 200, 80.0, True),
                (_NOW - _WIN - 100, 80.0, True),  # two HIGHs but outside window
            ],
        }
    )
    assert (
        get_windowed_tool_latency_burst_fraction("bf_old", _WIN, _THR, store=store, now_ms=_NOW)
        == 0.0
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "bf_rt": [
                (_NOW - 400, 80.0, True),  # burst
                (_NOW - 300, 80.0, True),  # burst (len=2)
                (_NOW - 200, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_burst_fraction("bf_rt", _WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 2.0 / 3.0) < 1e-9, f"2/3; got {result}"
