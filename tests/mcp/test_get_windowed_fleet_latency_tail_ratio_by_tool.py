"""Item 1201: get_windowed_fleet_latency_tail_ratio_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool tail ratio (p99 / p50) within window.
Returns float. 0.0 for unknown/empty tool, fewer than 2 calls, or p50==0.
Formula: p99 / p50. A ratio of 1.0 = no tail; 10.0 = 1% tail is 10x median.

Nearest-rank percentiles.
tool_a=[10]*9+[100] → p50=10, p99=100 → ratio=10.0
tool_b=[10,20,30,40,50] → p50=30, p99=50 → ratio≈1.667

PRIMARY DISC.:
  ratio_a=10.0 kills ratio_b≈1.667; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_tail_ratio_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_tail_ratio_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio_a=10.0 kills ratio_b≈1.667; kills always-0."""
    _reset()
    a_lats = [10, 10, 10, 10, 10, 10, 10, 10, 10, 100]
    store = _make_store(
        {
            "ftrbt_a": [(_NOW - float(900 - i * 80), float(v), True) for i, v in enumerate(a_lats)],
            "ftrbt_b": [
                (_NOW - float(900 - i * 150), float(v), True)
                for i, v in enumerate([10, 20, 30, 40, 50])
            ],
        }
    )
    ratio_a = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_a", store=store, now_ms=_NOW
    )
    ratio_b = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ratio_a, float), f"expected float, got {type(ratio_a)}"
    assert ratio_a == 10.0, (
        f"ratio_a=10.0 (p99=100/p50=10); kills ratio_b≈1.667/always-0; got {ratio_a}"
    )
    assert abs(ratio_b - 50.0 / 30.0) < 1e-9, f"ratio_b=50/30≈1.667; got {ratio_b}"


def test_fleet_tail_ratio_uniform_latency_returns_one() -> None:
    """Uniform latency → p99=p50 → ratio=1.0 (no tail)."""
    _reset()
    store = _make_store(
        {
            "ftrbt_flat": [(_NOW - float(d), 42.0, True) for d in range(100, 1000, 100)],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_flat", store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"uniform → ratio=1.0; got {result}"


def test_fleet_tail_ratio_single_call_returns_zero() -> None:
    """Single call → fewer than 2 points → 0.0."""
    _reset()
    store = _make_store(
        {
            "ftrbt_one": [(_NOW - 500, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_one", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_tail_ratio_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "ftrbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_tail_ratio_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_tail_ratio_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_tail_ratio_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "ftrbt_old": [
                (_NOW - _WIN - float(d), float(v), True)
                for d, v in [(300, 10), (200, 50), (100, 100)]
            ],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_tail_ratio_at_least_one() -> None:
    """For any non-empty non-zero-median window, tail_ratio >= 1.0."""
    _reset()
    store = _make_store(
        {
            "ftrbt_geq": [
                (_NOW - float(900 - i * 80), float(v), True)
                for i, v in enumerate([10, 10, 10, 10, 10, 10, 10, 10, 10, 100])
            ],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_geq", store=store, now_ms=_NOW
    )
    assert result >= 1.0, f"tail_ratio >= 1.0 always; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "ftrbt_rt": [
                (_NOW - float(900 - i * 80), float(v), True)
                for i, v in enumerate([10, 10, 10, 10, 10, 10, 10, 10, 10, 100])
            ],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio_by_tool(
        _WIN, "ftrbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 10.0
