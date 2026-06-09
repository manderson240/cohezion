"""Item 1090: get_windowed_tool_call_gap_mean_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- mean gap (ms) between consecutive windowed calls. 0.0 for <2 calls.
Mean call gap = total_span / (n-1) where n = number of windowed calls.

PRIMARY DISC.: ts=[t-400, t-300, t-100, t-0] -> gaps=[100,200,100]; mean=400/3≈133.33ms
  (PRIMARY DISC.: kills max_gap=200ms (max not mean);
   kills first_gap=100ms (only the first gap, not the average);
   correct mean_gap=133.33ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_gap_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_call_gap_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: ts=[t-400,t-300,t-100,t-0] -> mean_gap=400/3≈133.33ms.

    Kills max_gap=200ms (max, not mean).
    Kills first_gap=100ms (one gap, not average).
    Correct: mean=sum([100,200,100])/3=133.33ms.
    """
    _reset()
    store = _make_store({
        "gmean_disc": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 20.0, True),
            (_NOW - 100, 30.0, True),
            (_NOW - 0, 40.0, True),
        ],
    })
    result = get_windowed_tool_call_gap_mean_ms("gmean_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - (400.0 / 3.0)) < 1e-6, (
        f"mean_gap=133.33ms; kills max=200ms; kills first=100ms; got {result}"
    )


def test_call_gap_mean_equally_spaced() -> None:
    """Equally spaced calls -> mean = each gap."""
    _reset()
    store = _make_store({
        "gmean_equal": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
    })
    result = get_windowed_tool_call_gap_mean_ms("gmean_equal", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"equal gaps=100ms each; mean=100ms; got {result}"


def test_call_gap_mean_single_call_returns_zero() -> None:
    """Single call -> no gaps -> 0.0."""
    _reset()
    store = _make_store({"gmean_single": [(_NOW - 100, 42.0, True)]})
    assert get_windowed_tool_call_gap_mean_ms("gmean_single", _WIN, store=store, now_ms=_NOW) == 0.0


def test_call_gap_mean_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_call_gap_mean_ms("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_call_gap_mean_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gmean_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
    })
    assert get_windowed_tool_call_gap_mean_ms("gmean_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_call_gap_mean_two_calls() -> None:
    """Two calls -> one gap -> mean = that gap."""
    _reset()
    store = _make_store({
        "gmean_two": [
            (_NOW - 250, 10.0, True),
            (_NOW - 50, 20.0, True),
        ],
    })
    result = get_windowed_tool_call_gap_mean_ms("gmean_two", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 200.0) < 1e-9, f"single gap=200ms; got {result}"


def test_call_gap_mean_uses_timestamp_not_latency() -> None:
    """Mean gap is based on TIMESTAMPS of calls, not on latency values."""
    _reset()
    # Timestamps: [t-600, t-200, t-0] -> gaps=[400, 200] -> mean=300ms
    store = _make_store({
        "gmean_ts": [
            (_NOW - 600, 500.0, True),
            (_NOW - 200, 1.0, True),
            (_NOW - 0, 1.0, True),
        ],
    })
    result = get_windowed_tool_call_gap_mean_ms("gmean_ts", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 300.0) < 1e-9, f"mean time gap=300ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "gmean_rt": [(_NOW - float(d), 10.0, True) for d in [200, 100, 0]],
    })
    assert isinstance(get_windowed_tool_call_gap_mean_ms("gmean_rt", _WIN, store=store, now_ms=_NOW), float)
