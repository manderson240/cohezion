"""Item 1059: get_windowed_global_latency_gini_coefficient(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide Gini coefficient (pooled).

Fleet dual of per-tool item 1058. G=(2*sum(i*x_i)-(n+1)*sum(x_i))/(n*sum(x_i)) on pooled
sorted latencies (1-indexed). 0.0 for n_pooled<2 or sum==0. Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,10]+tool_b=[50,50] -> pooled sorted=[10,10,50,50] n=4
  sum=120, sum(i*x_i)=1*10+2*10+3*50+4*50=380
  G=(2*380-5*120)/(4*120)=160/480=1/3≈0.3333
  (PRIMARY DISC.: kills per-tool Gini avg:
     tool_a=[10,10] all-equal -> G=0; tool_b=[50,50] all-equal -> G=0; avg=0 ≠ 1/3;
   correct pooled Gini=1/3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_gini_coefficient,
    get_windowed_tool_latency_gini_coefficient,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10]+tool_b=[50,50] -> pooled Gini=1/3.

    Kills per-tool Gini avg: each all-equal -> 0; avg=0.0 ≠ pooled 1/3.
    Correct: pooled G=(2*380-5*120)/(4*120)=160/480=1/3.
    """
    _reset()
    store = _make_store(
        {
            "gg_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 10.0, True)],
            "gg_b": [(_NOW - 10, 50.0, True), (_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_latency_gini_coefficient(_WIN, store=store, now_ms=_NOW)
    # Per-tool: both all-equal -> 0
    per_a = get_windowed_tool_latency_gini_coefficient("gg_a", _WIN, store=store, now_ms=_NOW)
    per_b = get_windowed_tool_latency_gini_coefficient("gg_b", _WIN, store=store, now_ms=_NOW)
    assert per_a == 0.0 and per_b == 0.0, "per-tool should be 0 (all-equal)"
    assert isinstance(result, float)
    assert abs(result - 1 / 3) < 1e-9, f"pooled Gini=1/3; kills per-tool-avg=0.0; got {result}"


def test_global_gini_all_equal_returns_zero() -> None:
    """All-equal pooled -> Gini=0.0."""
    _reset()
    store = _make_store(
        {
            "gg_eq": [(_NOW - 10, 50.0, True)] * 6,
        }
    )
    result = get_windowed_global_latency_gini_coefficient(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> Gini=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_gini_coefficient(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gg_old": [(_NOW - _WIN - 100, 50.0, True)] * 4,
        }
    )
    assert get_windowed_global_latency_gini_coefficient(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_gini_in_range_zero_to_one() -> None:
    """Gini in [0, 1] for any realistic pooled input."""
    _reset()
    store = _make_store(
        {
            "gg_range_a": [(_NOW - 10, float(v), True) for v in [10, 100]],
            "gg_range_b": [(_NOW - 10, float(v), True) for v in [50, 500, 2000]],
        }
    )
    result = get_windowed_global_latency_gini_coefficient(_WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0, f"Gini must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gg_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_global_latency_gini_coefficient(_WIN, store=store, now_ms=_NOW), float
    )
