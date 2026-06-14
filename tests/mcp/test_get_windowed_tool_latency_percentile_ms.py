"""Item 1093: get_windowed_tool_latency_percentile_ms(tool_name, window_ms, percentile, *, store=None, now_ms=None) -> float
-- p-th percentile latency (ms) using nearest-rank method.
0.0 for empty window.
nearest-rank index = ceil(percentile/100 * n) - 1  (0-based, clipped to [0, n-1]).

PRIMARY DISC.: 10 calls lats=[10..100]ms, p95 -> nearest-rank=100ms
  (PRIMARY DISC.: kills linear-interpolation: p95=95.5ms != 100ms;
   nearest-rank ceil(9.5)=10, index=9, value=100ms correct).
"""

from __future__ import annotations


from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_percentile_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_latency_percentile_primary_discriminator_p95() -> None:
    """PRIMARY DISC.: n=10, lats=[10,20,...,100], p95 -> nearest-rank=100ms.

    Kills linear-interpolation: 95.5ms != 100ms.
    ceil(0.95*10)=10, index=9 (0-based), value=100ms.
    """
    _reset()
    store = _make_store(
        {
            "pct_disc": [
                (_NOW - float(1000 - 10 * i), float(10 * (i + 1)), True) for i in range(10)
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_ms(
        "pct_disc", _WIN, 95.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 100.0) < 1e-9, (
        f"nearest-rank p95=100ms; kills linear-interp 95.5ms; got {result}"
    )


def test_latency_percentile_p50_median() -> None:
    """p50 on 10 values [10..100] -> nearest-rank index 4 -> 50ms."""
    _reset()
    store = _make_store(
        {
            "pct_p50": [
                (_NOW - float(1000 - 10 * i), float(10 * (i + 1)), True) for i in range(10)
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_ms(
        "pct_p50", _WIN, 50.0, store=store, now_ms=_NOW
    )
    # ceil(0.5*10)=5, index=4 -> value=50ms
    assert abs(result - 50.0) < 1e-9, f"p50=50ms; got {result}"


def test_latency_percentile_p90() -> None:
    """p90 on 10 values -> nearest-rank index 8 -> 90ms."""
    _reset()
    store = _make_store(
        {
            "pct_p90": [
                (_NOW - float(1000 - 10 * i), float(10 * (i + 1)), True) for i in range(10)
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_ms(
        "pct_p90", _WIN, 90.0, store=store, now_ms=_NOW
    )
    # ceil(0.9*10)=9, index=8 -> value=90ms
    assert abs(result - 90.0) < 1e-9, f"p90=90ms; got {result}"


def test_latency_percentile_p100_max() -> None:
    """p100 always returns maximum value."""
    _reset()
    store = _make_store(
        {
            "pct_max": [
                (_NOW - 500, 10.0, True),
                (_NOW - 300, 50.0, True),
                (_NOW - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_ms(
        "pct_max", _WIN, 100.0, store=store, now_ms=_NOW
    )
    assert abs(result - 200.0) < 1e-9, f"p100=max=200ms; got {result}"


def test_latency_percentile_p0_min() -> None:
    """p0 (or very small) returns minimum value."""
    _reset()
    store = _make_store(
        {
            "pct_min": [
                (_NOW - 500, 10.0, True),
                (_NOW - 300, 50.0, True),
                (_NOW - 100, 200.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_ms("pct_min", _WIN, 0.0, store=store, now_ms=_NOW)
    assert abs(result - 10.0) < 1e-9, f"p0=min=10ms; got {result}"


def test_latency_percentile_single_call() -> None:
    """Single call -> only value regardless of percentile."""
    _reset()
    store = _make_store({"pct_one": [(_NOW - 100, 42.0, True)]})
    result = get_windowed_tool_latency_percentile_ms(
        "pct_one", _WIN, 95.0, store=store, now_ms=_NOW
    )
    assert abs(result - 42.0) < 1e-9, f"single call -> 42ms; got {result}"


def test_latency_percentile_empty_window_returns_zero() -> None:
    """No calls in window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_percentile_ms("no_tool", _WIN, 95.0, store={}, now_ms=_NOW) == 0.0
    )


def test_latency_percentile_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "pct_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert (
        get_windowed_tool_latency_percentile_ms("pct_old", _WIN, 50.0, store=store, now_ms=_NOW)
        == 0.0
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "pct_rt": [(_NOW - float(d), 10.0 * d, True) for d in [100, 200, 300]],
        }
    )
    result = get_windowed_tool_latency_percentile_ms("pct_rt", _WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
