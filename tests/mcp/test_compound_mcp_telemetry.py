"""Item 878: MCP connector telemetry matching Claude directory format."""

from __future__ import annotations


def _fresh_telemetry():
    """Import and reset telemetry for test isolation."""
    from cohezion.mcp import compound_mcp_telemetry as mod

    mod._TELEMETRY.clear()
    return mod


def test_error_rate_ten_calls_three_errors() -> None:
    """FALSIFIABLE: 10 calls, 3 errors -> error_rate=0.3."""
    mod = _fresh_telemetry()
    for i in range(7):
        mod.record_tool_call("my_tool", latency_ms=10.0, success=True)
    for i in range(3):
        mod.record_tool_call("my_tool", latency_ms=15.0, success=False)
    summary = mod.get_tool_telemetry_summary()
    assert "my_tool" in summary
    assert summary["my_tool"]["call_count"] == 10
    assert abs(summary["my_tool"]["error_rate"] - 0.3) < 1e-9


def test_call_count_accumulates() -> None:
    mod = _fresh_telemetry()
    mod.record_tool_call("t1", latency_ms=5.0, success=True)
    mod.record_tool_call("t1", latency_ms=5.0, success=True)
    mod.record_tool_call("t1", latency_ms=5.0, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert summary["t1"]["call_count"] == 3


def test_zero_errors_gives_zero_rate() -> None:
    mod = _fresh_telemetry()
    for _ in range(5):
        mod.record_tool_call("t2", latency_ms=8.0, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert summary["t2"]["error_rate"] == 0.0


def test_all_errors_gives_rate_one() -> None:
    mod = _fresh_telemetry()
    for _ in range(4):
        mod.record_tool_call("t3", latency_ms=20.0, success=False)
    summary = mod.get_tool_telemetry_summary()
    assert abs(summary["t3"]["error_rate"] - 1.0) < 1e-9


def test_p50_p95_present_in_summary() -> None:
    mod = _fresh_telemetry()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    for lat in latencies:
        mod.record_tool_call("t4", latency_ms=lat, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert "p50_ms" in summary["t4"]
    assert "p95_ms" in summary["t4"]
    # p50 of [10..100] sorted = 55.0 (avg of 50 and 60)
    assert summary["t4"]["p50_ms"] == 55.0


def test_multiple_tools_independent() -> None:
    mod = _fresh_telemetry()
    mod.record_tool_call("ta", latency_ms=5.0, success=True)
    mod.record_tool_call("tb", latency_ms=15.0, success=False)
    summary = mod.get_tool_telemetry_summary()
    assert summary["ta"]["call_count"] == 1
    assert summary["tb"]["call_count"] == 1
    assert summary["ta"]["error_rate"] == 0.0
    assert summary["tb"]["error_rate"] == 1.0


def test_empty_returns_empty_dict() -> None:
    mod = _fresh_telemetry()
    summary = mod.get_tool_telemetry_summary()
    assert summary == {}


def test_p95_single_call() -> None:
    mod = _fresh_telemetry()
    mod.record_tool_call("t5", latency_ms=42.0, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert summary["t5"]["p95_ms"] == 42.0
    assert summary["t5"]["p50_ms"] == 42.0


def test_summary_keyed_by_tool_name() -> None:
    mod = _fresh_telemetry()
    mod.record_tool_call("search", latency_ms=7.0, success=True)
    mod.record_tool_call("create", latency_ms=9.0, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert "search" in summary
    assert "create" in summary


def test_p95_higher_than_p50() -> None:
    mod = _fresh_telemetry()
    # 5 low + 1 high outlier -> p95 should be the outlier
    for _ in range(5):
        mod.record_tool_call("t6", latency_ms=10.0, success=True)
    mod.record_tool_call("t6", latency_ms=1000.0, success=True)
    summary = mod.get_tool_telemetry_summary()
    assert summary["t6"]["p95_ms"] >= summary["t6"]["p50_ms"]
