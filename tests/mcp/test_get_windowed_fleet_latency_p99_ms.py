"""Item 1159: get_windowed_fleet_latency_p99_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 99th percentile latency.
Thin composition: get_windowed_fleet_latency_percentile_ms(window_ms, 99.0, ...).
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  sorted [10,20,...,1000] step=10, n=100
  P99: ceil(0.99*100)-1 = 98 → latencies[98] = 990ms
  P95: ceil(0.95*100)-1 = 94 → latencies[94] = 950ms
  mean = 505ms
  P99=990ms kills P95=950ms and mean=505ms.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p99_ms,
    get_windowed_fleet_latency_percentile_ms,
    get_windowed_fleet_latency_p95_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p99_primary_discriminator() -> None:
    """PRIMARY DISC.: P99=990ms for n=100 step=10; kills P95=950ms; kills mean=505ms."""
    _reset()
    # 100 calls with latencies [10, 20, ..., 1000]
    latencies = [float(i * 10) for i in range(1, 101)]
    store = _make_store(
        {
            "fp99_a": [(_NOW - float(1000 - i * 9), lat, True) for i, lat in enumerate(latencies)],
        }
    )
    result = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 990.0) < 1e-9, (
        f"P99=990ms (nearest-rank index 98); kills P95=950/mean=505; got {result}"
    )


def test_fleet_p99_differs_from_p95() -> None:
    """P99 > P95 for skewed distribution (non-trivial distinction)."""
    _reset()
    latencies = [float(i * 10) for i in range(1, 101)]
    store = _make_store(
        {
            "fp99_diff": [
                (_NOW - float(1000 - i * 9), lat, True) for i, lat in enumerate(latencies)
            ],
        }
    )
    p99 = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert p99 > p95, f"P99({p99}) must exceed P95({p95})"
    assert abs(p99 - 990.0) < 1e-9 and abs(p95 - 950.0) < 1e-9


def test_fleet_p99_composition_with_percentile_ms() -> None:
    """Composition: p99_ms == percentile_ms(99.0)."""
    _reset()
    store = _make_store(
        {
            "fp99_comp": [(_NOW - float(1000 - i * 80), float(i * 10 + 5), True) for i in range(9)],
        }
    )
    p99 = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms(_WIN, 99.0, store=store, now_ms=_NOW)
    assert abs(p99 - generic) < 1e-12, "p99_ms must equal percentile_ms(99.0)"


def test_fleet_p99_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p99_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p99_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fp99_old": [(_NOW - _WIN - float(d), 999.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p99_single_call() -> None:
    """Single call -> P99 == that call's latency."""
    _reset()
    store = _make_store(
        {
            "fp99_one": [(_NOW - 300, 123.0, True)],
        }
    )
    result = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 123.0) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fp99_rt": [(_NOW - float(d), float(d), True) for d in range(50, 550, 50)],
        }
    )
    result = get_windowed_fleet_latency_p99_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
