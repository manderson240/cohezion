"""Item 1135: get_windowed_fleet_latency_sum_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide sum of all pooled latencies in the window (ms).
0.0 for empty window. Returns float.

PRIMARY DISC. (fleet-sum vs per-tool-avg-sum):
  tool_a lats=[10,20,30]ms (sum=60ms), tool_b lats=[100,200]ms (sum=300ms)
  per-tool-avg-sum = (60+300)/2 = 180ms
  max-per-tool-sum = 300ms
  fleet_sum = 10+20+30+100+200 = 360ms
  (PRIMARY DISC.: kills per-tool-avg=180ms; kills max-per-tool=300ms;
   correct: sum ALL pooled latencies, return float=360ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sum_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sum_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_sum=360ms; kills per-tool-avg=180ms and max-per-tool=300ms."""
    _reset()
    store = _make_store({
        "fsum_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fsum_b": [
            (_NOW - 600, 100.0, True),
            (_NOW - 500, 200.0, True),
        ],
    })
    # fleet sum = 10+20+30+100+200 = 360ms
    result = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 360.0) < 1e-9, (
        f"fleet_sum=360ms; kills per-tool-avg=180ms, kills max=300ms; got {result}"
    )


def test_fleet_sum_single_tool() -> None:
    """Single-tool fleet sum equals that tool's sum."""
    _reset()
    store = _make_store({
        "fsum_one": [
            (_NOW - 700, 10.0, True),
            (_NOW - 600, 20.0, True),
            (_NOW - 500, 30.0, True),
        ],
    })
    result = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 60.0) < 1e-9, f"expected 60ms; got {result}"


def test_fleet_sum_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_sum_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_sum_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fsum_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    assert get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_sum_window_boundary_exact() -> None:
    """Calls at exactly cutoff boundary (ts == cutoff_ms) are included (>= semantics)."""
    _reset()
    store = _make_store({
        "fsum_bnd": [
            (_NOW - _WIN, 50.0, True),   # ts == cutoff -> included
            (_NOW - _WIN - 1, 99.0, True),  # ts < cutoff -> excluded
        ],
    })
    result = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 50.0) < 1e-9, f"boundary call included; expected 50ms; got {result}"


def test_fleet_sum_symmetric_tools() -> None:
    """Two identical tools -> fleet sum = 2x one tool's sum."""
    _reset()
    store = _make_store({
        "fsum_s_a": [(_NOW - 700, 25.0, True), (_NOW - 600, 75.0, True)],
        "fsum_s_b": [(_NOW - 500, 25.0, True), (_NOW - 400, 75.0, True)],
    })
    result = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    # 25+75+25+75 = 200ms
    assert abs(result - 200.0) < 1e-9, f"expected 200ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fsum_rt_a": [(_NOW - 400, 30.0, True)],
        "fsum_rt_b": [(_NOW - 200, 70.0, True)],
    })
    result = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 100.0) < 1e-9
