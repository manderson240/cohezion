"""Item 999: get_windowed_tool_latency_iqr_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool interquartile range (IQR = p75 - p25) of latency in window.

IQR = get_windowed_latency_percentile(tool, 75, ...) - get_windowed_latency_percentile(tool, 25, ...)
Robust spread metric resistant to outliers.
0.0 for unknown tools or <2 calls in window. Returns float.

PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> IQR=20.0
  p75: idx=0.75*4=3.0 -> sorted[3]=40.0
  p25: idx=0.25*4=1.0 -> sorted[1]=20.0
  IQR = 40.0 - 20.0 = 20.0
  Kills range=50-10=40.0; kills stddev≈14.14; kills mean=30.0.
"""

from __future__ import annotations

import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_iqr_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_iqr_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,30,40,50] -> IQR=20.0 (not range=40.0, not stddev≈14.14).

    p75=40.0, p25=20.0, IQR=20.0.
    Kills impl returning range (max-min=40.0).
    Kills impl returning stddev (population stddev≈14.14).
    """
    _reset()
    store = _make_store(
        {
            "iqr_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tool_latency_iqr_ms("iqr_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 20.0) < 1e-9, (
        f"IQR([10,20,30,40,50])=20.0; kills range=40.0 or stddev≈14.14; got {result}"
    )
    # not the range
    assert abs(result - 40.0) > 1.0
    # not the stddev (≈14.142)
    assert abs(result - math.sqrt(200)) > 1.0


def test_iqr_asymmetric_distribution() -> None:
    """IQR is resistant to a high outlier that inflates range and stddev.

    lats [10, 20, 30, 1000]: outlier at 1000 inflates range and stddev,
    but IQR = p75 - p25 stays bounded.
    p25: idx=0.25*3=0.75; 10+0.75*(20-10)=17.5
    p75: idx=0.75*3=2.25; 30+0.25*(1000-30)=272.5
    IQR = 272.5 - 17.5 = 255.0
    range = 1000 - 10 = 990.0  (much larger — confirms IQR is different)
    """
    _reset()
    store = _make_store(
        {
            "iqr_asym": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 1000]],
        }
    )
    result = get_windowed_tool_latency_iqr_ms("iqr_asym", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 255.0) < 1e-9, f"IQR([10,20,30,1000])=255.0; got {result}"
    # Verify IQR < range (robustness of IQR vs range)
    assert result < 990.0 - 1.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_iqr_ms("no_such_iqr", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "iqr_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert get_windowed_tool_latency_iqr_ms("iqr_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_zero() -> None:
    """Single call has no spread -> IQR=0.0."""
    _reset()
    store = _make_store({"iqr_one": [(_NOW - 10, 42.0, True)]})
    # p75 == p25 == 42.0 for single point, IQR=0.0
    result = get_windowed_tool_latency_iqr_ms("iqr_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"Single call IQR=0.0; got {result}"


def test_iqr_non_negative() -> None:
    """IQR is always non-negative (p75 >= p25)."""
    _reset()
    store = _make_store(
        {
            "iqr_nn": [(_NOW - 10, float(v), True) for v in range(1, 11)],
        }
    )
    result = get_windowed_tool_latency_iqr_ms("iqr_nn", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0


def test_uniform_distribution_iqr_zero() -> None:
    """All latencies equal -> IQR=0.0 (p75=p25=value)."""
    _reset()
    store = _make_store(
        {
            "iqr_unif": [(_NOW - 10, 15.0, True)] * 8,
        }
    )
    result = get_windowed_tool_latency_iqr_ms("iqr_unif", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"Uniform lats -> IQR=0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"iqr_rtype": [(_NOW - 10, float(v), True) for v in [5, 10, 15, 20, 25]]})
    assert isinstance(
        get_windowed_tool_latency_iqr_ms("iqr_rtype", _WIN, store=store, now_ms=_NOW), float
    )
