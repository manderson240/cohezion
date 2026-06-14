"""Item 1130: get_windowed_fleet_latency_skewness(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide skewness (3rd standardised moment) of pooled latencies.
0.0 for empty window, <3 calls, or zero variance. Returns float.

PRIMARY DISC. (pool vs per-tool-then-average):
  tool_a lats=[10,50,90] (symmetric) -> per-tool skewness=0.0
  tool_b lats=[10,10,200] (right-skewed) -> per-tool skewness≈0.706
  per-tool-avg = (0+0.706)/2 ≈ 0.353
  pooled [10,10,10,50,90,200]: pooled skewness >> 0.353
  (PRIMARY DISC.: per-tool-avg ≈ half the pooled value; correct: pool all latencies,
   Fisher-Pearson population skewness = mean(((x-μ)/σ)³), return float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_skewness,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _population_skewness(lats: list[float]) -> float:
    """Reference implementation: population Fisher-Pearson skewness."""
    n = len(lats)
    if n < 3:
        return 0.0
    mean = sum(lats) / n
    variance = sum((x - mean) ** 2 for x in lats) / n
    if variance == 0.0:
        return 0.0
    stddev = variance**0.5
    return sum((x - mean) ** 3 for x in lats) / (n * stddev**3)


def test_fleet_skewness_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled skewness > per-tool-avg (≈2x larger)."""
    _reset()
    store = _make_store(
        {
            "fsk_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 50.0, True),
                (_NOW - 700, 90.0, True),
            ],
            "fsk_b": [
                (_NOW - 600, 10.0, True),
                (_NOW - 500, 10.0, True),
                (_NOW - 400, 200.0, True),
            ],
        }
    )
    # per-tool:
    #   tool_a: symmetric [10,50,90] -> skewness=0.0
    #   tool_b: right-skewed [10,10,200] -> skewness > 0
    per_tool_avg = (
        _population_skewness([10.0, 50.0, 90.0]) + _population_skewness([10.0, 10.0, 200.0])
    ) / 2.0
    # pooled: [10,10,10,50,90,200]
    expected_pooled = _population_skewness([10.0, 10.0, 10.0, 50.0, 90.0, 200.0])
    result = get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - expected_pooled) < 1e-9, (
        f"pooled skewness={expected_pooled:.4f}; got {result}"
    )
    # Prove primary discriminator: pooled ≠ per-tool-avg
    assert abs(result - per_tool_avg) > 0.1, (
        f"pooled={result:.4f} must differ from per-tool-avg={per_tool_avg:.4f} by >0.1"
    )


def test_fleet_skewness_symmetric_returns_zero() -> None:
    """Symmetric distribution [10,50,90] pooled from two tools -> skewness=0.0."""
    _reset()
    store = _make_store(
        {
            "fsk_sym_a": [
                (_NOW - 600, 10.0, True),
                (_NOW - 500, 50.0, True),
                (_NOW - 400, 90.0, True),
            ],
            "fsk_sym_b": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 50.0, True),
                (_NOW - 100, 90.0, True),
            ],
        }
    )
    # pooled [10,50,90,10,50,90] is symmetric -> skewness=0
    result = get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"symmetric pool -> 0.0; got {result}"


def test_fleet_skewness_fewer_than_3_calls_returns_zero() -> None:
    """<3 calls in window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsk_few": [
                (_NOW - 400, 10.0, True),
                (_NOW - 200, 90.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"2 calls -> 0.0; got {result}"


def test_fleet_skewness_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_skewness(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_skewness_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsk_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_skewness_all_same_returns_zero() -> None:
    """All latencies equal -> zero variance -> skewness=0.0."""
    _reset()
    store = _make_store(
        {
            "fsk_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fsk_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsk_rt_a": [
                (_NOW - 600, 10.0, True),
                (_NOW - 500, 50.0, True),
                (_NOW - 400, 90.0, True),
            ],
            "fsk_rt_b": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 10.0, True),
                (_NOW - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
