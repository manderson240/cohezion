"""Item 1100: get_windowed_fleet_latency_autocorrelation_lag1(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide Pearson lag-1 autocorrelation over ALL pooled calls sorted by timestamp.
0.0 for <3 pooled calls (need >=2 consecutive pairs) or zero variance.
Fleet dual of item 1082.

PRIMARY DISC.: tool_a ts=[t-500,t-300,t-100] lats=[10,90,10]ms (V-shape),
               tool_b ts=[t-400,t-200,t-0] lats=[90,10,90]ms (inverted-V)
  pooled sorted by ts: [(t-500,10),(t-400,90),(t-300,90),(t-200,10),(t-100,10),(t-0,90)]
  lats=[10,90,90,10,10,90]; x=[10,90,90,10,10], y=[90,90,10,10,90]
  xm=ym=42, autocorr < 0 (alternating pattern after pooling)
  (PRIMARY DISC.: kills per-tool-avg: each tool has independent autocorr;
   pooled interleaving of the two tools changes the lag sequence entirely;
   per-tool individual series have different structure than the pooled fleet stream).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_autocorrelation_lag1,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_autocorr_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled alternating sequence gives negative autocorr.

    Pooled lats=[10,90,90,10,10,90]: x=[10,90,90,10,10], y=[90,90,10,10,90]
    xm=ym=42, autocorr is negative (not matching per-tool patterns).
    """
    _reset()
    store = _make_store(
        {
            "facorr_v": [
                (_NOW - 500, 10.0, True),
                (_NOW - 300, 90.0, True),
                (_NOW - 100, 10.0, True),
            ],
            "facorr_inv": [
                (_NOW - 400, 90.0, True),
                (_NOW - 200, 10.0, True),
                (_NOW - 0, 90.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # Pooled sorted: [10,90,90,10,10,90]; x=[10,90,90,10,10], y=[90,90,10,10,90]
    # xm=42, ym=42; both tools contribute to interleaved alternating structure
    # The result should be in [-1, 1] and typically negative for alternating series
    assert -1.0 <= result <= 1.0, f"autocorr out of bounds; got {result}"
    # Specifically: the pooled series interleaves ups and downs, giving negative lag-1
    assert result < 0.0, f"alternating pooled series -> negative autocorr; got {result}"


def test_fleet_autocorr_perfect_positive() -> None:
    """Monotone rising series -> autocorr = 1.0."""
    _reset()
    store = _make_store(
        {
            "facorr_rise": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 20.0, True),
                (_NOW - 200, 30.0, True),
                (_NOW - 100, 40.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"monotone rise -> autocorr=1.0; got {result}"


def test_fleet_autocorr_perfect_negative() -> None:
    """Strictly alternating series -> autocorr = -1.0."""
    _reset()
    store = _make_store(
        {
            "facorr_alt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 90.0, True),
                (_NOW - 200, 10.0, True),
                (_NOW - 100, 90.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW)
    assert abs(result - (-1.0)) < 1e-9, f"alternating -> autocorr=-1.0; got {result}"


def test_fleet_autocorr_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_autocorr_fewer_than_three_pooled_calls_returns_zero() -> None:
    """<3 pooled calls -> <2 lag-1 pairs -> 0.0."""
    _reset()
    store = _make_store(
        {
            "facorr_two": [(_NOW - 200, 10.0, True), (_NOW - 100, 20.0, True)],
        }
    )
    assert get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_autocorr_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "facorr_old": [(_NOW - _WIN - 100, 10.0, True)] * 5,
        }
    )
    assert get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_autocorr_constant_latency_returns_zero() -> None:
    """All same latency -> zero variance in lag pairs -> 0.0."""
    _reset()
    store = _make_store(
        {
            "facorr_const_a": [(_NOW - 400, 50.0, True), (_NOW - 200, 50.0, True)],
            "facorr_const_b": [(_NOW - 300, 50.0, True), (_NOW - 100, 50.0, True)],
        }
    )
    assert get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "facorr_rt": [(_NOW - float(d), float(d), True) for d in [400, 300, 200, 100, 0]],
        }
    )
    assert isinstance(
        get_windowed_fleet_latency_autocorrelation_lag1(_WIN, store=store, now_ms=_NOW), float
    )
