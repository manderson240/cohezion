"""Item 878: compound_mcp_telemetry + get_tool_telemetry_summary -- MCP per-tool telemetry."""

from __future__ import annotations

from cohezion.compound.mcp_telemetry import compound_mcp_telemetry, get_tool_telemetry_summary


def test_error_rate_not_call_count_primary_discriminator() -> None:
    # 10 calls with 3 errors -> error_rate=0.3 (not 3 or 7)
    store: dict = {}
    for _ in range(7):
        compound_mcp_telemetry("my_tool", 10.0, True, store=store)
    for _ in range(3):
        compound_mcp_telemetry("my_tool", 20.0, False, store=store)
    summary = get_tool_telemetry_summary(store)
    assert abs(summary["my_tool"]["error_rate"] - 0.3) < 1e-9
    assert summary["my_tool"]["call_count"] == 10


def test_zero_error_rate_when_all_success() -> None:
    store: dict = {}
    for _ in range(5):
        compound_mcp_telemetry("tool_a", 15.0, True, store=store)
    summary = get_tool_telemetry_summary(store)
    assert summary["tool_a"]["error_rate"] == 0.0
    assert summary["tool_a"]["call_count"] == 5


def test_error_rate_one_when_all_fail() -> None:
    store: dict = {}
    for _ in range(4):
        compound_mcp_telemetry("tool_b", 50.0, False, store=store)
    summary = get_tool_telemetry_summary(store)
    assert abs(summary["tool_b"]["error_rate"] - 1.0) < 1e-9


def test_p50_latency() -> None:
    # [10, 20, 30, 40, 50]: p50 = median = 30ms
    store: dict = {}
    for ms in [10.0, 20.0, 30.0, 40.0, 50.0]:
        compound_mcp_telemetry("lat_tool", ms, True, store=store)
    summary = get_tool_telemetry_summary(store)
    assert abs(summary["lat_tool"]["p50_ms"] - 30.0) < 1e-9


def test_p95_latency() -> None:
    # 20 values: p95 = value at index floor(0.95*20) = index 19 = 200ms (max when evenly spaced)
    store: dict = {}
    for ms in [float(i * 10) for i in range(1, 21)]:  # 10..200
        compound_mcp_telemetry("p95_tool", ms, True, store=store)
    summary = get_tool_telemetry_summary(store)
    # p95: floor(0.95 * 20) = floor(19) = index 19 -> 200ms
    assert summary["p95_tool"]["p95_ms"] == 200.0


def test_multiple_tools_independent() -> None:
    store: dict = {}
    compound_mcp_telemetry("tool_x", 10.0, True, store=store)
    compound_mcp_telemetry("tool_x", 20.0, False, store=store)
    compound_mcp_telemetry("tool_y", 5.0, True, store=store)
    summary = get_tool_telemetry_summary(store)
    assert summary["tool_x"]["call_count"] == 2
    assert summary["tool_y"]["call_count"] == 1
    assert abs(summary["tool_x"]["error_rate"] - 0.5) < 1e-9
    assert summary["tool_y"]["error_rate"] == 0.0


def test_summary_keyed_by_tool_name() -> None:
    store: dict = {}
    compound_mcp_telemetry("search_tool", 15.0, True, store=store)
    summary = get_tool_telemetry_summary(store)
    assert "search_tool" in summary
    assert set(summary["search_tool"].keys()) >= {"call_count", "error_rate", "p50_ms", "p95_ms"}


def test_empty_store_returns_empty_dict() -> None:
    assert get_tool_telemetry_summary({}) == {}


def test_single_call_p50_equals_that_latency() -> None:
    store: dict = {}
    compound_mcp_telemetry("solo", 42.0, True, store=store)
    summary = get_tool_telemetry_summary(store)
    assert summary["solo"]["p50_ms"] == 42.0
    assert summary["solo"]["p95_ms"] == 42.0


def test_default_store_isolates_calls() -> None:
    # Using separate explicit stores — no cross-test pollution
    s1: dict = {}
    s2: dict = {}
    compound_mcp_telemetry("t", 5.0, True, store=s1)
    compound_mcp_telemetry("t", 100.0, False, store=s2)
    assert get_tool_telemetry_summary(s1)["t"]["call_count"] == 1
    assert get_tool_telemetry_summary(s2)["t"]["call_count"] == 1
    assert get_tool_telemetry_summary(s1)["t"]["error_rate"] == 0.0
    assert get_tool_telemetry_summary(s2)["t"]["error_rate"] == 1.0
