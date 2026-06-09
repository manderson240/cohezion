"""Item 1051: get_windowed_global_latency_entropy_bits(window_ms, n_bins=10, *, store=None, now_ms=None) -> float
-- fleet-wide Shannon entropy (pooled raw latencies, bits).

Pool ALL tool latencies; bin into n_bins equal-width buckets over [min, max];
H = -sum(p*log2(p)); 0.0 for <2 pooled samples or all-equal pool.
Fleet dual of per-tool item 1050. Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,10]+tool_b=[100,100] -> pooled=[10,10,100,100] n=4, n_bins=2
  bin[0]={10,10} p=0.5, bin[1]={100,100} p=0.5 -> H=1.0 bit
  (PRIMARY DISC.: kills per-tool entropy avg: each tool all-equal → H=0 each → avg=0.0 ≠ 1.0;
   kills H=0.0 (single-bin assumption);
   correct pooled H=1.0 bit).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_entropy_bits,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_entropy_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10]+tool_b=[100,100] -> pooled H=1.0 bit.

    Kills per-tool entropy avg: each tool all-equal -> H=0.0 each -> avg=0.0.
    Kills H=0.0 (wrong single-bin assumption).
    Correct: pooled n_bins=2, each bin p=0.5 -> H=1.0 bit.
    """
    _reset()
    store = _make_store({
        "gent_a": [(_NOW - 10, 10.0, True)] * 2,
        "gent_b": [(_NOW - 10, 100.0, True)] * 2,
    })
    result = get_windowed_global_latency_entropy_bits(_WIN, n_bins=2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 1.0) < 1e-9, (
        f"pooled H=1.0 bit; kills per-tool-avg=0.0; got {result}"
    )


def test_all_equal_pooled_entropy_zero() -> None:
    """All pooled latencies equal -> H=0.0 (single occupied bin)."""
    _reset()
    store = _make_store({
        "gent_eq": [(_NOW - 10, 50.0, True)] * 8,
    })
    result = get_windowed_global_latency_entropy_bits(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal pool -> H=0.0; got {result}"


def test_uniform_pooled_entropy() -> None:
    """Uniform pooled distribution [10,20,30,40,50] n_bins=5 -> H=log2(5)≈2.322."""
    _reset()
    store = _make_store({
        "gent_uni": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_global_latency_entropy_bits(_WIN, n_bins=5, store=store, now_ms=_NOW)
    expected = math.log2(5)
    assert abs(result - expected) < 1e-9, (
        f"uniform 5-bin pool -> H=log2(5)≈{expected:.4f}; got {result}"
    )


def test_entropy_bounded_by_log2_n_bins() -> None:
    """Entropy <= log2(n_bins) (maximum for uniform distribution)."""
    _reset()
    store = _make_store({
        "gent_bnd": [(_NOW - 10, float(v), True) for v in range(10, 110, 10)],
    })
    n_bins = 10
    result = get_windowed_global_latency_entropy_bits(
        _WIN, n_bins=n_bins, store=store, now_ms=_NOW
    )
    assert result <= math.log2(n_bins) + 1e-9, (
        f"entropy <= log2({n_bins})={math.log2(n_bins):.4f}; got {result}"
    )


def test_entropy_non_negative() -> None:
    """Entropy is always >= 0."""
    _reset()
    store = _make_store({
        "gent_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10, 200]],
    })
    result = get_windowed_global_latency_entropy_bits(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"entropy must be non-negative; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_entropy_bits(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gent_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_global_latency_entropy_bits(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gent_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(get_windowed_global_latency_entropy_bits(_WIN, store=store, now_ms=_NOW), float)
