"""Item 1046: get_windowed_global_latency_p5_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 5th-percentile latency (pooled raw values).

Thin delegate: get_windowed_global_latency_percentile(5.0, window_ms, ...).
0.0 for empty/no-recent pool. Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[40,50] -> pooled=[10,20,30,40,50] n=5
  idx = 0.05*4 = 0.2 -> 10 + 0.2*(20-10) = 12.0
  (PRIMARY DISC.: kills per-tool-then-avg:
     p5_a=idx=0.2->10+0.2*10=12.0, p5_b=idx=0.2->40+0.2*10=42.0, avg=27.0 ≠ 12.0;
   kills nearest-rank=10.0 (no interpolation);
   correct pooled p5=12.0 via linear interpolation).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_p5_ms,
    get_windowed_global_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_p5_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,20,30]+tool_b=[40,50] -> pooled p5=12.0.

    Kills per-tool-then-avg=(12.0+42.0)/2=27.0 (NOT pooled).
    Kills nearest-rank=10.0 (no interpolation).
    Correct: pooled idx=0.2 -> 10+0.2*(20-10)=12.0.
    """
    _reset()
    store = _make_store(
        {
            "gp5_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
            "gp5_b": [(_NOW - 10, float(v), True) for v in [40, 50]],
        }
    )
    result = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 12.0) < 1e-9, (
        f"pooled p5=12.0; kills per-tool-avg=27.0 and nearest-rank=10.0; got {result}"
    )


def test_global_p5_matches_percentile_delegate() -> None:
    """p5 == get_windowed_global_latency_percentile(5.0, ...) exactly."""
    _reset()
    store = _make_store(
        {
            "gp5_del": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    p5 = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    direct = get_windowed_global_latency_percentile(5.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p5 - direct) < 1e-9, f"p5={p5} != direct={direct}"


def test_global_p5_ten_values() -> None:
    """[10..100] n=10 -> idx=0.05*9=0.45 -> 10+0.45*10=14.5."""
    _reset()
    store = _make_store(
        {
            "gp5_ten": [(_NOW - 10, float(v), True) for v in range(10, 101, 10)],
        }
    )
    result = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 14.5) < 1e-9, f"p5=14.5 for [10..100]; got {result}"


def test_single_call_p5_equals_value() -> None:
    """Single call -> p5 = that value."""
    _reset()
    store = _make_store(
        {
            "gp5_one": [(_NOW - 10, 75.0, True)],
        }
    )
    result = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 75.0) < 1e-9, f"single call -> p5=75.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_p5_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gp5_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_all_equal_p5_equals_value() -> None:
    """All equal latencies -> p5 = that value."""
    _reset()
    store = _make_store(
        {
            "gp5_eq": [(_NOW - 10, 60.0, True)] * 6,
        }
    )
    result = get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 60.0) < 1e-9, f"all-equal -> p5=60.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gp5_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(get_windowed_global_latency_p5_ms(_WIN, store=store, now_ms=_NOW), float)
