"""Item 1131: get_windowed_fleet_latency_kurtosis(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide excess kurtosis (4th standardised moment - 3) of pooled latencies.
0.0 for empty window, <4 calls, or zero variance. Returns float.

PRIMARY DISC. (pool vs per-tool-then-average):
  tool_a lats=[10,50,90,130] (uniform, platykurtic, excess kurtosis < 0)
  tool_b lats=[50,50,50,200] (spike outlier, leptokurtic, excess kurtosis > per_a)
  per-tool-avg = (kurt_a + kurt_b) / 2
  pooled [10,50,50,50,90,130,200]: pooled excess kurtosis ≠ per-tool-avg
  (PRIMARY DISC.: kills per-tool-avg; correct: pool all latencies,
   excess_kurtosis = mean(((x-μ)/σ)⁴) - 3, return float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_kurtosis,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _population_excess_kurtosis(lats: list[float]) -> float:
    """Reference: population Fisher excess kurtosis = mean(((x-μ)/σ)⁴) - 3."""
    n = len(lats)
    if n < 4:
        return 0.0
    mean = sum(lats) / n
    variance = sum((x - mean) ** 2 for x in lats) / n
    if variance == 0.0:
        return 0.0
    stddev = variance**0.5
    raw = sum((x - mean) ** 4 for x in lats) / (n * stddev**4)
    return raw - 3.0


def test_fleet_kurtosis_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled kurtosis ≠ per-tool-avg; both computable from reference."""
    _reset()
    store = _make_store(
        {
            "fk_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 50.0, True),
                (_NOW - 700, 90.0, True),
                (_NOW - 600, 130.0, True),
            ],
            "fk_b": [
                (_NOW - 500, 50.0, True),
                (_NOW - 400, 50.0, True),
                (_NOW - 300, 50.0, True),
                (_NOW - 200, 200.0, True),
            ],
        }
    )
    kurt_a = _population_excess_kurtosis([10.0, 50.0, 90.0, 130.0])
    kurt_b = _population_excess_kurtosis([50.0, 50.0, 50.0, 200.0])
    per_tool_avg = (kurt_a + kurt_b) / 2.0
    expected_pooled = _population_excess_kurtosis(
        [10.0, 50.0, 90.0, 130.0, 50.0, 50.0, 50.0, 200.0]
    )
    result = get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - expected_pooled) < 1e-9, (
        f"pooled kurtosis={expected_pooled:.4f}; got {result}"
    )
    # Pooled and per-tool-avg must differ (PRIMARY DISC.)
    assert abs(result - per_tool_avg) > 1e-6, (
        f"pooled={result:.4f} must differ from per-tool-avg={per_tool_avg:.4f}"
    )


def test_fleet_kurtosis_all_same_returns_zero() -> None:
    """All latencies equal -> zero variance -> kurtosis=0.0."""
    _reset()
    store = _make_store(
        {
            "fk_flat_a": [(_NOW - float(d), 42.0, True) for d in [500, 400, 300]],
            "fk_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_kurtosis_fewer_than_4_calls_returns_zero() -> None:
    """<4 total calls -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fk_few": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 50.0, True),
                (_NOW - 100, 90.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"3 calls -> 0.0; got {result}"


def test_fleet_kurtosis_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_kurtosis(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_kurtosis_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fk_old": [(_NOW - _WIN - float(d), float(d), True) for d in [400, 300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_kurtosis_normal_distribution_near_zero() -> None:
    """Normal-ish distribution -> excess kurtosis near 0.0 (not raw kurt=3.0)."""
    _reset()
    # Symmetric 4-value [10,30,70,90]: mean=50, deviations symmetric
    store = _make_store(
        {
            "fk_norm": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 30.0, True),
                (_NOW - 200, 70.0, True),
                (_NOW - 100, 90.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    # Fisher EXCESS kurtosis: raw - 3; uniform-ish sample → near -1.36 (platykurtic)
    expected = _population_excess_kurtosis([10.0, 30.0, 70.0, 90.0])
    assert abs(result - expected) < 1e-9, f"expected excess_kurt={expected:.4f}; got {result}"
    # Excess kurtosis should NOT be near raw kurtosis (3.0) — that's the PRIMARY killer
    assert abs(result - 3.0) > 1.0, f"got raw kurtosis instead of excess: {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fk_rt": [
                (_NOW - 500, 10.0, True),
                (_NOW - 400, 50.0, True),
                (_NOW - 300, 50.0, True),
                (_NOW - 200, 50.0, True),
                (_NOW - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
