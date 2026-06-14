"""Item 1088: get_windowed_fleet_above_threshold_fraction(window_ms, threshold_ms, *, store=None, now_ms=None) -> float
-- fleet-wide fraction of ALL pooled calls where latency > threshold_ms.
0.0 for empty window. Range [0,1]. Fleet dual of item 1087.

PRIMARY DISC.: tool_a=[10,80,90] (2/3 above), tool_b=[20,70,85,15] (2/4 above)
  -> pooled [10,80,90,20,70,85,15]: 4/7 ≈ 0.5714
  (PRIMARY DISC.: kills per-tool-avg-fractions: (0.667+0.5)/2=0.583 != 0.5714;
   correct pooled fraction=4/7≈0.5714).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_above_threshold_fraction,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_above_fraction_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a 2/3 above, tool_b 2/4 above -> pooled 4/7≈0.5714.

    Kills per-tool-avg-fractions=(0.667+0.5)/2=0.583 (different denominator weighting).
    Correct: pooled count/total=4/7≈0.5714.
    """
    _reset()
    store = _make_store(
        {
            "faf_disc_a": [
                (_NOW - float(i * 100), lat, True) for i, lat in enumerate([10.0, 80.0, 90.0])
            ],
            "faf_disc_b": [
                (_NOW - float(i * 100), lat, True) for i, lat in enumerate([20.0, 70.0, 85.0, 15.0])
            ],
        }
    )
    result = get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - (4.0 / 7.0)) < 1e-9, (
        f"pooled 4/7≈0.5714; kills per-tool avg=0.583; got {result}"
    )


def test_fleet_above_fraction_all_above_returns_one() -> None:
    """All calls above threshold -> 1.0."""
    _reset()
    store = _make_store(
        {
            "faf_all_a": [(_NOW - float(d), 100.0, True) for d in [300, 200]],
            "faf_all_b": [(_NOW - float(d), 90.0, True) for d in [100, 0]],
        }
    )
    result = get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all above -> 1.0; got {result}"


def test_fleet_above_fraction_none_above_returns_zero() -> None:
    """No calls above threshold -> 0.0."""
    _reset()
    store = _make_store(
        {
            "faf_none_a": [(_NOW - float(d), 10.0, True) for d in [300, 200]],
            "faf_none_b": [(_NOW - float(d), 20.0, True) for d in [100, 0]],
        }
    )
    result = get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 0.0, f"none above -> 0.0; got {result}"


def test_fleet_above_fraction_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store={}, now_ms=_NOW) == 0.0


def test_fleet_above_fraction_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "faf_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
        }
    )
    assert get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW) == 0.0


def test_fleet_above_fraction_threshold_boundary_exclusive() -> None:
    """Calls at exactly threshold are NOT counted (strictly >)."""
    _reset()
    store = _make_store(
        {
            "faf_bound_a": [(_NOW - 200, 50.0, True)],  # at threshold
            "faf_bound_b": [(_NOW - 100, 51.0, True)],  # above
            "faf_bound_c": [(_NOW - 0, 50.0, True)],  # at threshold
        }
    )
    result = get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW)
    assert abs(result - (1.0 / 3.0)) < 1e-9, f"1/3 above; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "faf_rt_a": [(_NOW - 100, 100.0, True)],
            "faf_rt_b": [(_NOW - 50, 10.0, True)],
        }
    )
    assert isinstance(
        get_windowed_fleet_above_threshold_fraction(_WIN, 50.0, store=store, now_ms=_NOW), float
    )
