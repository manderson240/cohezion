"""Item 955: get_windowed_global_mean_latency_ms(window_ms, *, store=None, now_ms=None) -> float
-- mean latency across all tools in the recent window.

PRIMARY DISC.: tool A=[10,10,10]ms (3 calls) + tool B=[100]ms (1 call).
naive avg-of-means = (10+100)/2 = 55 WRONG.
correct = (10+10+10+100)/4 = 32.5.
Kills impl averaging per-tool means.
empty / no-recent-calls -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_weighted_mean_not_avg_of_means_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=[10,10,10] (3 calls), tool B=[100] (1 call).
    avg-of-means = (10+100)/2 = 55 WRONG.
    correct = (10+10+10+100)/4 = 32.5. Kills avg-per-tool-means impl."""
    _reset()
    store = _make_store({
        "wgm_a": [(_NOW - 10, 10.0, True)] * 3,
        "wgm_b": [(_NOW - 10, 100.0, True)],
    })
    result = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 32.5) < 0.001   # weighted correct
    assert abs(result - 55.0) > 1.0     # not naive avg-of-means


def test_empty_store_returns_zero() -> None:
    """No windowed calls -> 0.0."""
    _reset()
    assert get_windowed_global_mean_latency_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    store = _make_store({"ft_wgm": [(_NOW - 1, 5.0, True)]})
    result = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)


def test_single_call_mean_equals_latency() -> None:
    """Single recent call -> mean == that latency."""
    store = _make_store({"single_wgm": [(_NOW - 1, 77.0, True)]})
    result = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 77.0) < 0.001


def test_calls_outside_window_excluded() -> None:
    """Old calls are not included in the mean calculation."""
    store = _make_store({
        "wgm_mix": [
            (_NOW - _WIN - 1, 1000.0, True),   # outside window -- should NOT affect mean
            (_NOW - 10, 20.0, True),             # inside window
        ]
    })
    result = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 0.001


def test_all_calls_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "wgm_old": [(_NOW - _WIN - 100, 50.0, True)],
    })
    assert get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_single_tool_equals_per_tool_windowed_mean() -> None:
    """Single tool: global windowed mean == (sum of lats / count)."""
    store = _make_store({
        "consist_wgm": [(_NOW - 10, lat, True) for lat in [10.0, 20.0, 30.0]]
    })
    result = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 0.001   # (10+20+30)/3 = 20.0
