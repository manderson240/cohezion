"""Item 1208: get_windowed_fleet_latency_failure_success_ratio_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool ratio of failure mean latency to success mean latency within window.
Returns float. 0.0 for no failures or success mean == 0.0.
Formula: mean_failure / mean_success.

PRIMARY DISC.:
  tool_a: [(10ms,ok=T),(20ms,ok=T),(100ms,ok=F),(200ms,ok=F)]
    → mean_success=15.0, mean_failure=150.0 → ratio=10.0
  tool_b: [(50ms,ok=T),(50ms,ok=T)] → mean_failure=0.0 → ratio=0.0
  ratio_a=10.0 kills ratio_b=0.0; kills always-0; kills always-1.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_failure_success_ratio_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_failure_success_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio_a=10.0 kills ratio_b=0.0; kills always-0; kills always-1."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_a": [
                (_NOW - 900, 10.0, True),  # success
                (_NOW - 700, 20.0, True),  # success
                (_NOW - 500, 100.0, False),  # failure
                (_NOW - 300, 200.0, False),  # failure
            ],
            "ffsrbt_b": [
                (_NOW - 700, 50.0, True),  # success
                (_NOW - 400, 50.0, True),  # success — no failures
            ],
        }
    )
    ratio_a = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_a", store=store, now_ms=_NOW
    )
    ratio_b = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(ratio_a, float), f"expected float, got {type(ratio_a)}"
    assert ratio_a == 10.0, (
        f"ratio_a=(150.0/15.0)=10.0; kills ratio_b=0/always-0/always-1; got {ratio_a}"
    )
    assert ratio_b == 0.0, f"ratio_b=0.0 (no failures); got {ratio_b}"


def test_fleet_failure_success_ratio_greater_than_one() -> None:
    """Failures slower than successes → ratio > 1.0."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_gt": [
                (_NOW - 800, 10.0, True),  # success
                (_NOW - 600, 200.0, False),  # failure — slower
            ],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_gt", store=store, now_ms=_NOW
    )
    assert result == 20.0, f"200/10=20.0; got {result}"
    assert result > 1.0


def test_fleet_failure_success_ratio_less_than_one() -> None:
    """Failures faster than successes (fast-fail) → ratio < 1.0."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_lt": [
                (_NOW - 800, 100.0, True),  # success — slow
                (_NOW - 600, 5.0, False),  # failure — fast-fail
            ],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_lt", store=store, now_ms=_NOW
    )
    assert result == 0.05, f"5/100=0.05; got {result}"
    assert result < 1.0


def test_fleet_failure_success_ratio_no_failures_returns_zero() -> None:
    """All calls succeeded → no failures → 0.0."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_ok": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_ok", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_failure_success_ratio_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_other": [(_NOW - 500, 100.0, False)],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_failure_success_ratio_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_failure_success_ratio_no_successes_returns_zero() -> None:
    """No successful calls (success mean = 0) → 0.0 (avoid division by zero)."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_no_succ": [
                (_NOW - 600, 100.0, False),  # failure only
                (_NOW - 300, 200.0, False),  # failure only
            ],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_no_succ", store=store, now_ms=_NOW
    )
    # No successes → mean_success=0.0 → can't divide → return 0.0
    assert result == 0.0
    assert isinstance(result, float)


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "ffsrbt_rt": [
                (_NOW - 600, 50.0, True),  # success
                (_NOW - 300, 100.0, False),  # failure
            ],
        }
    )
    result = get_windowed_fleet_latency_failure_success_ratio_by_tool(
        _WIN, "ffsrbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 2.0  # 100/50 = 2.0
