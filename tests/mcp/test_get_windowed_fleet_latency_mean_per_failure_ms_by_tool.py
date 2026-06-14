"""Item 1206: get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool mean latency of FAILED calls only (ok=False) within window.
Returns float. 0.0 for unknown/empty tool or no failed calls.
Formula: sum(lat for ok=False calls) / count(ok=False calls).

PRIMARY DISC.:
  tool_a: [(10ms,ok=T),(100ms,ok=F),(200ms,ok=F)] → mean_failure=150.0
  tool_b: [(50ms,ok=T),(50ms,ok=T)] → mean_failure=0.0 (no failures)
  mean_failure_a=150.0 kills mean_failure_b=0.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mean_per_failure_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mean_per_failure_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: mean_failure_a=150.0 kills mean_failure_b=0.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_a": [
                (_NOW - 900, 10.0, True),  # success — excluded
                (_NOW - 600, 100.0, False),  # failure
                (_NOW - 300, 200.0, False),  # failure
            ],
            "fmpfbt_b": [
                (_NOW - 700, 50.0, True),  # success — excluded
                (_NOW - 400, 50.0, True),  # success — excluded
            ],
        }
    )
    mean_a = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_a", store=store, now_ms=_NOW
    )
    mean_b = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(mean_a, float), f"expected float, got {type(mean_a)}"
    assert mean_a == 150.0, (
        f"mean_failure_a=150.0 (100+200)/2; kills mean_b=0/always-0; got {mean_a}"
    )
    assert mean_b == 0.0, f"mean_failure_b=0.0 (no failures); got {mean_b}"


def test_fleet_mean_per_failure_excludes_successes() -> None:
    """Success calls do not affect failure mean."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_excl": [
                (_NOW - 900, 9999.0, True),  # success — should NOT affect mean
                (_NOW - 600, 100.0, False),  # failure
                (_NOW - 300, 200.0, False),  # failure
            ],
        }
    )
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_excl", store=store, now_ms=_NOW
    )
    assert result == 150.0, f"9999ms success excluded; mean=(100+200)/2=150; got {result}"


def test_fleet_mean_per_failure_no_failures_returns_zero() -> None:
    """All calls succeeded → no failures → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_ok": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_ok", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_mean_per_failure_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_other": [(_NOW - 500, 100.0, False)],
        }
    )
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_mean_per_failure_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_mean_per_failure_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_old": [
                (_NOW - _WIN - 200, 100.0, False),
                (_NOW - _WIN - 100, 200.0, False),
            ],
        }
    )
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmpfbt_rt": [
                (_NOW - 400, 80.0, False),  # failure
                (_NOW - 200, 50.0, True),  # success — excluded
            ],
        }
    )
    result = get_windowed_fleet_latency_mean_per_failure_ms_by_tool(
        _WIN, "fmpfbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 80.0
