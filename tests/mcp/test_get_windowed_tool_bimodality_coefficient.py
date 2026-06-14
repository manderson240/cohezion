"""Item 1052: get_windowed_tool_bimodality_coefficient(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool bimodality coefficient (BC).

BC = (skewness^2 + 1) / kurtosis_raw
     where kurtosis_raw = kurtosis_excess + 3 = sum((x-mean)^4)/(n*std^4)
BC in [0, 1]; BC > 5/9 ≈ 0.555 suggests bimodal distribution.
0.0 for n < 4 or std == 0.

PRIMARY DISC.: uniform [10,20,...,100] n=10
  skewness=0.0 (symmetric), kurtosis_excess≈-1.2242, kurtosis_raw≈1.7758
  BC=(0+1)/1.7758≈0.5632 > 5/9 (flat/uniform data triggers bimodal test)
  (PRIMARY DISC.: kills BC=0.0 (zero for non-bimodal assumption);
   kills BC=1.0 (maximum bimodal);
   correct BC≈0.5632 via exact formula).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_bimodality_coefficient,
)

_NOW = 1_000_000.0
_WIN = 500.0
_BIMODAL_THRESHOLD = 5.0 / 9.0  # ≈ 0.5556


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_bimodality_primary_discriminator() -> None:
    """PRIMARY DISC.: uniform [10..100] n=10 -> BC≈0.5632 > 5/9.

    Kills BC=0.0 (zero-for-non-bimodal assumption).
    Kills BC=1.0 (maximum bimodal assumption).
    Correct: BC=(0+1)/kurtosis_raw≈0.5632 (flat distribution triggers bimodal test).
    """
    _reset()
    lats = [float(v) for v in range(10, 101, 10)]  # [10,20,...,100] n=10
    store = _make_store(
        {
            "bc_disc": [(_NOW - 10, v, True) for v in lats],
        }
    )
    result = get_windowed_tool_bimodality_coefficient("bc_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # Verify BC > bimodal threshold (flat/uniform triggers bimodal test)
    assert result > _BIMODAL_THRESHOLD, f"uniform [10..100] BC≈0.563 > 5/9≈0.556; got {result}"
    # Verify exact value (kills wrong implementations)
    n = len(lats)
    mean = sum(lats) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in lats) / n)
    kurt_raw = sum((x - mean) ** 4 for x in lats) / (n * std**4)
    skew = sum((x - mean) ** 3 for x in lats) / (n * std**3)
    expected = (skew**2 + 1) / kurt_raw
    assert abs(result - expected) < 1e-9, f"exact BC={expected:.6f}; got {result}"


def test_all_equal_returns_zero() -> None:
    """All equal -> std=0 -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bc_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_tool_bimodality_coefficient("bc_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> BC=0.0; got {result}"


def test_fewer_than_4_samples_returns_zero() -> None:
    """n < 4 -> 0.0 (kurtosis requires n >= 4)."""
    _reset()
    store = _make_store(
        {
            "bc_few": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        }
    )
    result = get_windowed_tool_bimodality_coefficient("bc_few", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n=3 < 4 -> BC=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_bimodality_coefficient("no_such_bc", _WIN, store={}, now_ms=_NOW) == 0.0
    )


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "bc_old": [(_NOW - _WIN - 100, 50.0, True)] * 6,
        }
    )
    assert get_windowed_tool_bimodality_coefficient("bc_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_bc_in_zero_to_one_range() -> None:
    """BC is always in [0, 1] (bounded by construction)."""
    _reset()
    store = _make_store(
        {
            "bc_rng": [(_NOW - 10, float(v), True) for v in [10, 20, 80, 90, 10, 90, 50, 50]],
        }
    )
    result = get_windowed_tool_bimodality_coefficient("bc_rng", _WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0 + 1e-9, f"BC must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"bc_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 80, 90, 50, 50]]})
    assert isinstance(
        get_windowed_tool_bimodality_coefficient("bc_rt", _WIN, store=store, now_ms=_NOW), float
    )
