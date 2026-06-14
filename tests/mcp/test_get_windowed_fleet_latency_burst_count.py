"""Item 1114: get_windowed_fleet_latency_burst_count(window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> int
-- fleet-wide total burst count = sum of per-tool burst counts across all tools.
Returns int. 0 for empty window.

PRIMARY DISC.: tool_a has 2 burst-runs, tool_b has 1 burst-run -> fleet_total=3
  (PRIMARY DISC.: kills hotspot_count=2 (max-per-tool, not sum);
   kills per-tool-first=2 (only first tool);
   kills 0 (wrong threshold direction);
   correct: sum burst_count over all tools, return int=3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_burst_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0  # burst threshold ms


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_burst_count_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=2 bursts + tool_b=1 burst -> fleet_total=3.

    Kills hotspot=2 (max not sum); kills first-tool-only=2.
    """
    _reset()
    store = _make_store(
        {
            "fb_a": [
                # burst run 1: low, HIGH, HIGH, low
                (_NOW - 900, 10.0, True),  # low
                (_NOW - 800, 80.0, True),  # HIGH -> burst 1 start
                (_NOW - 700, 90.0, True),  # HIGH -> still burst 1
                (_NOW - 600, 10.0, True),  # low -> burst 1 end
                # burst run 2: HIGH, low
                (_NOW - 500, 70.0, True),  # HIGH -> burst 2 start
                (_NOW - 400, 10.0, True),  # low -> burst 2 end
            ],
            "fb_b": [
                # burst run 1: low, HIGH, HIGH, HIGH, low
                (_NOW - 350, 10.0, True),  # low
                (_NOW - 250, 60.0, True),  # HIGH -> burst 1 start
                (_NOW - 150, 65.0, True),  # HIGH -> still burst 1
                (_NOW - 100, 10.0, True),  # low -> burst 1 end
            ],
        }
    )
    result = get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 3, (
        f"tool_a=2+tool_b=1=fleet_total=3; kills hotspot=2; kills first=2; got {result}"
    )


def test_fleet_burst_count_single_tool() -> None:
    """Only one tool active -> fleet count = per-tool count."""
    _reset()
    store = _make_store(
        {
            "fb_solo": [
                (_NOW - 500, 80.0, True),  # HIGH burst 1
                (_NOW - 400, 10.0, True),  # low
                (_NOW - 300, 70.0, True),  # HIGH burst 2
                (_NOW - 200, 10.0, True),  # low
            ],
        }
    )
    assert get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW) == 2


def test_fleet_burst_count_no_bursts_returns_zero() -> None:
    """All latencies at or below threshold -> 0."""
    _reset()
    store = _make_store(
        {
            "fb_none_a": [(_NOW - 300, 30.0, True)] * 3,
            "fb_none_b": [(_NOW - 200, 50.0, True)] * 2,  # exactly at threshold
        }
    )
    assert get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW) == 0


def test_fleet_burst_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    assert get_windowed_fleet_latency_burst_count(_WIN, _THR, store={}, now_ms=_NOW) == 0


def test_fleet_burst_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fb_old": [(_NOW - _WIN - 100, 80.0, True)] * 5,
        }
    )
    assert get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW) == 0


def test_fleet_burst_count_sums_not_maxes() -> None:
    """Fleet total is sum; verify with unequal per-tool counts."""
    _reset()
    store = _make_store(
        {
            # tool_x: 3 bursts
            "fb_x": [
                (_NOW - 900, 80.0, True),  # burst 1
                (_NOW - 800, 10.0, True),  # exit
                (_NOW - 700, 80.0, True),  # burst 2
                (_NOW - 600, 10.0, True),  # exit
                (_NOW - 500, 80.0, True),  # burst 3
                (_NOW - 400, 10.0, True),  # exit
            ],
            # tool_y: 1 burst
            "fb_y": [
                (_NOW - 300, 80.0, True),  # burst 1
                (_NOW - 200, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW)
    assert result == 4, f"3+1=4; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fb_rt": [(_NOW - 200, 80.0, True), (_NOW - 100, 10.0, True)],
        }
    )
    result = get_windowed_fleet_latency_burst_count(_WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1
