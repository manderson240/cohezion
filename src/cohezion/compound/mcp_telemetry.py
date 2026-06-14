"""MCP per-tool call telemetry.  Item 878.

Pure in-memory counter functions matching the Claude connector directory
observability format: call_count, error_rate, p50_ms, p95_ms per tool.
No DB writes; no I/O; thread-safety NOT guaranteed (single-process assumption).

## FUTURE HOOKS
- Wire into compound-mcp request/response middleware for automatic capture
- Add rolling-window time-series (current store is cumulative only)
- Expose via /health endpoint for Claude directory dashboard
- Persist to SurrealDB for cross-session telemetry aggregation
"""

from __future__ import annotations

import math


def compound_mcp_telemetry(
    tool_name: str,
    latency_ms: float,
    success: bool,
    *,
    store: dict,
) -> None:
    """Record a single tool call into *store*.

    Args:
        tool_name:  Name of the MCP tool that was called.
        latency_ms: Wall-clock latency for this call in milliseconds.
        success:    True if the call succeeded; False on error.
        store:      Mutable dict acting as the in-memory telemetry store.
                    Pass an explicit ``{}`` per test to avoid cross-test
                    pollution.  In production, pass a module-level dict.
    """
    if tool_name not in store:
        store[tool_name] = {"latencies": [], "errors": 0}
    store[tool_name]["latencies"].append(latency_ms)
    if not success:
        store[tool_name]["errors"] += 1


def get_tool_telemetry_summary(store: dict) -> dict[str, dict]:
    """Return aggregated telemetry summary from *store*.

    Returns ``{tool_name: {call_count, error_rate, p50_ms, p95_ms}}``.
    Empty store -> {}.

    Percentile formula: ``sorted_latencies[floor(p/100 * n)]`` (index-based,
    no interpolation) — consistent with ``numpy.percentile`` method='lower'
    for single-list inputs.
    """
    if not store:
        return {}
    result: dict[str, dict] = {}
    for tool, data in store.items():
        latencies = sorted(data["latencies"])
        n = len(latencies)
        if n == 0:
            continue
        errors = data["errors"]
        error_rate = errors / n
        p50_ms = latencies[math.floor(0.50 * n)]
        p95_ms = latencies[math.floor(0.95 * n)]
        result[tool] = {
            "call_count": n,
            "error_rate": error_rate,
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
        }
    return result
