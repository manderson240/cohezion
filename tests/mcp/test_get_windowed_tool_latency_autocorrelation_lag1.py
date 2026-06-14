"""Item 1082: get_windowed_tool_latency_autocorrelation_lag1(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool lag-1 Pearson autocorrelation of latency values (correlation between
lats[i] and lats[i+1] for consecutive windowed samples ordered by timestamp).

Captures serial correlation: whether one slow call predicts the next.
Range [-1, 1]. 0.0 for <2 samples or zero variance.

PRIMARY DISC.: strictly alternating [10,50,10,50] -> lag-1 pairs (10,50),(50,10),(10,50)
  -> Pearson r = -1.0 (perfectly anti-correlated)
  (PRIMARY DISC.: kills autocorr=0 assumption; an alternating series is maximally
   anti-correlated, not uncorrelated; correct lag-1 r=-1.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_autocorrelation_lag1,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_autocorr_primary_discriminator_alternating() -> None:
    """PRIMARY DISC.: alternating [10,50,10,50] -> lag-1 r=-1.0.

    Kills autocorr=0 assumption (alternating is not uncorrelated).
    Kills r=+1.0 (sign is negative for anti-correlated series).
    Correct: lag-1 r=-1.0.
    """
    _reset()
    store = _make_store(
        {
            "ac_disc": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 50.0, True),
                (_NOW - 100, 10.0, True),
                (_NOW - 0, 50.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_autocorrelation_lag1(
        "ac_disc", _WIN, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - (-1.0)) < 1e-9, f"alternating [10,50,10,50] -> lag-1 r=-1.0; got {result}"


def test_autocorr_perfectly_increasing_returns_one() -> None:
    """Strictly increasing latency -> each call predicts the next -> r=+1.0."""
    _reset()
    store = _make_store(
        {
            "ac_inc": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 20.0, True),
                (_NOW - 100, 30.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_autocorrelation_lag1(
        "ac_inc", _WIN, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"increasing -> r=1.0; got {result}"


def test_autocorr_constant_latency_returns_zero() -> None:
    """All identical values -> zero variance -> r=0.0."""
    _reset()
    store = _make_store(
        {
            "ac_const": [(_NOW - float(d), 50.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_latency_autocorrelation_lag1(
        "ac_const", _WIN, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"constant latency -> r=0.0; got {result}"


def test_autocorr_single_sample_returns_zero() -> None:
    """Single sample -> no pairs -> 0.0."""
    _reset()
    store = _make_store(
        {
            "ac_single": [(_NOW - 100, 42.0, True)],
        }
    )
    assert (
        get_windowed_tool_latency_autocorrelation_lag1("ac_single", _WIN, store=store, now_ms=_NOW)
        == 0.0
    )


def test_autocorr_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_autocorrelation_lag1("no_tool", _WIN, store={}, now_ms=_NOW)
        == 0.0
    )


def test_autocorr_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "ac_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30, 40]],
        }
    )
    assert (
        get_windowed_tool_latency_autocorrelation_lag1("ac_old", _WIN, store=store, now_ms=_NOW)
        == 0.0
    )


def test_autocorr_in_range_minus_one_to_one() -> None:
    """Result must be in [-1, 1] for any valid dataset."""
    _reset()
    store = _make_store(
        {
            "ac_range": [
                (_NOW - float(d), float(v), True)
                for d, v in [(400, 100), (300, 10), (200, 80), (100, 20), (0, 60)]
            ],
        }
    )
    result = get_windowed_tool_latency_autocorrelation_lag1(
        "ac_range", _WIN, store=store, now_ms=_NOW
    )
    assert -1.0 <= result <= 1.0, f"lag-1 autocorr must be in [-1,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "ac_rt": [
                (_NOW - float(d), float(v), True)
                for d, v in [(300, 10), (200, 20), (100, 30), (0, 40)]
            ],
        }
    )
    assert isinstance(
        get_windowed_tool_latency_autocorrelation_lag1("ac_rt", _WIN, store=store, now_ms=_NOW),
        float,
    )
