"""Item 1053: get_windowed_tool_latency_coefficient_of_quartile_variation(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool coefficient of quartile variation (CQV).

CQV = (Q3 - Q1) / (Q3 + Q1); robust relative spread measure.
0.0 for Q3+Q1 == 0 or n < 4.
Uses linear interpolation for quartiles (same as get_windowed_latency_percentile).

PRIMARY DISC.: lats [10,20,30,40,50] n=5
  Q1=idx=0.25*4=1.0 -> 20.0 (exact, no interpolation needed)
  Q3=idx=0.75*4=3.0 -> 40.0 (exact)
  CQV=(40-20)/(40+20)=20/60=1/3≈0.3333
  (PRIMARY DISC.: kills CV=stddev/mean≈0.526 (wrong formula);
   kills range/(max+min)=40/60≈0.667 (range-based not quartile);
   correct CQV=(Q3-Q1)/(Q3+Q1)=1/3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_coefficient_of_quartile_variation,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_cqv_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] n=5 -> CQV=(Q3-Q1)/(Q3+Q1)=20/60=1/3.

    Kills CV=stddev/mean≈0.526 (wrong formula).
    Kills range/(max+min)=40/60≈0.667 (range-based).
    Correct: Q1=20, Q3=40, CQV=1/3≈0.3333.
    """
    _reset()
    store = _make_store(
        {
            "cqv_disc": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tool_latency_coefficient_of_quartile_variation(
        "cqv_disc", _WIN, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    expected = 1.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"CQV=1/3≈{expected:.6f}; kills CV≈0.526 and range-ratio≈0.667; got {result}"
    )


def test_cqv_equals_q3_minus_q1_over_sum() -> None:
    """CQV == (Q3-Q1)/(Q3+Q1) using the percentile delegate (arithmetic identity)."""
    _reset()
    lats = [10.0, 20.0, 50.0, 100.0, 200.0]
    store = _make_store(
        {
            "cqv_id": [(_NOW - 10, v, True) for v in lats],
        }
    )
    cqv = get_windowed_tool_latency_coefficient_of_quartile_variation(
        "cqv_id", _WIN, store=store, now_ms=_NOW
    )
    q1 = get_windowed_latency_percentile("cqv_id", 25.0, _WIN, store=store, now_ms=_NOW)
    q3 = get_windowed_latency_percentile("cqv_id", 75.0, _WIN, store=store, now_ms=_NOW)
    if q3 + q1 > 0:
        expected = (q3 - q1) / (q3 + q1)
        assert abs(cqv - expected) < 1e-9, f"CQV={cqv} != (Q3-Q1)/(Q3+Q1)={expected}"


def test_all_equal_cqv_zero() -> None:
    """All equal -> Q1=Q3 -> CQV=0.0."""
    _reset()
    store = _make_store(
        {
            "cqv_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_tool_latency_coefficient_of_quartile_variation(
        "cqv_eq", _WIN, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"all-equal -> CQV=0.0; got {result}"


def test_fewer_than_4_samples_returns_zero() -> None:
    """n < 4 -> 0.0."""
    _reset()
    store = _make_store(
        {
            "cqv_few": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        }
    )
    result = get_windowed_tool_latency_coefficient_of_quartile_variation(
        "cqv_few", _WIN, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"n=3 < 4 -> CQV=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_coefficient_of_quartile_variation(
            "no_such_cqv", _WIN, store={}, now_ms=_NOW
        )
        == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "cqv_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_coefficient_of_quartile_variation(
            "cqv_old", _WIN, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_cqv_non_negative() -> None:
    """CQV >= 0 always (Q3 >= Q1 for sorted data)."""
    _reset()
    store = _make_store(
        {
            "cqv_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10]],
        }
    )
    result = get_windowed_tool_latency_coefficient_of_quartile_variation(
        "cqv_pos", _WIN, store=store, now_ms=_NOW
    )
    assert result >= 0.0, f"CQV must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"cqv_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_tool_latency_coefficient_of_quartile_variation(
            "cqv_rt", _WIN, store=store, now_ms=_NOW
        ),
        float,
    )
