"""Item 1109: get_windowed_fleet_call_failure_rate(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide failure rate = failures / total_calls in window.
Returns float in [0.0, 1.0].  0.0 for empty window.

PRIMARY DISC. (three-tool case): tool_a 2/2 fails, tool_b 1/4 fails, tool_c 0/3 fails
  -> pooled: 3 failures / 9 total = 0.333...
  (PRIMARY DISC.: kills per-tool-avg-rate = avg(1.0, 0.25, 0.0) = 0.417 (wrong);
   kills int_count = 3 (not normalized);
   kills 0.5 (only two tools counted);
   correct: pool ALL records, divide total_failures / total_calls).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_failure_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_failure_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled 3/9=0.333 != per-tool-avg-rate 0.417."""
    _reset()
    store = _make_store(
        {
            "fr_a": [
                (_NOW - 900, 10.0, False),  # fail
                (_NOW - 800, 10.0, False),  # fail
            ],  # tool_a: 2/2
            "fr_b": [
                (_NOW - 700, 10.0, True),  # ok
                (_NOW - 600, 10.0, False),  # fail
                (_NOW - 500, 10.0, True),  # ok
                (_NOW - 400, 10.0, True),  # ok
            ],  # tool_b: 1/4
            "fr_c": [
                (_NOW - 300, 10.0, True),  # ok
                (_NOW - 200, 10.0, True),  # ok
                (_NOW - 100, 10.0, True),  # ok
            ],  # tool_c: 0/3
        }
    )
    result = get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # pooled = 3/9 = 0.3333...; per-tool-avg = (1.0+0.25+0.0)/3 = 0.4167
    assert abs(result - (3.0 / 9.0)) < 1e-9, (
        f"pooled 3/9=0.333; kills per-tool-avg=0.417; got {result}"
    )


def test_fleet_failure_rate_all_failures() -> None:
    """All calls fail -> rate=1.0."""
    _reset()
    store = _make_store(
        {
            "fr_all_a": [(_NOW - 300, 10.0, False)] * 2,
            "fr_all_b": [(_NOW - 200, 10.0, False)] * 3,
        }
    )
    result = get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all fail -> 1.0; got {result}"


def test_fleet_failure_rate_no_failures() -> None:
    """No failures -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fr_none_a": [(_NOW - 300, 10.0, True)] * 2,
            "fr_none_b": [(_NOW - 200, 10.0, True)] * 3,
        }
    )
    assert get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_failure_rate_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_call_failure_rate(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_failure_rate_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fr_old": [(_NOW - _WIN - 100, 10.0, False)] * 5,
        }
    )
    assert get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_failure_rate_boundary() -> None:
    """Calls at boundary ts>=cutoff are included; outside excluded."""
    _reset()
    store = _make_store(
        {
            "fr_bnd": [
                (_NOW - _WIN - 1, 10.0, False),  # outside
                (_NOW - _WIN, 10.0, False),  # at boundary -> included
                (_NOW - 500, 10.0, True),  # inside success
            ],
        }
    )
    # 1 failure / 2 total = 0.5
    result = get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.5) < 1e-9, f"1 failure / 2 total = 0.5; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fr_rt": [(_NOW - 100, 10.0, False), (_NOW - 50, 10.0, True)],
        }
    )
    result = get_windowed_fleet_call_failure_rate(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
