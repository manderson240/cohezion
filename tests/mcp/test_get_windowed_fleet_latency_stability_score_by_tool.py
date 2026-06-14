"""Item 1203: get_windowed_fleet_latency_stability_score_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency stability score in [0.0, 1.0] within window.
Returns float. 1.0 for unknown/empty tool or all-equal latency.
Formula: 1.0 / (1.0 + cv)  where cv = stddev / mean.
Monotonically decreasing in CV: cv=0 → score=1.0, cv=0.5 → ≈0.667, cv=1.0 → 0.5.

PRIMARY DISC.:
  tool_a=[10,10,10] (cv=0.0) → score=1.0
  tool_b=[10,20,30] (cv≈0.408, mean=20, pop_stddev≈8.165) → score≈0.710
  score_a=1.0 kills score_b≈0.710; kills always-0.
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_stability_score_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_stability_score_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: score_a=1.0 kills score_b≈0.710; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fssbt_a": [(_NOW - float(d), 10.0, True) for d in [900, 600, 300]],
            "fssbt_b": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 20.0, True),
                (_NOW - 300, 30.0, True),
            ],
        }
    )
    score_a = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_a", store=store, now_ms=_NOW
    )
    score_b = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(score_a, float), f"expected float, got {type(score_a)}"
    assert score_a == 1.0, f"score_a=1.0 (cv=0); kills score_b<1/always-0; got {score_a}"
    # Expected: cv_b = sqrt(((10-20)^2+(20-20)^2+(30-20)^2)/3)/20 = sqrt(200/3)/20
    mean_b = 20.0
    stddev_b = math.sqrt(((10 - 20) ** 2 + (20 - 20) ** 2 + (30 - 20) ** 2) / 3)
    cv_b = stddev_b / mean_b
    expected_b = 1.0 / (1.0 + cv_b)
    assert abs(score_b - expected_b) < 1e-9, f"score_b≈{expected_b:.4f}; got {score_b}"


def test_fleet_stability_score_perfect_stability() -> None:
    """Constant latency → cv=0 → score=1.0."""
    _reset()
    store = _make_store(
        {
            "fssbt_const": [(_NOW - float(d), 99.0, True) for d in [900, 600, 300]],
        }
    )
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_const", store=store, now_ms=_NOW
    )
    assert result == 1.0


def test_fleet_stability_score_unknown_tool_returns_one() -> None:
    """Unknown tool → 1.0 (vacuously perfectly stable, no calls to violate stability)."""
    _reset()
    store = _make_store(
        {
            "fssbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 1.0
    assert isinstance(result, float)


def test_fleet_stability_score_empty_store_returns_one() -> None:
    """Empty store → 1.0 (no calls = vacuously stable)."""
    _reset()
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 1.0


def test_fleet_stability_score_in_range() -> None:
    """Score is always in [0.0, 1.0]."""
    _reset()
    store = _make_store(
        {
            "fssbt_range": [
                (_NOW - float(d), float(v), True)
                for d, v in [(900, 10), (700, 100), (500, 30), (300, 200), (100, 5)]
            ],
        }
    )
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_range", store=store, now_ms=_NOW
    )
    assert 0.0 <= result <= 1.0, f"score must be in [0,1]; got {result}"


def test_fleet_stability_score_outside_window_returns_one() -> None:
    """All calls outside window → 1.0 (empty → vacuously stable)."""
    _reset()
    store = _make_store(
        {
            "fssbt_old": [
                (_NOW - _WIN - 200, 10.0, True),
                (_NOW - _WIN - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_old", store=store, now_ms=_NOW
    )
    assert result == 1.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fssbt_rt": [(_NOW - float(d), 42.0, True) for d in [900, 600, 300]],
        }
    )
    result = get_windowed_fleet_latency_stability_score_by_tool(
        _WIN, "fssbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 1.0
