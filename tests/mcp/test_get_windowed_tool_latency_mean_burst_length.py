"""Item 1123: get_windowed_tool_latency_mean_burst_length(tool_name, window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- mean number of consecutive calls per burst (burst length = calls in run, averaged over bursts).
0.0 for empty window or zero bursts. Returns float.

PRIMARY DISC.: burst1_len=3, burst2_len=1 -> mean_burst_length=(3+1)/2=2.0
  (PRIMARY DISC.: kills max_burst_length=3 (max not mean);
   kills burst_count=2 (count not mean length);
   kills above_fraction=4/7=0.571 (fraction of above-threshold calls, not run length);
   correct: sum(run_lengths) / burst_count, return float=2.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_mean_burst_length,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_mean_burst_length_primary_discriminator() -> None:
    """PRIMARY DISC.: burst_lens=[3,1] -> mean=2.0. Kills max=3, count=2, fraction=4/7."""
    _reset()
    store = _make_store(
        {
            "mbl_disc": [
                (_NOW - 900, 10.0, True),  # low
                (_NOW - 800, 80.0, True),  # HIGH -> burst 1 start
                (_NOW - 700, 90.0, True),  # HIGH -> len=2
                (_NOW - 600, 85.0, True),  # HIGH -> len=3
                (_NOW - 500, 10.0, True),  # low -> burst 1 end (len=3)
                (_NOW - 400, 75.0, True),  # HIGH -> burst 2 start
                (_NOW - 300, 10.0, True),  # low -> burst 2 end (len=1)
            ],
        }
    )
    result = get_windowed_tool_latency_mean_burst_length(
        "mbl_disc", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 2.0) < 1e-9, (
        f"(3+1)/2=2.0; kills max=3; kills count=2; kills fraction=4/7; got {result}"
    )


def test_mean_burst_length_single_burst() -> None:
    """Single burst of length 4 -> mean=4.0."""
    _reset()
    store = _make_store(
        {
            "mbl_one": [
                (_NOW - 600, 10.0, True),  # low
                (_NOW - 500, 80.0, True),  # burst start
                (_NOW - 400, 80.0, True),  # burst len=2
                (_NOW - 300, 80.0, True),  # burst len=3
                (_NOW - 200, 80.0, True),  # burst len=4
                (_NOW - 100, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_mean_burst_length(
        "mbl_one", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result - 4.0) < 1e-9, f"single burst len=4 -> mean=4.0; got {result}"


def test_mean_burst_length_no_bursts_returns_zero() -> None:
    """No above-threshold calls -> 0.0."""
    _reset()
    store = _make_store(
        {
            "mbl_none": [(_NOW - float(d), 30.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_mean_burst_length(
            "mbl_none", _WIN, _THR, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_mean_burst_length_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_mean_burst_length("no_tool", _WIN, _THR, store={}, now_ms=_NOW)
        == 0.0
    )


def test_mean_burst_length_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "mbl_old": [(_NOW - _WIN - 100, 80.0, True)] * 4,
        }
    )
    assert (
        get_windowed_tool_latency_mean_burst_length("mbl_old", _WIN, _THR, store=store, now_ms=_NOW)
        == 0.0
    )


def test_mean_burst_length_uniform_lengths() -> None:
    """Three bursts each of length 2 -> mean=2.0."""
    _reset()
    store = _make_store(
        {
            "mbl_uniform": [
                (_NOW - 900, 80.0, True),  # burst 1
                (_NOW - 800, 80.0, True),  # burst 1 len=2
                (_NOW - 700, 10.0, True),  # exit
                (_NOW - 600, 80.0, True),  # burst 2
                (_NOW - 500, 80.0, True),  # burst 2 len=2
                (_NOW - 400, 10.0, True),  # exit
                (_NOW - 300, 80.0, True),  # burst 3
                (_NOW - 200, 80.0, True),  # burst 3 len=2
                (_NOW - 100, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_mean_burst_length(
        "mbl_uniform", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert abs(result - 2.0) < 1e-9, f"3 bursts each len=2 -> mean=2.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "mbl_rt": [
                (_NOW - 400, 80.0, True),  # burst
                (_NOW - 300, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_tool_latency_mean_burst_length(
        "mbl_rt", _WIN, _THR, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 1.0) < 1e-9
