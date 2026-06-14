"""Item 1154: get_windowed_fleet_latency_min_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide minimum latency across all pooled calls in the window.
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  tool_a=[300, 10], tool_b=[200, 50]
  fleet_min = 10.0
  kills max=300ms; kills mean≈140ms; kills always-0.
  Composition: min_ms <= mean_ms <= max_ms.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_min_ms,
    get_windowed_fleet_latency_max_ms,
    get_windowed_fleet_latency_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_latency_min_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_min=10.0; kills max=300, mean≈140, always-0."""
    _reset()
    store = _make_store(
        {
            "fmin_a": [(_NOW - 900, 300.0, True), (_NOW - 800, 10.0, True)],
            "fmin_b": [(_NOW - 700, 200.0, True), (_NOW - 600, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 10.0) < 1e-9, (
        f"fleet_min=10.0; kills max=300/mean≈140/always-0; got {result}"
    )


def test_fleet_latency_min_max_mean_ordering() -> None:
    """Composition: min_ms <= mean_ms <= max_ms for any non-empty store."""
    _reset()
    store = _make_store(
        {
            "fmin_ord_a": [(_NOW - 900, 100.0, True), (_NOW - 800, 500.0, True)],
            "fmin_ord_b": [(_NOW - 700, 200.0, True), (_NOW - 600, 50.0, True)],
        }
    )
    mn = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    mean = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    mx = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert mn <= mean <= mx, f"ordering violated: min({mn}) <= mean({mean}) <= max({mx})"


def test_fleet_latency_min_single_tool() -> None:
    """Single tool, multiple calls -> min of that tool's calls."""
    _reset()
    store = _make_store(
        {
            "fmin_one": [
                (_NOW - 900, 500.0, True),
                (_NOW - 700, 25.0, True),
                (_NOW - 500, 80.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 25.0) < 1e-9, f"single tool min=25; got {result}"


def test_fleet_latency_min_single_call() -> None:
    """Single call in window -> that call's latency."""
    _reset()
    store = _make_store(
        {
            "fmin_one_call": [(_NOW - 500, 99.0, True)],
        }
    )
    result = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 99.0) < 1e-9, f"single call -> 99.0; got {result}"


def test_fleet_latency_min_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_min_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9, f"empty -> 0.0; got {result}"


def test_fleet_latency_min_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fmin_old": [(_NOW - _WIN - float(d), 1.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"outside window -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmin_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9
