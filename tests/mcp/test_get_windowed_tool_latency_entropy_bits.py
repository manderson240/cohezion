"""Item 1050: get_windowed_tool_latency_entropy_bits(tool_name, window_ms, n_bins=10, *, store=None, now_ms=None) -> float
-- per-tool Shannon entropy of the latency distribution (bits).

Bin latency values into n_bins equal-width buckets over [min, max].
H = -sum(p * log2(p)) over non-empty bins; 0.0 for <2 samples or all-equal.

PRIMARY DISC. (all-equal case): lats [50]*8 -> single bin p=1.0 -> H=0.0
  (PRIMARY DISC.: kills H=log2(8)=3.0 uniform-8 assumption; correct H=0.0).

PRIMARY DISC. (uniform case): lats [10,20,30,40,50] n=5, n_bins=5
  -> each bin has 1 value, all p=0.2 -> H=log2(5)≈2.322 bits
  (PRIMARY DISC.: kills H=0.0 (all-equal assumption);
   kills H=log2(10)≈3.32 (wrong n_bins assumption);
   correct H=log2(5)≈2.322 bits).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_entropy_bits,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_all_equal_entropy_zero() -> None:
    """PRIMARY DISC. (all-equal): [50]*8 -> H=0.0.

    Kills H=log2(8)=3.0 (uniform-8 assumption).
    Correct: single bin p=1.0 -> H=0.0.
    """
    _reset()
    store = _make_store(
        {
            "ent_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_tool_latency_entropy_bits("ent_eq", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.0) < 1e-9, f"all-equal [50]*8 -> H=0.0; kills H=3.0; got {result}"


def test_uniform_five_bins_entropy() -> None:
    """PRIMARY DISC. (uniform): [10,20,30,40,50] n_bins=5 -> H=log2(5)≈2.322.

    Each bin has exactly 1 of 5 values -> p=0.2 for each -> H=log2(5).
    Kills H=0.0 (all-equal assumption).
    Kills H=log2(10)≈3.32 (wrong n_bins).
    """
    _reset()
    lats = [10.0, 20.0, 30.0, 40.0, 50.0]
    store = _make_store(
        {
            "ent_uni": [(_NOW - 10, v, True) for v in lats],
        }
    )
    result = get_windowed_tool_latency_entropy_bits(
        "ent_uni", _WIN, n_bins=5, store=store, now_ms=_NOW
    )
    expected = math.log2(5)
    assert abs(result - expected) < 1e-9, f"uniform 5-bin -> H=log2(5)≈{expected:.6f}; got {result}"


def test_single_call_entropy_zero() -> None:
    """Single call -> <2 samples -> H=0.0."""
    _reset()
    store = _make_store(
        {
            "ent_one": [(_NOW - 10, 75.0, True)],
        }
    )
    result = get_windowed_tool_latency_entropy_bits("ent_one", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"single call -> H=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_entropy_bits("no_such_ent", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "ent_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert get_windowed_tool_latency_entropy_bits("ent_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_entropy_non_negative() -> None:
    """Entropy is always >= 0."""
    _reset()
    store = _make_store(
        {
            "ent_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10, 200]],
        }
    )
    result = get_windowed_tool_latency_entropy_bits("ent_pos", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"entropy must be non-negative; got {result}"


def test_entropy_bounded_by_log2_n_bins() -> None:
    """Entropy <= log2(n_bins) (maximum when all bins equally occupied)."""
    _reset()
    store = _make_store(
        {
            "ent_bnd": [(_NOW - 10, float(v), True) for v in range(10, 110, 10)],
        }
    )
    n_bins = 10
    result = get_windowed_tool_latency_entropy_bits(
        "ent_bnd", _WIN, n_bins=n_bins, store=store, now_ms=_NOW
    )
    assert result <= math.log2(n_bins) + 1e-9, (
        f"entropy <= log2({n_bins})={math.log2(n_bins):.4f}; got {result}"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"ent_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_entropy_bits("ent_rt", _WIN, store=store, now_ms=_NOW), float
    )
