"""Item 1029: get_windowed_tool_p10_p90_ratio(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- p10/p90 ratio (tail symmetry index).

ratio = p10 / p90
0.0 if p90 == 0 (guard against division by zero).
Injectable store. Pure function.

Always in (0, 1] for non-degenerate distributions (p10 <= p90).
ratio -> 1.0 = symmetric distribution.
ratio -> 0.0 = extreme right tail (slow outliers dominate).

PRIMARY DISC.: lats [10, 20, 30, 40, 50]
  p10 = 14.0 (idx=0.4 -> 10+0.4*(20-10) = 14.0)
  p90 = 46.0 (idx=3.6 -> 40+0.6*(50-40) = 46.0)
  ratio = 14/46 ≈ 0.30435
  (kills p90/p10=46/14≈3.286 (inverted ratio);
   kills p10-p90=32.0 (difference not ratio);
   correct ratio≈0.30435 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p10_p90_ratio,
    get_windowed_tool_p10_ms,
    get_windowed_tool_p90_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p10_p90_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> ratio=14/46≈0.30435.

    Kills p90/p10=46/14≈3.286 (inverted).
    Kills p10-p90=32.0 (difference not ratio).
    Correct: p10/p90 = 14.0/46.0 ≈ 0.30435.
    """
    _reset()
    store = _make_store(
        {
            "rat_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tool_p10_p90_ratio("rat_a", _WIN, store=store, now_ms=_NOW)
    p10 = get_windowed_tool_p10_ms("rat_a", _WIN, store=store, now_ms=_NOW)
    p90 = get_windowed_tool_p90_ms("rat_a", _WIN, store=store, now_ms=_NOW)
    expected = p10 / p90
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"ratio=p10/p90={expected:.6f}; kills inverted={1 / expected:.3f} or diff={p90 - p10}; got {result}"
    )


def test_symmetric_distribution_ratio_near_one() -> None:
    """Symmetric distribution (all equal) -> ratio == 1.0."""
    _reset()
    store = _make_store(
        {
            "rat_sym": [(_NOW - 10, 100.0, True)] * 10,
        }
    )
    result = get_windowed_tool_p10_p90_ratio("rat_sym", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all-equal -> ratio=1.0; got {result}"


def test_ratio_is_less_than_or_equal_one() -> None:
    """p10 <= p90 always -> ratio <= 1.0."""
    _reset()
    store = _make_store(
        {
            "rat_ord": [(_NOW - 10, float(v), True) for v in [1, 10, 50, 100, 500, 1000]],
        }
    )
    result = get_windowed_tool_p10_p90_ratio("rat_ord", _WIN, store=store, now_ms=_NOW)
    assert result <= 1.0 + 1e-9, f"p10<=p90 -> ratio<=1.0; got {result}"


def test_heavy_right_tail_ratio_near_zero() -> None:
    """Heavy right tail -> ratio << 1.0."""
    _reset()
    # lats: mostly fast (10ms), one huge outlier (10000ms)
    store = _make_store(
        {
            "rat_tail": [(_NOW - 10, 10.0, True)] * 9 + [(_NOW - 10, 10000.0, True)],
        }
    )
    result = get_windowed_tool_p10_p90_ratio("rat_tail", _WIN, store=store, now_ms=_NOW)
    assert result < 0.1, f"extreme right tail -> ratio<<1.0; got {result}"


def test_p90_zero_guard_returns_zero() -> None:
    """When p90==0 (all zero latencies) -> ratio=0.0 (guard)."""
    _reset()
    store = _make_store(
        {
            "rat_zero": [(_NOW - 10, 0.0, True)] * 5,
        }
    )
    result = get_windowed_tool_p10_p90_ratio("rat_zero", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"p90=0 -> ratio=0.0 (guard); got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p10_p90_ratio("no_such_rat", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "rat_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_tool_p10_p90_ratio("rat_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"rat_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]]})
    assert isinstance(
        get_windowed_tool_p10_p90_ratio("rat_rt", _WIN, store=store, now_ms=_NOW), float
    )
