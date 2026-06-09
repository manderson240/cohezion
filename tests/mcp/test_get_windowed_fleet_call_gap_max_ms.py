"""Item 1101: get_windowed_fleet_call_gap_max_ms(window_ms, *, store=None, now_ms=None) -> float
-- max gap (ms) between consecutive call timestamps across ALL pooled fleet calls.
0.0 for <2 pooled calls. Fleet dual of item 1089.

PRIMARY DISC.: tool_a ts=[t-600,t-200], tool_b ts=[t-500,t-100]
  pooled sorted=[t-600,t-500,t-200,t-100]; gaps=[100,300,100]; max=300ms
  (PRIMARY DISC.: kills per-tool-max-avg: tool_a max=400ms, tool_b max=400ms, avg=400ms != 300ms;
   pooled interleaving reveals the actual largest quiet period in fleet traffic;
   per-tool avg inflates because each tool's own gaps ignore the other tool's calls).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_gap_max_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_call_gap_max_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled max=300ms kills per-tool-avg=400ms.

    tool_a=[t-600,t-200]: own max gap=400ms.
    tool_b=[t-500,t-100]: own max gap=400ms. Per-tool avg=400ms.
    Pooled sorted=[t-600,t-500,t-200,t-100]: gaps=[100,300,100]; max=300ms.
    """
    _reset()
    store = _make_store({
        "fgap_disc_a": [
            (_NOW - 600, 10.0, True),
            (_NOW - 200, 20.0, True),
        ],
        "fgap_disc_b": [
            (_NOW - 500, 30.0, True),
            (_NOW - 100, 40.0, True),
        ],
    })
    result = get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 300.0) < 1e-9, (
        f"pooled max=300ms; kills per-tool-avg=400ms; got {result}"
    )


def test_fleet_call_gap_max_single_tool() -> None:
    """Single tool -> fleet max gap equals that tool's max gap."""
    _reset()
    store = _make_store({
        "fgap_single": [
            (_NOW - 500, 10.0, True),
            (_NOW - 200, 20.0, True),
            (_NOW - 0, 30.0, True),
        ],
    })
    result = get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 300.0) < 1e-9, f"max gap=[300,200], max=300ms; got {result}"


def test_fleet_call_gap_max_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_call_gap_max_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_call_gap_max_single_pooled_call_returns_zero() -> None:
    """<2 pooled calls -> no gaps -> 0.0."""
    _reset()
    store = _make_store({"fgap_one": [(_NOW - 100, 10.0, True)]})
    assert get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_gap_max_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fgap_old_a": [(_NOW - _WIN - 100, 10.0, True)],
        "fgap_old_b": [(_NOW - _WIN - 200, 20.0, True)],
    })
    assert get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_call_gap_max_three_tools_interleaved() -> None:
    """Three tools interleaving fills time; verifies pooling."""
    _reset()
    # tool_a: t-900, t-600 (own gap=300)
    # tool_b: t-750, t-450 (own gap=300)
    # tool_c: t-300, t-0   (own gap=300)
    # Pooled sorted: [900,750,600,450,300,0]; gaps=[150,150,150,150,300]; max=300ms
    store = _make_store({
        "fgap_3a": [(_NOW - 900, 10.0, True), (_NOW - 600, 20.0, True)],
        "fgap_3b": [(_NOW - 750, 30.0, True), (_NOW - 450, 40.0, True)],
        "fgap_3c": [(_NOW - 300, 50.0, True), (_NOW - 0, 60.0, True)],
    })
    result = get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 300.0) < 1e-9, f"pooled max gap=300ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fgap_rt_a": [(_NOW - 500, 10.0, True)],
        "fgap_rt_b": [(_NOW - 200, 20.0, True)],
    })
    assert isinstance(get_windowed_fleet_call_gap_max_ms(_WIN, store=store, now_ms=_NOW), float)
