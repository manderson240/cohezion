"""Item 968: get_windowed_latency_percentile(tool_name, percentile, window_ms, *, store=None, now_ms=None) -> float
-- arbitrary-percentile windowed latency for a single tool.

PRIMARY DISC.: 5 calls lats=[10,20,30,40,50], percentile=80 -> 42.0 (linear interp).
Kills impl always returning p50 or p95 hard-coded.
Kills impl returning p100=50.0 instead of the interpolated value.
percentile=50 agrees with get_windowed_tool_telemetry_full() p50_ms.
0 calls -> 0.0; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_latency_percentile,
    get_windowed_tool_telemetry_full,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_arbitrary_percentile_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls [10,20,30,40,50], p80 -> 42.0 (linear interp at idx=3.2).
    Kills hardcoded p50 impl (30.0 != 42.0) and hardcoded p95 impl (48.0 != 42.0)."""
    _reset()
    store = _make_store(
        {
            "wlp_a": [
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
                (_NOW - 10, 40.0, True),
                (_NOW - 10, 50.0, True),
            ]
        }
    )
    result = get_windowed_latency_percentile("wlp_a", 80.0, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 42.0) < 0.001  # linear interp: idx=3.2 -> 40+0.2*(50-40)=42.0


def test_not_p50_not_p95() -> None:
    """Confirms result differs from both p50 and p95 for this input.
    p50=30.0, p95=48.0; p80 must be 42.0 (distinct from both)."""
    store = _make_store(
        {
            "wlp_b": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    p80 = get_windowed_latency_percentile("wlp_b", 80.0, _WIN, store=store, now_ms=_NOW)
    p50 = get_windowed_latency_percentile("wlp_b", 50.0, _WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_latency_percentile("wlp_b", 95.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p50 - 30.0) < 0.001
    assert abs(p95 - 48.0) < 0.001
    assert abs(p80 - 42.0) < 0.001
    assert p80 != p50
    assert p80 != p95


def test_p50_agrees_with_windowed_tool_telemetry_full() -> None:
    """p50 from this function must equal p50_ms from get_windowed_tool_telemetry_full."""
    _reset()
    store = _make_store(
        {
            "wlp_consist": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45]],
        }
    )
    p50_direct = get_windowed_latency_percentile(
        "wlp_consist", 50.0, _WIN, store=store, now_ms=_NOW
    )
    full = get_windowed_tool_telemetry_full("wlp_consist", _WIN, store=store, now_ms=_NOW)
    assert abs(p50_direct - full["p50_ms"]) < 0.001


def test_p95_agrees_with_windowed_tool_telemetry_full() -> None:
    """p95 from this function must equal p95_ms from get_windowed_tool_telemetry_full."""
    _reset()
    store = _make_store(
        {
            "wlp_consist2": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45]],
        }
    )
    p95_direct = get_windowed_latency_percentile(
        "wlp_consist2", 95.0, _WIN, store=store, now_ms=_NOW
    )
    full = get_windowed_tool_telemetry_full("wlp_consist2", _WIN, store=store, now_ms=_NOW)
    assert abs(p95_direct - full["p95_ms"]) < 0.001


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_latency_percentile("no_such_wlp", 50.0, _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "wlp_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
        }
    )
    assert get_windowed_latency_percentile("wlp_old", 50.0, _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_any_percentile_returns_that_latency() -> None:
    """Single call -> every percentile returns the single latency."""
    store = _make_store({"wlp_single": [(_NOW - 10, 77.0, True)]})
    for pct in [0.0, 25.0, 50.0, 75.0, 100.0]:
        val = get_windowed_latency_percentile("wlp_single", pct, _WIN, store=store, now_ms=_NOW)
        assert abs(val - 77.0) < 0.001, f"p{pct} should be 77.0, got {val}"


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wlp": [(_NOW - 10, 5.0, True)]})
    assert isinstance(
        get_windowed_latency_percentile("rtype_wlp", 50.0, _WIN, store=store, now_ms=_NOW),
        float,
    )
