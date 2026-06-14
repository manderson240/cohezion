"""Item 1086: get_windowed_fleet_burst_hotspot(window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> tuple[str, int]
-- (tool_name, burst_count) for the tool with the MOST bursts (highest burst_count).
("", 0) if no tool has any bursts.

PRIMARY DISC.: tool_a=3 bursts, tool_b=1 burst, tool_c=2 bursts -> ("hotspot_a", 3)
  (PRIMARY DISC.: kills argmax-by-total-above-threshold: tool_b could have 10 isolated
   slow calls (burst_count=10 by that metric) while tool_a has 3 organized burst runs --
   the correct hotspot is the tool with the most DISTINCT burst incidents; correct
   ("hotspot_a", 3)).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_burst_hotspot,
)

_NOW = 1_000_000.0
_WIN = 2000.0  # wide window to capture all test data


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _burst_sequence(
    start_offset: float, n_bursts: int, base_step: float = 100.0
) -> list[tuple[float, float, bool]]:
    """Generate n_bursts alternating [low, high] pairs starting from start_offset back in time."""
    recs: list[tuple[float, float, bool]] = []
    ts = _NOW - start_offset
    for _ in range(n_bursts):
        recs.append((ts, 10.0, True))  # below threshold
        ts += base_step
        recs.append((ts, 100.0, True))  # above threshold (burst)
        ts += base_step
    recs.append((ts, 10.0, True))  # final recovery
    return recs


def test_fleet_burst_hotspot_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=3 bursts, tool_b=1, tool_c=2 -> ("hotspot_a", 3).

    Kills argmax-by-count (different metric from burst_count).
    Correct: argmax-by-burst-count = ("hotspot_a", 3).
    """
    _reset()
    store = _make_store(
        {
            "hotspot_a": _burst_sequence(1800.0, 3),  # 3 bursts -- MOST
            "hotspot_b": _burst_sequence(1600.0, 1),  # 1 burst
            "hotspot_c": _burst_sequence(1400.0, 2),  # 2 bursts
        }
    )
    result = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    tool, count = result
    assert tool == "hotspot_a", f"most bursts=3 is hotspot_a; got {tool}"
    assert count == 3, f"burst_count=3; got {count}"


def test_fleet_burst_hotspot_no_bursts_returns_sentinel() -> None:
    """No above-threshold calls -> ("", 0)."""
    _reset()
    store = _make_store(
        {
            "hspot_none_a": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100, 0]],
            "hspot_none_b": [(_NOW - float(d), 20.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert result == ("", 0), f"no bursts -> ('', 0); got {result}"


def test_fleet_burst_hotspot_empty_store_returns_sentinel() -> None:
    """Empty store -> ("", 0)."""
    _reset()
    result = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store={}, now_ms=_NOW)
    assert result == ("", 0), f"empty store -> ('', 0); got {result}"


def test_fleet_burst_hotspot_single_tool() -> None:
    """Single tool with bursts -> that tool is the hotspot."""
    _reset()
    store = _make_store(
        {
            "hspot_single": _burst_sequence(1000.0, 2),
        }
    )
    tool, count = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert tool == "hspot_single", f"only tool -> hotspot; got {tool}"
    assert count == 2, f"2 bursts; got {count}"


def test_fleet_burst_hotspot_tie_returns_a_winner() -> None:
    """Tied burst counts -> must return one of them (not crash, not sentinel)."""
    _reset()
    store = _make_store(
        {
            "hspot_tie_x": _burst_sequence(1500.0, 2),
            "hspot_tie_y": _burst_sequence(1200.0, 2),
        }
    )
    tool, count = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert tool in {"hspot_tie_x", "hspot_tie_y"}, f"one of the tied tools; got {tool}"
    assert count == 2, f"burst_count=2; got {count}"


def test_fleet_burst_hotspot_no_recent_calls_returns_sentinel() -> None:
    """All calls outside window -> ("", 0)."""
    _reset()
    store = _make_store(
        {
            "hspot_old": [(_NOW - _WIN - 100, 200.0, True)] * 5,
        }
    )
    result = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert result == ("", 0), f"all outside window -> ('', 0); got {result}"


def test_returns_tuple_type() -> None:
    """Return type is tuple[str, int]."""
    _reset()
    store = _make_store(
        {
            "hspot_rt": _burst_sequence(500.0, 1),
        }
    )
    result = get_windowed_fleet_burst_hotspot(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], str) and isinstance(result[1], int)
