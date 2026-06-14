"""Item 1185: get_windowed_fleet_latency_kurtosis_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency excess kurtosis (fourth standardised moment minus 3).
Returns float. 0.0 for unknown/empty tool or when stddev == 0.
Formula: sum((x - mean)^4) / (n * stddev^4) - 3.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50]      → uniform-like, kurtosis_a = -1.3 (platykurtic)
  tool_b=[30x6 + 5.0 + 55.0]  → concentrated center with outliers, kurtosis_b = 1.0
  kurtosis_a=-1.3 kills kurtosis_b=1.0; kills always-0.
  Excess kurtosis > 0 = heavier tails than Gaussian (latency spikes more extreme).
  Excess kurtosis < 0 = lighter tails (bounded, uniform-like).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_kurtosis_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_kurtosis_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: kurtosis_a=-1.3 kills kurtosis_b=1.0; kills always-0."""
    _reset()
    # tool_a: uniform-like [10,20,30,40,50] → kurtosis = -1.3
    ts_offsets_a = [900, 800, 700, 600, 500]
    lats_a = [10.0, 20.0, 30.0, 40.0, 50.0]
    # tool_b: concentrated center + outliers [30x6, 5, 55] → kurtosis = 1.0
    ts_offsets_b = [490, 480, 470, 460, 450, 440, 430, 420]
    lats_b = [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 5.0, 55.0]
    store = _make_store(
        {
            "fkrtbt_a": [(_NOW - float(d), lat, True) for d, lat in zip(ts_offsets_a, lats_a)],
            "fkrtbt_b": [(_NOW - float(d), lat, True) for d, lat in zip(ts_offsets_b, lats_b)],
        }
    )
    result_a = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_a", store=store, now_ms=_NOW
    )
    result_b = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(result_a, float), f"expected float, got {type(result_a)}"
    assert abs(result_a - (-1.3)) < 1e-9, f"kurtosis_a (uniform-like) = -1.3; got {result_a}"
    assert abs(result_b - 1.0) < 1e-9, f"kurtosis_b (centered with outliers) = 1.0; got {result_b}"


def test_fleet_kurtosis_by_tool_platykurtic_is_negative() -> None:
    """Uniform-like distribution → excess kurtosis < 0."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_uni": [
                (_NOW - float(d), float(lat), True)
                for d, lat in zip([900, 800, 700, 600, 500], [10, 20, 30, 40, 50])
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_uni", store=store, now_ms=_NOW
    )
    assert result < 0, f"uniform-like → platykurtic < 0; got {result}"


def test_fleet_kurtosis_by_tool_leptokurtic_is_positive() -> None:
    """Concentrated center + outliers → excess kurtosis > 0."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_lep": [
                (_NOW - float(d), lat, True)
                for d, lat in zip(
                    [490, 480, 470, 460, 450, 440, 430, 420],
                    [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 5.0, 55.0],
                )
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_lep", store=store, now_ms=_NOW
    )
    assert result > 0, f"leptokurtic → kurtosis > 0; got {result}"


def test_fleet_kurtosis_by_tool_uniform_stddev_zero_returns_zero() -> None:
    """All same latency → stddev=0 → kurtosis=0.0 (guard)."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_same": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_same", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_kurtosis_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_kurtosis_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_kurtosis_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_kurtosis_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_old", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fkrtbt_rt": [
                (_NOW - float(d), float(lat), True)
                for d, lat in zip([900, 800, 700, 600, 500], [10, 20, 30, 40, 50])
            ],
        }
    )
    result = get_windowed_fleet_latency_kurtosis_by_tool(
        _WIN, "fkrtbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - (-1.3)) < 1e-9
