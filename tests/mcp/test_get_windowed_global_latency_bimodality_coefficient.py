"""Item 1057: get_windowed_global_latency_bimodality_coefficient(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide bimodality coefficient BC=(skewness^2+1)/kurtosis_raw (pooled).

Fleet dual of per-tool item 1052. 0.0 for n_pooled<4 or variance==0. Injectable store.

PRIMARY DISC.: tool_a=[10,10,10,10]+tool_b=[100,100,100,100] -> pooled=[10]*4+[100]*4 n=8
  mean=55, var=2025, std=45, skewness=0 (symmetric bimodal), kurtosis_raw=1.0
  BC=(0^2+1)/1.0=1.0
  (PRIMARY DISC.: kills per-tool BC avg: each tool all-equal -> variance=0 -> BC=0 per tool,
     avg=0.0 ≠ 1.0; correct pooled bimodal BC=1.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_bimodality_coefficient,
    get_windowed_tool_bimodality_coefficient,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_bc_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10]*4 + tool_b=[100]*4 -> pooled BC=1.0.

    Kills per-tool BC avg: each tool all-equal -> variance=0 -> BC=0, avg=0.0.
    Correct: pooled skew=0, kurtosis_raw=1.0, BC=1.0.
    """
    _reset()
    store = _make_store({
        "gbc_a": [(_NOW - 10, 10.0, True)] * 4,
        "gbc_b": [(_NOW - 10, 100.0, True)] * 4,
    })
    result = get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW)
    # Per-tool BC: each all-equal -> 0.0; per-tool avg = 0.0 (WRONG)
    per_tool_a = get_windowed_tool_bimodality_coefficient("gbc_a", _WIN, store=store, now_ms=_NOW)
    per_tool_b = get_windowed_tool_bimodality_coefficient("gbc_b", _WIN, store=store, now_ms=_NOW)
    assert per_tool_a == 0.0 and per_tool_b == 0.0, "per-tool should be 0 (all-equal)"
    assert isinstance(result, float)
    assert abs(result - 1.0) < 1e-9, (
        f"pooled bimodal BC=1.0; kills per-tool-avg=0.0; got {result}"
    )


def test_global_bc_fewer_than_4_returns_zero() -> None:
    """n_pooled < 4 -> 0.0."""
    _reset()
    store = _make_store({
        "gbc_few": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
    })
    result = get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n_pooled=3 < 4 -> 0.0; got {result}"


def test_global_bc_all_equal_returns_zero() -> None:
    """All-equal pooled -> variance=0 -> 0.0."""
    _reset()
    store = _make_store({
        "gbc_eq": [(_NOW - 10, 50.0, True)] * 8,
    })
    result = get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> BC=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_bimodality_coefficient(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gbc_old": [(_NOW - _WIN - 100, 50.0, True)] * 6,
    })
    assert get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_bc_non_negative() -> None:
    """BC >= 0 (numerator skew^2+1 >= 1, kurtosis_raw > 0 for n>=4 non-equal)."""
    _reset()
    store = _make_store({
        "gbc_pos": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200, 50, 10, 200]],
    })
    result = get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"BC must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "gbc_rt": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 10, 100, 100, 100, 100]],
    })
    assert isinstance(
        get_windowed_global_latency_bimodality_coefficient(_WIN, store=store, now_ms=_NOW), float
    )
