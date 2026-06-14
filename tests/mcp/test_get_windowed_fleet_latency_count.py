"""Item 1136: get_windowed_fleet_latency_count(window_ms, *, store=None, now_ms=None) -> int
-- fleet-wide total call count across all tools in the window.
0 for empty window. Returns int.

PRIMARY DISC. (fleet-count vs per-tool-avg):
  tool_a calls=3, tool_b calls=2
  per-tool-avg = (3+2)/2 = 2.5 (float, wrong type too)
  max-per-tool = 3
  fleet_count = 3+2 = 5
  (PRIMARY DISC.: kills per-tool-avg=2.5; kills max-per-tool=3;
   correct: sum ALL call counts, return int=5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_count_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_count=5; kills per-tool-avg=2.5 and max-per-tool=3."""
    _reset()
    store = _make_store(
        {
            "fcnt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
            ],
            "fcnt_b": [
                (_NOW - 600, 50.0, True),
                (_NOW - 500, 60.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 5, f"fleet_count=5; kills per-tool-avg=2.5, kills max=3; got {result}"


def test_fleet_count_single_tool() -> None:
    """Single-tool fleet count equals that tool's call count."""
    _reset()
    store = _make_store(
        {
            "fcnt_one": [
                (_NOW - 700, 10.0, True),
                (_NOW - 600, 20.0, True),
                (_NOW - 500, 30.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert result == 3, f"expected 3; got {result}"


def test_fleet_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_latency_count(_WIN, store={}, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fcnt_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_count_window_boundary_exact() -> None:
    """Call at exactly cutoff boundary (ts == cutoff_ms) is included."""
    _reset()
    store = _make_store(
        {
            "fcnt_bnd": [
                (_NOW - _WIN, 50.0, True),  # ts == cutoff -> included
                (_NOW - _WIN - 1, 99.0, True),  # ts < cutoff -> excluded
            ],
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert result == 1, f"boundary call included; expected 1; got {result}"


def test_fleet_count_three_tools() -> None:
    """Three tools, varying call counts, summed correctly."""
    _reset()
    store = _make_store(
        {
            "fcnt_t1": [(_NOW - float(d), 1.0, True) for d in [900, 800, 700, 600]],  # 4
            "fcnt_t2": [(_NOW - float(d), 2.0, True) for d in [500, 400]],  # 2
            "fcnt_t3": [(_NOW - float(d), 3.0, True) for d in [300, 200, 100]],  # 3
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert result == 9, f"expected 9; got {result}"


def test_returns_int_type() -> None:
    """Return type is int (not float)."""
    _reset()
    store = _make_store(
        {
            "fcnt_rt_a": [(_NOW - 400, 30.0, True)],
            "fcnt_rt_b": [(_NOW - 200, 70.0, True)],
        }
    )
    result = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result).__name__}"
    assert result == 2
