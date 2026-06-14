"""Item 1153: get_windowed_fleet_latency_max_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide maximum latency across all pooled calls in the window.
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  tool_a=[10, 300], tool_b=[50, 200]
  fleet_max = 300.0
  kills mean≈140ms; kills min=10ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_max_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_latency_max_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_max=300.0; kills mean≈140, min=10, always-0."""
    _reset()
    store = _make_store(
        {
            "fmax_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 300.0, True)],
            "fmax_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 300.0) < 1e-9, (
        f"fleet_max=300.0; kills mean≈140/min=10/always-0; got {result}"
    )


def test_fleet_latency_max_single_tool() -> None:
    """Single tool, multiple calls -> max of that tool's calls."""
    _reset()
    store = _make_store(
        {
            "fmax_one": [
                (_NOW - 900, 5.0, True),
                (_NOW - 700, 150.0, True),
                (_NOW - 500, 80.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 150.0) < 1e-9, f"single tool max=150; got {result}"


def test_fleet_latency_max_single_call() -> None:
    """Single call in window -> that call's latency."""
    _reset()
    store = _make_store(
        {
            "fmax_one_call": [(_NOW - 500, 42.0, True)],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 42.0) < 1e-9, f"single call -> 42.0; got {result}"


def test_fleet_latency_max_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_max_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9, f"empty -> 0.0; got {result}"


def test_fleet_latency_max_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fmax_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"outside window -> 0.0; got {result}"


def test_fleet_latency_max_ignores_outside_window() -> None:
    """In-window calls determine max, not older calls with higher latency."""
    _reset()
    store = _make_store(
        {
            "fmax_mixed": [
                (_NOW - _WIN - 100, 9999.0, True),  # outside window — must be ignored
                (_NOW - 500, 75.0, True),  # inside window
                (_NOW - 300, 25.0, True),  # inside window
            ],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 75.0) < 1e-9, f"in-window max=75 (9999 outside); got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmax_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 200.0) < 1e-9
