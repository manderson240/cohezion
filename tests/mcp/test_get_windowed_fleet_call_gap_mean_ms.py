"""Item 1102: get_windowed_fleet_call_gap_mean_ms(window_ms, *, store=None, now_ms=None) -> float
-- mean gap (ms) between consecutive timestamps across ALL pooled fleet calls
   = total_span / (n-1) where n=total pooled calls. 0.0 for <2 pooled calls.
Fleet dual of item 1090.

PRIMARY DISC.: tool_a ts=[t-500,t-300], tool_b ts=[t-400,t-200,t-0]
  pooled sorted=[t-500,t-400,t-300,t-200,t-0]; n=5, span=500ms
  fleet_mean_gap = 500/(5-1) = 125ms
  (PRIMARY DISC.: kills per-tool-avg-mean-gap:
    tool_a mean_gap=200ms, tool_b mean_gap=200ms, avg=200ms != 125ms;
    pooling adds 2 extra timestamps inside the span, reducing average gap;
    correct fleet mean_gap=125ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_gap_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_call_gap_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled mean_gap=125ms kills per-tool-avg=200ms."""
    _reset()
    store = _make_store(
        {
            "fgmean_disc_a": [
                (_NOW - 500, 10.0, True),
                (_NOW - 300, 20.0, True),
            ],
            "fgmean_disc_b": [
                (_NOW - 400, 30.0, True),
                (_NOW - 200, 40.0, True),
                (_NOW - 0, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # pooled sorted=[t-500,t-400,t-300,t-200,t-0]; span=500ms, n=5
    # mean_gap = 500/4 = 125ms
    assert abs(result - 125.0) < 1e-9, (
        f"pooled mean_gap=125ms; kills per-tool-avg=200ms; got {result}"
    )


def test_fleet_call_gap_mean_single_tool() -> None:
    """Single tool -> fleet mean gap equals that tool's mean gap."""
    _reset()
    store = _make_store(
        {
            "fgmean_single": [
                (_NOW - 600, 10.0, True),
                (_NOW - 300, 20.0, True),
                (_NOW - 0, 30.0, True),
            ],
        }
    )
    result = get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW)
    # span=600ms, n=3, mean_gap=600/2=300ms
    assert abs(result - 300.0) < 1e-9, f"single tool mean_gap=300ms; got {result}"


def test_fleet_call_gap_mean_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_call_gap_mean_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_call_gap_mean_single_pooled_call_returns_zero() -> None:
    """<2 pooled calls -> 0.0."""
    _reset()
    store = _make_store({"fgmean_one": [(_NOW - 100, 10.0, True)]})
    assert get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_gap_mean_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fgmean_old_a": [(_NOW - _WIN - 100, 10.0, True)],
            "fgmean_old_b": [(_NOW - _WIN - 200, 20.0, True)],
        }
    )
    assert get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_gap_mean_two_calls_from_different_tools() -> None:
    """Two calls from different tools -> span/(2-1) = span."""
    _reset()
    store = _make_store(
        {
            "fgmean_2a": [(_NOW - 400, 10.0, True)],
            "fgmean_2b": [(_NOW - 100, 20.0, True)],
        }
    )
    result = get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 300.0) < 1e-9, f"2-call gap=300ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fgmean_rt_a": [(_NOW - 500, 10.0, True)],
            "fgmean_rt_b": [(_NOW - 200, 20.0, True)],
        }
    )
    assert isinstance(get_windowed_fleet_call_gap_mean_ms(_WIN, store=store, now_ms=_NOW), float)
