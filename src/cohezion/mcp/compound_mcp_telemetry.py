"""MCP connector telemetry — item 878.

Tracks per-tool call count, error rate, and latency percentiles (p50/p95)
in the format expected by the Claude connector directory observability dashboard
(https://claude.com/blog/observability-for-developers-building-connectors).

Pure in-memory store (no DB write).  Thread-safe via GIL for CPython.
Reset _TELEMETRY.clear() for test isolation.
"""
from __future__ import annotations

_TELEMETRY: dict[str, dict] = {}


def record_tool_call(tool_name: str, latency_ms: float, success: bool) -> None:
    """Record one tool call observation.  Item 878.

    Args:
        tool_name: The MCP tool name (e.g. "search_files", "read_file").
        latency_ms: End-to-end latency in milliseconds.
        success: True if the call succeeded; False on error.
    """
    if tool_name not in _TELEMETRY:
        _TELEMETRY[tool_name] = {
            "call_count": 0,
            "error_count": 0,
            "latencies": [],
        }
    stats = _TELEMETRY[tool_name]
    stats["call_count"] += 1
    if not success:
        stats["error_count"] += 1
    stats["latencies"].append(latency_ms)


def _percentile(sorted_values: list[float], p: float) -> float:
    """Return the p-th percentile (0-100) using nearest-rank method."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    # Interpolating: index = (p/100) * (n-1)
    idx = (p / 100.0) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_values[-1]
    frac = idx - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def get_tool_telemetry_summary() -> dict[str, dict]:
    """Return per-tool telemetry summary.  Item 878.

    Returns:
        {tool_name: {call_count, error_rate, p50_ms, p95_ms}}
        Empty dict when no calls recorded.
    """
    result: dict[str, dict] = {}
    for tool_name, stats in _TELEMETRY.items():
        n = stats["call_count"]
        if n == 0:
            continue
        sorted_lats = sorted(stats["latencies"])
        result[tool_name] = {
            "call_count": n,
            "error_rate": stats["error_count"] / n,
            "p50_ms": _percentile(sorted_lats, 50.0),
            "p95_ms": _percentile(sorted_lats, 95.0),
        }
    return result
