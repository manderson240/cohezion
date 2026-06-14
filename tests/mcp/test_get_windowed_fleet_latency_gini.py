"""Item 1145: get_windowed_fleet_latency_gini(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide Gini coefficient of pooled latencies (latency inequality).
Returns float in [0.0, 1.0]. 0.0 for empty window or all-equal latencies.

Formula (sorted ascending x[0]..x[n-1]):
  Gini = (2 * sum((i+1)*x[i]) / (n * sum(x))) - (n+1)/n

PRIMARY DISC. (non-trivial unequal value):
  pooled sorted [10, 90], n=2, sum=100
  Gini = (2*(1*10 + 2*90) / (2*100)) - 3/2 = (2*190/200) - 1.5 = 1.9 - 1.5 = 0.4
  (PRIMARY DISC.: kills always-zero; kills formula-error returning 0.1 or 0.8;
   correct=0.4).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_gini,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _gini_reference(lats: list[float]) -> float:
    """Reference implementation of Gini coefficient (sorted formula)."""
    n = len(lats)
    if n == 0:
        return 0.0
    s = sum(lats)
    if s == 0.0:
        return 0.0
    sorted_lats = sorted(lats)
    weighted_sum = sum((i + 1) * x for i, x in enumerate(sorted_lats))
    return (2 * weighted_sum) / (n * s) - (n + 1) / n


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: Gini=0.4 for [10,90]; kills always-zero."""
    _reset()
    store = _make_store(
        {
            "fgi_a": [(_NOW - 700, 10.0, True)],
            "fgi_b": [(_NOW - 600, 90.0, True)],
        }
    )
    expected = _gini_reference([10.0, 90.0])
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - expected) < 1e-9, f"Gini=0.4 for [10,90]; got {result}; expected {expected}"
    assert abs(result - 0.4) < 1e-9, f"expected Gini=0.4; got {result}"


def test_fleet_gini_all_equal_returns_zero() -> None:
    """All latencies equal -> Gini=0.0 (perfect equality)."""
    _reset()
    store = _make_store(
        {
            "fgi_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fgi_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all equal -> 0.0; got {result}"


def test_fleet_gini_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_gini(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_gini_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fgi_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_gini_in_range() -> None:
    """Gini coefficient is always in [0.0, 1.0]."""
    _reset()
    store = _make_store(
        {
            "fgi_rng": [
                (_NOW - float(d), float(v), True)
                for d, v in zip([900, 800, 700, 600, 500], [1, 10, 50, 100, 1000])
            ],
        }
    )
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0, f"Gini out of range: {result}"


def test_fleet_gini_matches_reference() -> None:
    """Multi-tool fixture matches reference implementation."""
    _reset()
    store = _make_store(
        {
            "fgi_ref_a": [
                (_NOW - float(d), float(v), True) for d, v in zip([900, 800, 700], [10, 20, 30])
            ],
            "fgi_ref_b": [(_NOW - float(d), float(v), True) for d, v in zip([600, 500], [60, 100])],
        }
    )
    pooled = [10.0, 20.0, 30.0, 60.0, 100.0]
    expected = _gini_reference(pooled)
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert abs(result - expected) < 1e-9, f"expected {expected}; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fgi_rt_a": [(_NOW - 400, 20.0, True)],
            "fgi_rt_b": [(_NOW - 200, 80.0, True)],
        }
    )
    result = get_windowed_fleet_latency_gini(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
