"""MCP connector telemetry — items 878, 882/885.

Tracks per-tool call count, error rate, and latency percentiles (p50/p95)
in the format expected by the Claude connector directory observability dashboard
(https://claude.com/blog/observability-for-developers-building-connectors).

Cumulative store (_TELEMETRY) for all-time metrics.
Windowed store (_WINDOWED_TELEMETRY) for time-window metrics (spike detection).

Pure in-memory stores (no DB write).  Thread-safe via GIL for CPython.
Reset store.clear() for test isolation.
"""

from __future__ import annotations

import json as _json
import time as _time
from pathlib import Path as _Path


_TELEMETRY: dict[str, dict] = {}
# Windowed store: {tool_name: [(ts_ms, latency_ms, success), ...]}
_WINDOWED_TELEMETRY: dict[str, list] = {}


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


def get_tool_call_count(tool_name: str) -> int:
    """Return the cumulative call count for a specific tool.  Item 911.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Total number of calls recorded for *tool_name*.
        Returns 0 for tools with no recorded calls (never raises KeyError).
    """
    return _TELEMETRY.get(tool_name, {}).get("call_count", 0)


def get_tool_error_count(tool_name: str) -> int:
    """Return the cumulative error count for a specific tool.  Item 912.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Total number of failed calls recorded for *tool_name*.
        Returns 0 for tools with no recorded calls or zero errors (never raises KeyError).
    """
    return _TELEMETRY.get(tool_name, {}).get("error_count", 0)


def get_tool_error_rate(tool_name: str) -> float:
    """Return the cumulative error rate for a specific tool.  Item 913.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        error_count / call_count for *tool_name*, as a float in [0.0, 1.0].
        Returns 0.0 for unknown tools or tools with no calls (never raises).
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or stats["call_count"] == 0:
        return 0.0
    return float(stats["error_count"]) / stats["call_count"]


def get_tool_p50_ms(tool_name: str) -> float:
    """Return the p50 (median) latency for a specific tool.  Item 914.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        p50 latency in milliseconds from the cumulative store.
        Returns 0.0 for unknown tools or tools with no recorded calls.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or not stats["latencies"]:
        return 0.0
    return _percentile(sorted(stats["latencies"]), 50.0)


def get_tool_p95_ms(tool_name: str) -> float:
    """Return the p95 latency for a specific tool.  Item 915.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        p95 latency in milliseconds from the cumulative store.
        Returns 0.0 for unknown tools or tools with no recorded calls.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or not stats["latencies"]:
        return 0.0
    return _percentile(sorted(stats["latencies"]), 95.0)


def get_tool_stats(tool_name: str) -> dict:
    """Return a unified per-tool profile dict.  Item 916.

    Composes the five individual accessors into a single dict, eliminating
    5-call boilerplate for callers wanting the full per-tool profile.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        {call_count, error_count, error_rate, p50_ms, p95_ms} — all zeros for
        unknown tools (never raises KeyError).
    """
    return {
        "call_count": get_tool_call_count(tool_name),
        "error_count": get_tool_error_count(tool_name),
        "error_rate": get_tool_error_rate(tool_name),
        "p50_ms": get_tool_p50_ms(tool_name),
        "p95_ms": get_tool_p95_ms(tool_name),
    }


def get_all_tool_stats() -> dict[str, dict]:
    """Return a per-tool stats map for every tool in the cumulative store.  Item 917.

    Returns:
        {tool_name: get_tool_stats(tool_name)} for every tool recorded.
        Empty dict when no tools have been recorded.
    """
    return {tool_name: get_tool_stats(tool_name) for tool_name in _TELEMETRY}


def get_top_n_tools_by_call_count(n: int) -> list[str]:
    """Return up to N tool names sorted by descending call count.  Item 918.

    Ties in call count are broken by ascending tool name (alphabetical) for
    deterministic results.

    Args:
        n: Number of top tools to return.  n ≤ 0 returns [].

    Returns:
        List of up to *n* tool names, busiest first.
        Empty list when store is empty or *n* ≤ 0.
    """
    if n <= 0:
        return []
    sorted_tools = sorted(
        _TELEMETRY.keys(),
        key=lambda t: (-_TELEMETRY[t]["call_count"], t),
    )
    return sorted_tools[:n]


def get_top_n_tools_by_error_rate(n: int) -> list[str]:
    """Return up to N tool names sorted by descending error rate.  Item 919.

    Only tools that have been called at least once are included (error rate is
    only defined when call_count > 0).  Ties broken by ascending tool name.

    Args:
        n: Number of top error-prone tools to return.  n ≤ 0 returns [].

    Returns:
        List of up to *n* tool names, most error-prone first.
        Empty list when store is empty or *n* ≤ 0.
    """
    if n <= 0:
        return []
    eligible = [t for t, stats in _TELEMETRY.items() if stats["call_count"] > 0]
    sorted_tools = sorted(
        eligible,
        key=lambda t: (-get_tool_error_rate(t), t),
    )
    return sorted_tools[:n]


def get_top_n_tools_by_p95_ms(n: int) -> list[str]:
    """Return up to N tool names sorted by descending p95 latency.  Item 920.

    Closes the top-N ranking trio (call_count + error_rate + p95).
    Ties broken by ascending tool name (deterministic).

    Args:
        n: Number of top high-latency tools to return.  n ≤ 0 returns [].

    Returns:
        List of up to *n* tool names, highest-p95 first.
        Empty list when store is empty or *n* ≤ 0.
    """
    if n <= 0:
        return []
    sorted_tools = sorted(
        _TELEMETRY.keys(),
        key=lambda t: (-get_tool_p95_ms(t), t),
    )
    return sorted_tools[:n]


def get_tool_windowed_stats(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> dict:
    """Return windowed per-tool stats for a specific tool.  Item 921.

    Windowed complement of ``get_tool_stats`` — queries ``_WINDOWED_TELEMETRY``
    rather than the cumulative ``_TELEMETRY`` store.

    Args:
        tool_name:  The MCP tool name to look up.
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store to query (injectable for test isolation;
                    defaults to ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        {call_count, error_rate, p50_ms, p95_ms} for calls in the last *window_ms* ms.
        All-zero dict (call_count=0, error_rate=0.0, p50_ms=0.0, p95_ms=0.0) when
        the tool is unknown or has no calls in the window.
        Note: no ``error_count`` key — matches ``get_windowed_summary`` schema.
    """
    _zero: dict = {"call_count": 0, "error_rate": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    records = store.get(tool_name)
    if not records:
        return _zero
    cutoff_ms = now_ms - window_ms
    recent = [(lat, ok) for ts, lat, ok in records if ts >= cutoff_ms]
    if not recent:
        return _zero
    n = len(recent)
    errors = sum(1 for _, ok in recent if not ok)
    sorted_lats = sorted(lat for lat, _ in recent)
    return {
        "call_count": n,
        "error_rate": float(errors) / n,
        "p50_ms": _percentile(sorted_lats, 50.0),
        "p95_ms": _percentile(sorted_lats, 95.0),
    }


def get_tool_windowed_p95_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the windowed p95 latency for a specific tool.  Item 922.

    Lightweight shortcut for monitoring/alerting that avoids constructing the
    full windowed stats dict when only p95 is needed.

    Args:
        tool_name:  The MCP tool name to look up.
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        p95 latency in milliseconds from the windowed store.
        0.0 for unknown tools or tools with no calls in the window.
    """
    return get_tool_windowed_stats(tool_name, window_ms, store=store, now_ms=now_ms)["p95_ms"]


def get_tool_windowed_error_rate(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the windowed error rate for a specific tool.  Item 923.

    Single-metric shortcut mirroring ``get_tool_windowed_p95_ms`` (item 922)
    for the error-rate axis.

    Args:
        tool_name:  The MCP tool name to look up.
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Error rate (0.0–1.0) from the windowed store.
        0.0 for unknown tools or tools with no calls in the window.
    """
    return get_tool_windowed_stats(tool_name, window_ms, store=store, now_ms=now_ms)["error_rate"]


def get_tool_windowed_call_count(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the windowed call count for a specific tool.  Item 924.

    Completes the windowed fast-path trio: p95 (922) + error_rate (923) + call_count (924).

    Args:
        tool_name:  The MCP tool name to look up.
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Integer count of calls in the last *window_ms* ms.
        0 for unknown tools or tools with no calls in the window.
    """
    return int(
        get_tool_windowed_stats(tool_name, window_ms, store=store, now_ms=now_ms)["call_count"]
    )


def get_all_tool_windowed_stats(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> dict[str, dict]:
    """Return windowed stats for all tools that have calls within the window.  Item 925.

    Windowed complement of ``get_all_tool_stats`` — only tools with ≥1 call
    in the last *window_ms* ms appear in the result.

    Args:
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        {tool_name: {call_count, error_rate, p50_ms, p95_ms}} for active tools only.
        Empty dict when store is empty or no tool has calls within the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    result: dict[str, dict] = {}
    for tool_name in store:
        stats = get_tool_windowed_stats(tool_name, window_ms, store=store, now_ms=now_ms)
        if stats["call_count"] > 0:
            result[tool_name] = stats
    return result


def get_tool_windowed_p50_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the windowed p50 latency for a specific tool.  Item 927.

    Windowed complement of ``get_tool_p50_ms`` (item 914).
    Mirrors ``get_tool_windowed_p95_ms`` (item 922) for the p50 axis.

    Args:
        tool_name:  The MCP tool name to look up.
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        p50 latency in milliseconds from the windowed store.
        0.0 for unknown tools or tools with no calls in the window.
    """
    return get_tool_windowed_stats(tool_name, window_ms, store=store, now_ms=now_ms)["p50_ms"]


def get_windowed_tool_names(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> list[str]:
    """Return sorted list of tool names active within the window.  Item 928.

    Enables dashboards to discover which tools are currently active without
    constructing the full stats dict.

    Args:
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Alphabetically sorted list of tool names that have ≥1 call in the window.
        Empty list when store is empty or no tool has calls in the window.
    """
    active = get_all_tool_windowed_stats(window_ms, store=store, now_ms=now_ms)
    return sorted(active.keys())


def get_windowed_tool_count(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> int:
    """Return count of distinct tools active within the window.  Item 931.

    Windowed complement of :func:`get_tool_count` — only tools with ≥1 call
    within the last *window_ms* milliseconds are counted.

    Args:
        window_ms:  Look-back window in milliseconds.
        store:      Windowed telemetry store (injectable; defaults to
                    ``_WINDOWED_TELEMETRY``).
        now_ms:     Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Number of distinct tool names active in the window; 0 when none.
    """
    return len(get_windowed_tool_names(window_ms, store=store, now_ms=now_ms))


def record_tool_call_windowed(
    tool_name: str,
    latency_ms: float,
    success: bool,
    ts_ms: float | None = None,
) -> None:
    """Record one tool call with a timestamp for windowed analysis.  Item 882/885.

    Args:
        tool_name: The MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        success: True if the call succeeded; False on error.
        ts_ms: Timestamp in milliseconds since epoch.  Defaults to now.
    """
    if ts_ms is None:
        ts_ms = _time.time() * 1000.0
    if tool_name not in _WINDOWED_TELEMETRY:
        _WINDOWED_TELEMETRY[tool_name] = []
    _WINDOWED_TELEMETRY[tool_name].append((ts_ms, latency_ms, success))


def record_tool_call_all(
    tool_name: str,
    latency_ms: float,
    success: bool,
    *,
    ts_ms: float | None = None,
) -> None:
    """Record one tool call in BOTH the cumulative and windowed stores.  Item 909.

    Convenience wrapper that calls ``record_tool_call`` and
    ``record_tool_call_windowed`` together, eliminating dual-call boilerplate
    for callers that want both stores populated.

    Args:
        tool_name:  The MCP tool name.
        latency_ms: End-to-end latency in milliseconds.
        success:    True if the call succeeded; False on error.
        ts_ms:      Timestamp in ms for the windowed record.  Defaults to now.
    """
    record_tool_call(tool_name, latency_ms, success)
    record_tool_call_windowed(tool_name, latency_ms, success, ts_ms=ts_ms)


#: Alias for :func:`record_tool_call_all` with a name that makes the
#: windowed-store intent explicit.  Item 926.
record_tool_call_all_windowed = record_tool_call_all


def clear_telemetry_stores() -> None:
    """Reset both in-memory telemetry stores to empty.  Item 910.

    Idempotent: calling on already-empty stores is a no-op.
    Useful for test isolation and operator resets.
    Does NOT affect custom dicts passed as the ``store`` parameter
    to injectable functions.
    """
    _TELEMETRY.clear()
    _WINDOWED_TELEMETRY.clear()


def get_windowed_summary(
    store: dict[str, list],
    window_ms: float,
    now_ms: float | None = None,
) -> dict[str, dict]:
    """Return per-tool summary for calls within the last window_ms ms.  Item 882/885.

    Args:
        store: The _WINDOWED_TELEMETRY dict (injectable for test isolation).
        window_ms: Look-back window in milliseconds.
        now_ms: Current time in ms (defaults to time.time()*1000).

    Returns:
        {tool_name: {call_count, error_rate, p50_ms, p95_ms}}
        Tools with no calls in window are excluded.  Empty dict if none.
    """
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    result: dict[str, dict] = {}
    for tool_name, records in store.items():
        recent = [(lat, ok) for ts, lat, ok in records if ts >= cutoff_ms]
        if not recent:
            continue
        n = len(recent)
        errors = sum(1 for _, ok in recent if not ok)
        sorted_lats = sorted(lat for lat, _ in recent)
        result[tool_name] = {
            "call_count": n,
            "error_rate": float(errors) / n,
            "p50_ms": _percentile(sorted_lats, 50.0),
            "p95_ms": _percentile(sorted_lats, 95.0),
        }
    return result


def detect_latency_spike(
    store: dict[str, list],
    window_ms: float,
    baseline_window_ms: float,
    *,
    now_ms: float | None = None,
    spike_ratio_threshold: float = 2.0,
) -> dict[str, bool]:
    """Detect per-tool p95 latency spikes vs a baseline window.  Item 903.

    Compares the p95 latency of the most-recent ``window_ms`` milliseconds
    against the p95 of the preceding ``baseline_window_ms`` milliseconds.
    A spike is declared when ``recent_p95 / baseline_p95 > spike_ratio_threshold``.

    Args:
        store:                   The _WINDOWED_TELEMETRY dict (injectable for tests).
        window_ms:               Recent look-back window length in ms.
        baseline_window_ms:      Historical baseline window length in ms (must cover
                                 older period: [now - window_ms - baseline_window_ms,
                                 now - window_ms]).
        now_ms:                  Current timestamp in ms (defaults to time.time()*1000).
        spike_ratio_threshold:   Ratio strictly above which a spike is declared (default 2.0).

    Returns:
        {tool_name: bool} — True = spike detected.  Tools with no recent calls
        OR no baseline calls are excluded (can't compute ratio).  Empty when store is
        empty or no tool has both recent and baseline calls.
    """
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    recent_cutoff = now_ms - window_ms
    baseline_cutoff = recent_cutoff - baseline_window_ms

    result: dict[str, bool] = {}
    for tool_name, records in store.items():
        recent_lats = sorted(lat for ts, lat, _ok in records if ts >= recent_cutoff)
        baseline_lats = sorted(
            lat for ts, lat, _ok in records if baseline_cutoff <= ts < recent_cutoff
        )
        if not recent_lats or not baseline_lats:
            continue
        recent_p95 = _percentile(recent_lats, 95.0)
        baseline_p95 = _percentile(baseline_lats, 95.0)
        if baseline_p95 == 0.0:
            continue  # can't compute ratio; exclude tool
        ratio = recent_p95 / baseline_p95
        result[tool_name] = ratio > spike_ratio_threshold
    return result


def detect_error_spike(
    store: dict[str, list],
    window_ms: float,
    baseline_window_ms: float,
    *,
    now_ms: float | None = None,
    delta_threshold: float = 0.2,
) -> dict[str, bool]:
    """Per-tool error-rate spike flag via absolute rate delta.  Item 904.

    Compares the error rate in the recent ``window_ms`` milliseconds against the
    error rate in the preceding ``baseline_window_ms`` milliseconds.  A spike is
    declared when ``recent_error_rate - baseline_error_rate > delta_threshold``.

    Recent window:   [now - window_ms, now]
    Baseline window: [now - window_ms - baseline_window_ms, now - window_ms)

    Tools with no recent OR no baseline calls are excluded from the result.

    Args:
        store:           The _WINDOWED_TELEMETRY dict (injectable for tests).
        window_ms:       Recent look-back window in ms.
        baseline_window_ms: Older baseline window length in ms.
        now_ms:          Current time in ms (defaults to time.time()*1000).
        delta_threshold: Absolute error-rate increase above which spike fires (default 0.2).

    Returns:
        {tool_name: bool} — True = spike detected.  Empty dict when no data.
    """
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    recent_cutoff = now_ms - window_ms
    baseline_cutoff = recent_cutoff - baseline_window_ms

    result: dict[str, bool] = {}
    for tool_name, records in store.items():
        recent = [(ok,) for ts, _lat, ok in records if ts >= recent_cutoff]
        baseline = [(ok,) for ts, _lat, ok in records if baseline_cutoff <= ts < recent_cutoff]
        if not recent or not baseline:
            continue
        recent_err = sum(1 for (ok,) in recent if not ok) / len(recent)
        baseline_err = sum(1 for (ok,) in baseline if not ok) / len(baseline)
        result[tool_name] = (recent_err - baseline_err) > delta_threshold
    return result


def get_telemetry_health_snapshot(
    store: dict[str, list],
    window_ms: float,
    baseline_window_ms: float,
    *,
    now_ms: float | None = None,
) -> dict[str, dict]:
    """Unified per-tool health snapshot.  Item 905.

    Aggregates detect_latency_spike, detect_error_spike, and get_windowed_summary
    into a single per-tool dict:
        {tool_name: {latency_spike, error_spike, recent_p95, recent_error_rate}}

    Only tools with recent calls (in [now-window_ms, now]) are included.
    Tools with no baseline data have latency_spike=False, error_spike=False
    (cannot compute ratio/delta; conservative default is no spike rather than
    excluding the tool from observability).

    Args:
        store:               _WINDOWED_TELEMETRY dict (injectable for test isolation).
        window_ms:           Recent look-back window in ms.
        baseline_window_ms:  Older baseline window in ms.
        now_ms:              Current time in ms (defaults to time.time()*1000).

    Returns:
        {tool_name: {latency_spike: bool, error_spike: bool,
                     recent_p95: float, recent_error_rate: float}}
        Empty dict when no recent calls in store.
    """
    if now_ms is None:
        now_ms = _time.time() * 1000.0

    # Windowed summary anchors which tools appear (tools with recent data only)
    summary = get_windowed_summary(store, window_ms, now_ms=now_ms)
    if not summary:
        return {}

    # Spike dicts exclude tools with no baseline — default to False for those
    lat_spikes = detect_latency_spike(store, window_ms, baseline_window_ms, now_ms=now_ms)
    err_spikes = detect_error_spike(store, window_ms, baseline_window_ms, now_ms=now_ms)

    result: dict[str, dict] = {}
    for tool_name, stats in summary.items():
        result[tool_name] = {
            "latency_spike": bool(lat_spikes.get(tool_name, False)),
            "error_spike": bool(err_spikes.get(tool_name, False)),
            "recent_p95": float(stats["p95_ms"]),
            "recent_error_rate": float(stats["error_rate"]),
        }
    return result


def persist_telemetry_snapshot(path: _Path | str) -> None:
    """Write the cumulative telemetry summary to disk as JSON.  Item 907.

    Atomic write: data is written to a temporary file beside the destination,
    then renamed into place so readers never see a partial file.

    Args:
        path: Destination file path (``pathlib.Path`` or ``str``).
              Parent directory must exist.
    """
    dest = _Path(path)
    summary = get_tool_telemetry_summary()
    payload = _json.dumps(summary, indent=2)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.rename(dest)


def load_telemetry_snapshot(path: _Path | str) -> dict[str, dict]:
    """Read a persisted telemetry snapshot back from disk.  Item 908.

    Inverse of ``persist_telemetry_snapshot``.  Does NOT mutate ``_TELEMETRY``.

    Args:
        path: Path to the JSON file written by ``persist_telemetry_snapshot``.

    Returns:
        {tool_name: {call_count, error_rate, p50_ms, p95_ms}} — same shape as
        ``get_tool_telemetry_summary()``.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file contents are not valid JSON.
    """
    src = _Path(path)
    if not src.exists():
        raise FileNotFoundError(f"Telemetry snapshot not found: {src}")
    text = src.read_text(encoding="utf-8")
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError as exc:
        raise ValueError(f"Malformed telemetry snapshot at {src}: {exc}") from exc
    return data


def get_tool_telemetry_full(tool_name: str) -> dict:
    """Return a complete per-tool profile dict with 8 keys.  Item 949.

    Extends :func:`get_tool_stats` (5 keys) with ``min_ms``, ``max_ms``, and
    ``success_rate``.  Unknown tools return a safe all-zero dict except
    ``success_rate`` which defaults to ``1.0`` (no failures observed).

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Dict with exactly 8 keys:
        ``{call_count, error_count, error_rate, success_rate,
           p50_ms, p95_ms, min_ms, max_ms}``.
    """
    return {
        "call_count": get_tool_call_count(tool_name),
        "error_count": get_tool_error_count(tool_name),
        "error_rate": get_tool_error_rate(tool_name),
        "success_rate": get_tool_success_rate(tool_name),
        "p50_ms": get_tool_p50_ms(tool_name),
        "p95_ms": get_tool_p95_ms(tool_name),
        "min_ms": get_tool_min_latency_ms(tool_name),
        "max_ms": get_tool_max_latency_ms(tool_name),
    }


def get_global_mean_latency_ms() -> float:
    """Return the mean latency over all tools combined (weighted).  Item 948.

    Computed as ``total_latency_sum / total_call_count`` (pooled / weighted) —
    NOT the average of per-tool means.  When tool call counts differ, pooling
    gives the correct aggregate; naive averaging over-weights low-traffic tools.

    Returns:
        Arithmetic mean latency in milliseconds; 0.0 when no calls recorded.
    """
    total_calls = sum(stats["call_count"] for stats in _TELEMETRY.values())
    if total_calls == 0:
        return 0.0
    total_lat = sum(sum(stats["latencies"]) for stats in _TELEMETRY.values())
    return float(total_lat) / total_calls


def get_global_p50_ms() -> float:
    """Return the p50 (median) latency over all tools combined (pooled).  Item 947.

    Pools all latency records from every tool and computes p50 on the combined
    list.  This gives the correct aggregate median — averaging per-tool p50
    values would over-weight low-traffic tools.

    Returns:
        p50 latency in milliseconds; 0.0 when no calls have been recorded.
    """
    all_lats: list[float] = []
    for stats in _TELEMETRY.values():
        all_lats.extend(stats["latencies"])
    if not all_lats:
        return 0.0
    return _percentile(sorted(all_lats), 50.0)


def get_global_p95_ms() -> float:
    """Return the p95 latency over all tools combined (pooled).  Item 946.

    Pools / concatenates all latency records from every tool in ``_TELEMETRY``
    and computes p95 on the combined list.  This is the correct aggregate —
    averaging per-tool p95 values would over-weight low-traffic tools.

    Returns:
        p95 latency in milliseconds; 0.0 when no calls have been recorded.
    """
    all_lats: list[float] = []
    for stats in _TELEMETRY.values():
        all_lats.extend(stats["latencies"])
    if not all_lats:
        return 0.0
    return _percentile(sorted(all_lats), 95.0)


def get_global_error_rate() -> float:
    """Return the overall error rate across all tools.  Item 945.

    Computed as ``total_error_count / total_call_count`` (pooled / weighted
    average) — NOT the average of per-tool error rates.  When tool call counts
    differ, pooling gives the correct aggregate; naive averaging over-weights
    low-traffic tools.

    Returns:
        Global error rate in [0.0, 1.0]; 0.0 when no calls have been recorded.
    """
    total_calls = sum(stats["call_count"] for stats in _TELEMETRY.values())
    if total_calls == 0:
        return 0.0
    total_errors = sum(stats["error_count"] for stats in _TELEMETRY.values())
    return float(total_errors) / total_calls


def get_total_error_count() -> int:
    """Return the total number of errors recorded across all tools.  Item 944.

    Sum of ``error_count`` for every tool in ``_TELEMETRY``.

    Returns:
        Total failed calls across all tools; 0 when none recorded.
    """
    return sum(stats["error_count"] for stats in _TELEMETRY.values())


def get_total_call_count() -> int:
    """Return the total number of calls recorded across all tools.  Item 943.

    Sum of ``call_count`` for every tool in ``_TELEMETRY``.  Distinct from
    :func:`get_tool_count` (which counts distinct tools, not total calls).

    Returns:
        Total calls across all tools; 0 when no calls have been recorded.
    """
    return sum(stats["call_count"] for stats in _TELEMETRY.values())


def get_busiest_tool() -> str | None:
    """Return the name of the tool with the most recorded calls.  Item 942.

    Enables dashboards to identify the highest-traffic tool at a glance.
    Ties in call count are broken alphabetically (ascending).

    Returns:
        Tool name with the highest call count; ``None`` when store is empty.
    """
    if not _TELEMETRY:
        return None
    max_count = max(get_tool_call_count(t) for t in _TELEMETRY)
    candidates = [
        t for t in _TELEMETRY
        if get_tool_call_count(t) == max_count
    ]
    return min(candidates)  # alphabetically first among count-tied tools


def get_fastest_tool() -> str | None:
    """Return the name of the tool with the lowest p50 latency.  Item 941.

    Enables dashboards to show which tool responds fastest (lowest median
    latency). Ties in p50 are broken alphabetically (ascending).

    Returns:
        Tool name with the lowest p50 latency; ``None`` when store is empty.
    """
    if not _TELEMETRY:
        return None
    min_p50 = min(get_tool_p50_ms(t) for t in _TELEMETRY)
    candidates = [
        t for t in _TELEMETRY
        if abs(get_tool_p50_ms(t) - min_p50) < 1e-9
    ]
    return min(candidates)  # alphabetically first among p50-tied tools


def get_most_error_prone_tool() -> str | None:
    """Return the name of the tool with the highest error rate.  Item 940.

    Enables dashboards to surface the tool most at risk of reliability issues.
    Ties in error rate are broken alphabetically (ascending) for determinism.

    Returns:
        Tool name with the highest error rate; ``None`` when store is empty.
    """
    if not _TELEMETRY:
        return None
    max_rate = max(get_tool_error_rate(t) for t in _TELEMETRY)
    candidates = [
        t for t in _TELEMETRY
        if abs(get_tool_error_rate(t) - max_rate) < 1e-9
    ]
    return min(candidates)  # alphabetically first among rate-tied tools


def get_slowest_tool() -> str | None:
    """Return the name of the tool with the highest p95 latency.  Item 939.

    Enables dashboards to surface the current SLO risk at a glance.
    Ties in p95 are broken alphabetically (ascending) for determinism.

    Returns:
        Tool name with the highest p95 latency; ``None`` when store is empty.
    """
    if not _TELEMETRY:
        return None
    max_p95 = max(get_tool_p95_ms(t) for t in _TELEMETRY)
    candidates = [t for t in _TELEMETRY if abs(get_tool_p95_ms(t) - max_p95) < 1e-9]
    return min(candidates)  # alphabetically first among p95-tied tools


def get_tool_success_rate(tool_name: str) -> float:
    """Return the success rate for a tool.  Item 938.

    The complement of :func:`get_tool_error_rate`: ``1.0 - error_rate``.
    Unknown tools return ``1.0`` — no failures have been observed.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Success rate in [0.0, 1.0]; 1.0 for unknown tools.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or stats["call_count"] == 0:
        return 1.0
    return 1.0 - float(stats["error_count"]) / stats["call_count"]


def get_tool_success_count(tool_name: str) -> int:
    """Return the number of successful calls for a tool.  Item 937.

    ``call_count - error_count``: avoids arithmetic boilerplate at call sites.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Number of successful calls; 0 for unknown tools.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats:
        return 0
    return stats["call_count"] - stats["error_count"]


def get_tool_latency_range_ms(tool_name: str) -> tuple[float, float]:
    """Return (min, max) latency range for a tool.  Item 936.

    Convenience for callers that need both bounds without two separate calls.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        ``(min_latency_ms, max_latency_ms)`` tuple; ``(0.0, 0.0)`` for unknown
        tools or tools with no recorded calls.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or not stats["latencies"]:
        return (0.0, 0.0)
    return (float(min(stats["latencies"])), float(max(stats["latencies"])))


def get_tool_max_latency_ms(tool_name: str) -> float:
    """Return the maximum recorded latency for a tool.  Item 935.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Maximum latency value in milliseconds; 0.0 for unknown tools.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or not stats["latencies"]:
        return 0.0
    return float(max(stats["latencies"]))


def get_tool_min_latency_ms(tool_name: str) -> float:
    """Return the minimum recorded latency for a tool.  Item 934.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Minimum latency value in milliseconds; 0.0 for unknown tools.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or not stats["latencies"]:
        return 0.0
    return float(min(stats["latencies"]))


def get_tool_mean_latency_ms(tool_name: str) -> float:
    """Return the arithmetic mean latency for a tool.  Item 933.

    Note: mean and p50 coincide for symmetric distributions but diverge for
    skewed ones (e.g. [10, 20, 60] → mean=30.0, p50=20.0).  Use p50/p95 for
    latency SLO work; use mean for aggregate-cost estimates.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Arithmetic mean of all recorded latencies in milliseconds.
        Returns 0.0 for unknown tools or tools with no calls.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats or stats["call_count"] == 0:
        return 0.0
    return float(sum(stats["latencies"])) / stats["call_count"]


def get_tool_total_latency_ms(tool_name: str) -> float:
    """Return the sum of all recorded latencies for a tool.  Item 932.

    Useful for computing average latency (total / call_count) without re-reading
    the raw latency list separately.

    Args:
        tool_name: The MCP tool name to look up.

    Returns:
        Sum of all latency values in milliseconds; 0.0 for unknown tools.
    """
    stats = _TELEMETRY.get(tool_name)
    if not stats:
        return 0.0
    return float(sum(stats["latencies"]))


def get_tool_count() -> int:
    """Return the count of distinct tools ever recorded.  Item 930.

    Counts unique tool names in ``_TELEMETRY`` — not the total number of calls.
    Five calls across three distinct tools returns 3, not 5.

    Returns:
        Number of distinct tool names; 0 when no calls have been recorded.
    """
    return len(_TELEMETRY)


def get_all_tool_names() -> list[str]:
    """Return sorted list of all tool names ever recorded.  Item 929.

    Cumulative complement of :func:`get_windowed_tool_names` — includes every
    tool that has ever been passed to :func:`record_tool_call`, regardless of
    when the calls occurred.  Enables dashboards to enumerate the full tool
    catalog without filtering by recency.

    Returns:
        Alphabetically sorted list of all tool names in ``_TELEMETRY``.
        Empty list when no calls have been recorded yet.
    """
    return sorted(_TELEMETRY.keys())


def get_all_tool_telemetry_full() -> dict[str, dict]:
    """Return the complete 8-key profile for every recorded tool.  Item 950.

    Delegates to :func:`get_tool_telemetry_full` for each tool currently in
    ``_TELEMETRY``, assembling the results into a single map.

    Returns:
        ``{tool_name: get_tool_telemetry_full(tool_name)}`` for all recorded
        tools.  Empty dict when no calls have been recorded yet.  Each nested
        dict has exactly 8 keys: ``{call_count, error_count, error_rate,
        success_rate, p50_ms, p95_ms, min_ms, max_ms}``.
    """
    return {tool: get_tool_telemetry_full(tool) for tool in _TELEMETRY}


def get_windowed_global_p95_ms(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the pooled p95 latency across all tools in the recent window.  Item 952.

    Windowed complement of :func:`get_global_p95_ms` — queries
    ``_WINDOWED_TELEMETRY`` rather than the cumulative store.  Pools all
    latency records from **every tool** that fall within the last *window_ms* ms
    and computes p95 on the combined list.

    Pooling is critical: averaging per-tool p95 values over-weights low-traffic
    tools and gives the wrong aggregate when call counts differ.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        p95 latency in milliseconds over the combined pool of recent records
        across all tools.  0.0 when no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    pooled: list[float] = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    if not pooled:
        return 0.0
    return float(_percentile(sorted(pooled), 95.0))


def get_windowed_global_error_rate(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the overall error rate across all tools in the recent window.  Item 953.

    Windowed complement of :func:`get_global_error_rate` — queries
    ``_WINDOWED_TELEMETRY`` rather than the cumulative store.  Computes
    ``total_windowed_errors / total_windowed_calls`` (pooled / weighted) —
    NOT the average of per-tool windowed error rates.

    When tool call counts differ, naive averaging over-weights low-traffic
    tools and gives the wrong aggregate.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Error rate in [0.0, 1.0] over all recent records across all tools.
        0.0 when no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total_calls = 0
    total_errors = 0
    for records in store.values():
        for ts, _lat, ok in records:
            if ts >= cutoff_ms:
                total_calls += 1
                if not ok:
                    total_errors += 1
    if total_calls == 0:
        return 0.0
    return float(total_errors) / total_calls


def get_windowed_global_call_count(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> int:
    """Return total call count across all tools in the recent window.  Item 954.

    Windowed complement of :func:`get_total_call_count` — counts all records
    in ``_WINDOWED_TELEMETRY`` within the last *window_ms* ms across ALL tools.

    Completes the windowed-global triad:
    - :func:`get_windowed_global_p95_ms`  (item 952)
    - :func:`get_windowed_global_error_rate`  (item 953)
    - :func:`get_windowed_global_call_count`  (item 954)

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Total integer count of recent records across all tools.
        0 when no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    return sum(
        1
        for records in store.values()
        for ts, _lat, _ok in records
        if ts >= cutoff_ms
    )


def get_windowed_global_mean_latency_ms(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return mean latency across all tools in the recent window (pooled).  Item 955.

    Windowed complement of :func:`get_global_mean_latency_ms` — queries
    ``_WINDOWED_TELEMETRY``.  Computes ``total_latency / total_calls`` pooled
    across all tools, NOT the average of per-tool means.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        Arithmetic mean latency in milliseconds; 0.0 when no recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total_lat = 0.0
    total_calls = 0
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                total_lat += lat
                total_calls += 1
    if total_calls == 0:
        return 0.0
    return total_lat / total_calls


def get_windowed_global_p50_ms(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the pooled p50 latency across all tools in the recent window.  Item 956.

    Windowed complement of :func:`get_global_p50_ms` — pools all latency
    records from ``_WINDOWED_TELEMETRY`` within the last *window_ms* ms and
    computes p50 on the combined list.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        p50 latency in milliseconds over the combined pool of recent records.
        0.0 when no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    pooled: list[float] = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    if not pooled:
        return 0.0
    return float(_percentile(sorted(pooled), 50.0))


def get_windowed_busiest_tool(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> str | None:
    """Return the tool with the most calls in the recent window.  Item 957.

    Windowed analog of :func:`get_busiest_tool` (cumulative, item 942).
    Returns the tool_name whose windowed call count is highest.  When multiple
    tools tie for the maximum, the alphabetically first name is returned for
    deterministic output.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        The name of the busiest tool in the window, or ``None`` when the store
        is empty or no calls fall within the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    # Build {tool: windowed_call_count} for tools with ≥1 recent call
    counts: dict[str, int] = {}
    for tool, records in store.items():
        n = sum(1 for ts, _lat, _ok in records if ts >= cutoff_ms)
        if n > 0:
            counts[tool] = n
    if not counts:
        return None
    max_count = max(counts.values())
    candidates = [t for t, n in counts.items() if n == max_count]
    return min(candidates)


def get_windowed_slowest_tool(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> str | None:
    """Return the tool with the highest windowed p95 latency.  Item 958.

    Windowed analog of :func:`get_slowest_tool` (cumulative, item 939).
    Returns the tool_name whose windowed p95 latency is highest.  When multiple
    tools tie, the alphabetically first name is returned.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        The name of the slowest tool (by windowed p95), or ``None`` when the
        store is empty or no calls fall within the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    # Build {tool: windowed_p95} for tools with ≥1 recent latency record
    p95s: dict[str, float] = {}
    for tool, records in store.items():
        recent_lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
        if recent_lats:
            p95s[tool] = _percentile(recent_lats, 95.0)
    if not p95s:
        return None
    max_p95 = max(p95s.values())
    candidates = [t for t, p in p95s.items() if abs(p - max_p95) < 1e-9]
    return min(candidates)


def get_windowed_fastest_tool(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> str | None:
    """Return the tool with the lowest windowed p50 latency.  Item 959.

    Windowed analog of :func:`get_fastest_tool` (cumulative, item 941).
    Returns the tool_name whose windowed p50 latency is lowest.  When multiple
    tools tie, the alphabetically first name is returned.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        The name of the fastest tool (by windowed p50), or ``None`` when the
        store is empty or no calls fall within the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    # Build {tool: windowed_p50} for tools with ≥1 recent latency record
    p50s: dict[str, float] = {}
    for tool, records in store.items():
        recent_lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
        if recent_lats:
            p50s[tool] = _percentile(recent_lats, 50.0)
    if not p50s:
        return None
    min_p50 = min(p50s.values())
    candidates = [t for t, p in p50s.items() if abs(p - min_p50) < 1e-9]
    return min(candidates)


def get_windowed_most_error_prone_tool(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> str | None:
    """Return the tool with the highest windowed error rate.  Item 960.

    Windowed analog of :func:`get_most_error_prone_tool` (cumulative, item 940).
    Returns the tool_name whose windowed error rate is highest.  When multiple
    tools tie, the alphabetically first name is returned.  Tools with no recent
    calls are excluded (their windowed error rate is undefined, not 0.0).

    Uses error rate (not error count) so a tool with 2/2 failures is ranked
    higher than a tool with 10/1000 failures.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        The name of the most error-prone tool (by windowed error rate), or
        ``None`` when the store is empty or no calls fall within the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    # Build {tool: windowed_error_rate} for tools with ≥1 recent call
    rates: dict[str, float] = {}
    for tool, records in store.items():
        recent = [(ok,) for ts, _lat, ok in records if ts >= cutoff_ms]
        if recent:
            n = len(recent)
            errors = sum(1 for (ok,) in recent if not ok)
            rates[tool] = float(errors) / n
    if not rates:
        return None
    max_rate = max(rates.values())
    candidates = [t for t, r in rates.items() if abs(r - max_rate) < 1e-9]
    return min(candidates)


def get_windowed_tool_telemetry_full(
    tool_name: str,
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> dict:
    """Return the full 6-key windowed profile for a single tool.  Item 961.

    Windowed analog of :func:`get_tool_telemetry_full` (cumulative, item 949).
    Extends the 4-key :func:`get_tool_windowed_stats` result with two additional
    keys: ``error_count`` (exact integer count) and ``success_rate`` (= 1 -
    ``error_rate``), matching the full-profile contract.

    Args:
        tool_name: The MCP tool name to look up.
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        ``{call_count, error_count, error_rate, success_rate, p50_ms, p95_ms}``.
        All-zero dict with ``success_rate=1.0`` for unknown tools or when no
        calls fall within the window.
    """
    _zero: dict = {
        "call_count": 0,
        "error_count": 0,
        "error_rate": 0.0,
        "success_rate": 1.0,
        "p50_ms": 0.0,
        "p95_ms": 0.0,
    }
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    records = store.get(tool_name)
    if not records:
        return dict(_zero)
    cutoff_ms = now_ms - window_ms
    recent = [(lat, ok) for ts, lat, ok in records if ts >= cutoff_ms]
    if not recent:
        return dict(_zero)
    n = len(recent)
    errors = sum(1 for _, ok in recent if not ok)
    sorted_lats = sorted(lat for lat, _ in recent)
    error_rate = float(errors) / n
    return {
        "call_count": n,
        "error_count": errors,
        "error_rate": error_rate,
        "success_rate": 1.0 - error_rate,
        "p50_ms": _percentile(sorted_lats, 50.0),
        "p95_ms": _percentile(sorted_lats, 95.0),
    }


def get_all_windowed_tool_telemetry_full(
    window_ms: float,
    *,
    store: dict[str, list] | None = None,
    now_ms: float | None = None,
) -> dict[str, dict]:
    """Return the full 6-key windowed profile for every active tool.  Item 962.

    Windowed analog of :func:`get_all_tool_telemetry_full` (cumulative, item 950).
    Only tools with ≥1 call in the window are included — tools that exist in the
    store but have no recent records are excluded.

    Args:
        window_ms: Look-back window in milliseconds.
        store:     Windowed telemetry store (injectable; defaults to
                   ``_WINDOWED_TELEMETRY``).
        now_ms:    Current time in ms (defaults to ``time.time() * 1000``).

    Returns:
        ``{tool_name: get_windowed_tool_telemetry_full(tool_name, ...)}`` for each
        tool with ≥1 recent call.  Empty dict when no tools have recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    result: dict[str, dict] = {}
    for tool_name in store:
        profile = get_windowed_tool_telemetry_full(
            tool_name, window_ms, store=store, now_ms=now_ms
        )
        if profile["call_count"] > 0:
            result[tool_name] = profile
    return result


def get_windowed_top_n_tools_by_call_count(
    n: int,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> list[str]:
    """Return up to *n* tool names sorted descending by windowed call count.

    Ties broken alphabetically ascending.  Tools with no calls in the window
    are excluded.  Returns [] when n<=0, store empty, or no recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    if n <= 0:
        return []
    cutoff_ms = now_ms - window_ms
    counts: dict[str, int] = {}
    for tool, records in store.items():
        cnt = sum(1 for ts, _lat, _ok in records if ts >= cutoff_ms)
        if cnt > 0:
            counts[tool] = cnt
    if not counts:
        return []
    # Sort: descending count, then ascending name for ties
    ranked = sorted(counts.keys(), key=lambda t: (-counts[t], t))
    return ranked[:n]


def get_windowed_top_n_tools_by_error_rate(
    n: int,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> list[str]:
    """Return up to *n* tool names sorted descending by windowed error RATE.

    Ties broken alphabetically ascending.  Tools with no calls in the window
    are excluded.  Returns [] when n<=0, store empty, or no recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    if n <= 0:
        return []
    cutoff_ms = now_ms - window_ms
    rates: dict[str, float] = {}
    for tool, records in store.items():
        recent = [(ok,) for ts, _lat, ok in records if ts >= cutoff_ms]
        if not recent:
            continue
        cnt = len(recent)
        errors = sum(1 for (ok,) in recent if not ok)
        rates[tool] = float(errors) / cnt
    if not rates:
        return []
    # Sort: descending rate, then ascending name for ties
    ranked = sorted(rates.keys(), key=lambda t: (-rates[t], t))
    return ranked[:n]


def get_windowed_top_n_tools_by_p95_latency(
    n: int,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> list[str]:
    """Return up to *n* tool names sorted descending by windowed p95 latency.

    Ties broken alphabetically ascending.  Tools with no calls in the window
    are excluded.  Returns [] when n<=0, store empty, or no recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    if n <= 0:
        return []
    cutoff_ms = now_ms - window_ms
    p95s: dict[str, float] = {}
    for tool, records in store.items():
        recent_lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
        if recent_lats:
            p95s[tool] = _percentile(recent_lats, 95.0)
    if not p95s:
        return []
    ranked = sorted(p95s.keys(), key=lambda t: (-p95s[t], t))
    return ranked[:n]


def get_windowed_error_budget_used(
    tool_name: str,
    budget_rate: float,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fraction of error budget consumed by *tool_name* in the window.

    Result = actual_windowed_error_rate / budget_rate.
    Returns 0.0 when tool absent, no recent calls, or budget_rate==0.
    May exceed 1.0 when over-budget (not clamped).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    if budget_rate == 0.0:
        return 0.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [(ok,) for ts, _lat, ok in records if ts >= cutoff_ms]
    if not recent:
        return 0.0
    n = len(recent)
    errors = sum(1 for (ok,) in recent if not ok)
    actual_rate = float(errors) / n
    return actual_rate / budget_rate


def get_windowed_tools_over_error_budget(
    budget_rate: float,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> list[str]:
    """Return sorted list of tools with windowed error rate strictly > *budget_rate*.

    Tools with no recent calls are excluded.  Result is alphabetically sorted.
    Returns [] when none exceed the budget or no recent calls.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    over: list[str] = []
    for tool, records in store.items():
        recent = [(ok,) for ts, _lat, ok in records if ts >= cutoff_ms]
        if not recent:
            continue
        n = len(recent)
        errors = sum(1 for (ok,) in recent if not ok)
        rate = float(errors) / n
        if rate > budget_rate:
            over.append(tool)
    return sorted(over)


def get_windowed_latency_percentile(
    tool_name: str,
    percentile: float,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return an arbitrary *percentile* (0–100) of windowed latencies for *tool_name*.

    Uses the same linear-interpolation algorithm as `_percentile()`.
    Returns 0.0 when the tool is absent or has no calls in the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    if not recent_lats:
        return 0.0
    return _percentile(recent_lats, percentile)


def get_windowed_global_latency_percentile(
    percentile: float,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return an arbitrary *percentile* (0–100) of ALL windowed latencies fleet-wide.

    All recent latencies from every tool are pooled into a single sorted list
    before computing the percentile — NOT an average of per-tool percentiles.
    Returns 0.0 when the pool is empty (no recent calls at all).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    if not all_lats:
        return 0.0
    all_lats.sort()
    return _percentile(all_lats, percentile)


def get_windowed_tool_success_count(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the count of *successful* calls (ok=True) in the window for *tool_name*.

    Returns 0 when the tool is absent or has no calls in the window.
    Always returns int (not float).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return sum(1 for ts, _lat, ok in records if ts >= cutoff_ms and ok)


def get_windowed_global_success_count(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the total count of successful calls fleet-wide in the window.

    Sums successful (ok=True) calls across ALL tools.
    Returns 0 when the store is empty or no recent calls exist.
    Always returns int.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total: int = 0
    for records in store.values():
        total += sum(1 for ts, _lat, ok in records if ts >= cutoff_ms and ok)
    return total


def get_windowed_tool_error_count(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the count of *failed* calls (ok=False) in the window for *tool_name*.

    The dual of `get_windowed_tool_success_count`.
    Returns 0 when the tool is absent or has no calls in the window.
    Always returns int (not float).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return sum(1 for ts, _lat, ok in records if ts >= cutoff_ms and not ok)


def get_windowed_global_error_count(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the total count of failed calls fleet-wide in the window.

    Sums failed (ok=False) calls across ALL tools.
    Returns 0 when the store is empty or no recent calls exist.
    Property: success_count + error_count == total_call_count.
    Always returns int.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total: int = 0
    for records in store.values():
        total += sum(1 for ts, _lat, ok in records if ts >= cutoff_ms and not ok)
    return total


def get_windowed_tool_min_latency_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the minimum call latency in the window for *tool_name*.

    Includes latencies from both successful and failed calls.
    Returns 0.0 when the tool is absent or has no calls in the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    if not recent_lats:
        return 0.0
    return float(min(recent_lats))


def get_windowed_tool_max_latency_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the maximum call latency in the window for *tool_name*.

    The dual of `get_windowed_tool_min_latency_ms`.
    Includes latencies from both successful and failed calls.
    Returns 0.0 when the tool is absent or has no calls in the window.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    if not recent_lats:
        return 0.0
    return float(max(recent_lats))


def get_windowed_tool_latency_range_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the latency range (max - min) in the window for *tool_name*.

    Returns 0.0 when the tool is absent, has no calls, or all calls have
    the same latency (single call or uniform distribution).
    Composes max and min: range = max_latency - min_latency.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    if not recent_lats:
        return 0.0
    return float(max(recent_lats) - min(recent_lats))


def get_windowed_tool_mean_latency_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the arithmetic mean latency (ms) in the window for *tool_name*.

    Returns 0.0 when the tool is absent or has no recent calls.
    Note: mean([10,20,90]) = 40.0 != p50([10,20,90]) = 20.0 (primary discriminator).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    if not recent_lats:
        return 0.0
    return float(sum(recent_lats) / len(recent_lats))


def get_windowed_tool_latency_stddev_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the population standard deviation of latencies (ms) in the window for *tool_name*.

    Uses population stddev (divides by n) because the window contains the full observed
    population of calls, not a sample. Returns 0.0 when the tool is absent, has no recent
    calls, or has only one recent call.

    PRIMARY DISC.: lats [10, 20, 30] -> stddev≈8.165 (not range=20.0, not mean=20.0).
    Two-call discriminator: lats [10, 30] -> stddev=10.0 = |30-10|/2 = 10.0.
    Failed calls contribute their latency (latency is measured regardless of outcome).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(recent_lats)
    if n < 2:
        return 0.0
    mean = sum(recent_lats) / n
    variance = sum((lat - mean) ** 2 for lat in recent_lats) / n
    return float(variance ** 0.5)


def get_windowed_global_min_latency_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the global minimum latency fleet-wide in the window.  Item 979.

    Pools ALL recent call latencies from all tools and returns the minimum.
    Returns 0.0 when the store is empty or no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    if not all_lats:
        return 0.0
    return float(min(all_lats))


def get_windowed_global_max_latency_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the global maximum latency fleet-wide in the window.  Item 980.

    Pools ALL recent call latencies from all tools and returns the maximum.
    Returns 0.0 when the store is empty or no recent calls exist.
    Fleet-wide dual of get_windowed_tool_max_latency_ms (item 975).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    if not all_lats:
        return 0.0
    return float(max(all_lats))


def get_windowed_global_latency_range_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the global latency range (max - min) fleet-wide in the window.  Item 981.

    Pools ALL recent call latencies, computes global_max - global_min.
    Returns 0.0 when the store is empty, has a single recent call, or all
    latencies are identical.  Composes items 979 (global min) + 980 (global max).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    if not all_lats:
        return 0.0
    return float(max(all_lats) - min(all_lats))


def get_windowed_global_latency_stddev_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the population standard deviation of ALL windowed latencies fleet-wide.  Item 983.

    Pools ALL recent call latencies from all tools in the window and computes the
    population stddev (divides by n). Returns 0.0 when no recent calls exist or
    when fewer than 2 calls exist (a single observation has no spread).

    Fleet-wide dual of get_windowed_tool_latency_stddev_ms (item 982).
    PRIMARY DISC.: tool_a [10] + tool_b [10,10,90] -> pooled stddev≈34.641
    (not per-tool stddev average, not per-tool mean average).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    n = len(all_lats)
    if n < 2:
        return 0.0
    mean = sum(all_lats) / n
    variance = sum((lat - mean) ** 2 for lat in all_lats) / n
    return float(variance ** 0.5)


def get_windowed_tool_call_count(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the windowed call count for *tool_name*.  Item 982.

    Standalone accessor for the `call_count` field from
    get_windowed_tool_telemetry_full() (item 961); avoids forcing callers to
    unpack the full profile dict when only the count is needed.

    Counts ALL calls (successes + failures) within the window.
    Returns 0 for unknown tools or when no recent calls exist.
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return sum(1 for ts, _lat, _ok in records if ts >= cutoff_ms)


def get_windowed_tool_error_rate(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the windowed error rate for *tool_name*.  Item 985.

    Standalone accessor for the ``error_rate`` field from
    get_windowed_tool_telemetry_full() (item 961); avoids forcing callers to
    unpack the full profile dict.

    error_rate = error_count / call_count.
    Returns 0.0 for unknown tools or when no recent calls exist.
    Property: error_rate + success_rate == 1.0 for any non-empty window.
    PRIMARY DISC.: 5 calls with 2 failures -> 0.4 (not error_count=2, not success_rate=0.6).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [(ok,) for ts, _lat, ok in records if ts >= cutoff_ms]
    n = len(recent)
    if n == 0:
        return 0.0
    errors = sum(1 for (ok,) in recent if not ok)
    return float(errors / n)


def get_windowed_tool_success_rate(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the windowed success rate for *tool_name*.  Item 986.

    Complement of get_windowed_tool_error_rate (item 985).
    success_rate = success_count / call_count.
    Property: error_rate + success_rate == 1.0 for any non-empty window.

    Returns 0.0 for unknown tools or when no recent calls exist.
    PRIMARY DISC.: 5 calls with 2 failures -> 0.6 (not success_count=3, not error_rate=0.4).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [ok for ts, _lat, ok in records if ts >= cutoff_ms]
    n = len(recent)
    if n == 0:
        return 0.0
    successes = sum(1 for ok in recent if ok)
    return float(successes / n)


def get_windowed_global_success_rate(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide windowed success rate.  Item 988.

    Complement of get_windowed_global_error_rate (item 987).
    global_success_rate = global_success_count / global_call_count.
    Pools ALL calls across all tools in the window — NOT an average of per-tool rates.

    Property: global_success_rate + global_error_rate == 1.0 for non-empty window.
    Returns 0.0 when no recent calls exist.
    PRIMARY DISC.: tool_a 1/1 success + tool_b 0/3 successes -> pooled=0.25 (not 0.5).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_outcomes = [
        ok
        for records in store.values()
        for ts, _lat, ok in records
        if ts >= cutoff_ms
    ]
    n = len(all_outcomes)
    if n == 0:
        return 0.0
    successes = sum(1 for ok in all_outcomes if ok)
    return float(successes / n)


def get_windowed_tool_p50_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the p50 (median) latency in the window for *tool_name*.  Item 990.

    Convenience shortcut for get_windowed_latency_percentile(tool_name, 50, ...).
    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,20,30,40,90] -> p50=30.0 (not mean=38.0, not max=90.0).
    Even-count interpolation: [10,20,30,40] -> idx=1.5 -> 20+0.5*10=25.0.
    """
    return get_windowed_latency_percentile(
        tool_name, 50.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_p25_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the p25 (lower quartile) latency in the window for *tool_name*.  Item 1010.

    Convenience shortcut for get_windowed_latency_percentile(tool_name, 25, ...).
    Completes the named-percentile quintet alongside p50/p75/p95/p99.
    p25 is the lower quartile; IQR = p75 - p25.
    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8)
      idx = 0.25 * (8-1) = 1.75 -> 20 + 0.75*(50-20) = 42.5
      (kills floor=20.0; kills ceil=50.0).
    """
    return get_windowed_latency_percentile(
        tool_name, 25.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_p75_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the p75 latency in the window for *tool_name*.  Item 1008.

    Convenience shortcut for get_windowed_latency_percentile(tool_name, 75, ...).
    Completes the named-percentile quartet alongside p50/p95/p99.
    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8)
      idx = 0.75 * (8-1) = 5.25 -> 300 + 0.25*(500-300) = 350.0
      (kills floor=300.0; kills ceil=500.0).
    """
    return get_windowed_latency_percentile(
        tool_name, 75.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_p95_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the p95 latency in the window for *tool_name*.  Item 991.

    Convenience shortcut for get_windowed_latency_percentile(tool_name, 95, ...).
    The per-tool dual of get_windowed_global_p95_ms (item 922).
    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,20,30,40,50] -> p95=48.0 (not p50=30.0, not max=50.0).
    idx = 0.95 * (n-1) = 3.8; 40 + 0.8*(50-40) = 48.0.
    """
    return get_windowed_latency_percentile(
        tool_name, 95.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_p99_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the p99 latency in the window for *tool_name*.  Item 992.

    Convenience shortcut for get_windowed_latency_percentile(tool_name, 99, ...).
    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,20,30,40,50] -> p99=49.6 (not p95=48.0, not max=50.0).
    idx = 0.99 * (n-1) = 3.96; 40 + 0.96*(50-40) = 49.6.
    Order constraint: p99 >= p95 >= p50 for any non-empty window.
    """
    return get_windowed_latency_percentile(
        tool_name, 99.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_global_p99_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide p99 latency in the window.  Item 993.

    Shortcut for get_windowed_global_latency_percentile(99.0, window_ms, ...).
    Pools ALL recent latencies from all tools before computing the percentile --
    NOT an average of per-tool p99 values.
    Returns 0.0 when no recent calls exist.

    PRIMARY DISC.: tool_a[10,50] + tool_b[20,30] -> pooled [10,20,30,50]
      idx=0.99*3=2.97; p99=30+0.97*(50-30)=49.4
      (kills avg-of-per-tool-p99=39.75; kills max-per-tool-p99=49.6).
    """
    return get_windowed_global_latency_percentile(
        99.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_global_p25_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide p25 (lower quartile) latency in the window.  Item 1011.

    Shortcut for get_windowed_global_latency_percentile(25.0, window_ms, ...).
    Pools ALL recent latencies from all tools before computing the percentile --
    NOT an average of per-tool p25 values.
    Returns 0.0 when no recent calls exist.
    global_iqr == get_windowed_global_p75_ms - get_windowed_global_p25_ms.

    PRIMARY DISC.: tool_a [50,100] + tool_b [200,400]
      pooled sorted [50,100,200,400] (n=4), idx=0.25*3=0.75
      -> 50 + 0.75*(100-50) = 87.5
      (kills floor=50.0; kills ceil=100.0).
    """
    return get_windowed_global_latency_percentile(
        25.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_global_latency_p5_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide p5 (5th percentile) latency in the window.  Item 1046.

    Shortcut for get_windowed_global_latency_percentile(5.0, window_ms, ...).
    Pools ALL recent latencies from all tools before computing the percentile --
    NOT an average of per-tool p5 values.
    Returns 0.0 when no recent calls exist.

    PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[40,50]
      pooled [10,20,30,40,50] (n=5), idx=0.05*4=0.2
      -> 10 + 0.2*(20-10) = 12.0
      (kills per-tool-then-avg=(12.0+42.0)/2=27.0 -- NOT pooled;
       kills nearest-rank=10.0 -- no interpolation;
       correct pooled p5=12.0).
    """
    return get_windowed_global_latency_percentile(
        5.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_global_p5_p95_ratio(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide p5/p95 tail symmetry index (pooled raw values).  Item 1047.

    ratio = global_p5 / global_p95.  Returns 0.0 if global_p95 == 0.0.
    Pools ALL tool latencies before computing percentiles (NOT per-tool avg).
    Injectable store.  Pure function.  Fleet dual of per-tool item 1045.

    PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
      pooled [10,10,10,10,100] n=5
      p5=10.0 (idx=0.2 -> 10+0.2*0=10.0),
      p95=82.0 (idx=3.8 -> 10+0.8*(100-10)=82.0)
      ratio=10.0/82.0≈0.12195
      (kills per-tool-avg=1.0; kills ratio=1.0 symmetric assumption).
    """
    p5 = get_windowed_global_latency_percentile(5.0, window_ms, store=store, now_ms=now_ms)
    p95 = get_windowed_global_latency_percentile(95.0, window_ms, store=store, now_ms=now_ms)
    if p95 == 0.0:
        return 0.0
    return float(p5 / p95)


def get_windowed_global_p75_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide p75 latency in the window.  Item 1009.

    Shortcut for get_windowed_global_latency_percentile(75.0, window_ms, ...).
    Pools ALL recent latencies from all tools before computing the percentile --
    NOT an average of per-tool p75 values.
    Returns 0.0 when no recent calls exist.

    PRIMARY DISC.: tool_a [50,100] + tool_b [200,400]
      pooled sorted [50,100,200,400] (n=4), idx=0.75*3=2.25
      -> 200 + 0.25*(400-200) = 250.0
      (kills per-tool-avg approach which gives a different result).
    """
    return get_windowed_global_latency_percentile(
        75.0, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_throughput_per_sec(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return per-tool call throughput in calls/second over the recent window.  Item 996.

    Counts ALL calls (success + failures) that fall within the last *window_ms*
    milliseconds and divides by the window duration in seconds.

    Formula: call_count_in_window / (window_ms / 1000.0)

    Returns 0.0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: 5 calls in 1000ms window -> 5.0/sec
      (kills impl returning raw count=5; kills calls/window_ms=0.005).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    records = store.get(tool_name)
    if not records:
        return 0.0
    cutoff_ms = now_ms - window_ms
    count = sum(1 for ts, _lat, _ok in records if ts >= cutoff_ms)
    if count == 0:
        return 0.0
    return float(count / (window_ms / 1000.0))


def get_windowed_global_throughput_per_sec(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fleet-wide call throughput in calls/second over the recent window.  Item 997.

    Pools the total call count across ALL tools that fall within the last
    *window_ms* milliseconds and divides by the window duration in seconds.

    Formula: total_call_count_all_tools / (window_ms / 1000.0)

    Returns 0.0 when no recent calls exist anywhere in the fleet.

    PRIMARY DISC.: tool_a 3 calls + tool_b 2 calls in 1000ms -> 5.0/sec
      (kills avg-of-per-tool-throughput=(3+2)/2=2.5; kills max-per-tool=3.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total = sum(
        1
        for records in store.values()
        for ts, _lat, _ok in records
        if ts >= cutoff_ms
    )
    if total == 0:
        return 0.0
    return float(total / (window_ms / 1000.0))


def get_windowed_tool_latency_iqr_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return per-tool interquartile range (IQR = p75 - p25) of latency in window.  Item 999.

    IQR is a robust spread metric resistant to latency outliers (e.g., occasional
    10s timeout spikes inflate stddev and range but leave IQR stable).

    Computes: get_windowed_latency_percentile(tool, 75, ...) - get_windowed_latency_percentile(tool, 25, ...)

    Returns 0.0 for unknown tools or when no recent calls exist (single call also
    returns 0.0 since p75 == p25 for a 1-element distribution).

    PRIMARY DISC.: lats [10,20,30,40,50] -> IQR=20.0
      p75=idx=0.75*4=3.0 -> 40.0; p25=idx=0.25*4=1.0 -> 20.0; IQR=20.0
      (kills range=50-10=40.0; kills stddev≈14.14).
    """
    p75 = get_windowed_latency_percentile(tool_name, 75.0, window_ms, store=store, now_ms=now_ms)
    p25 = get_windowed_latency_percentile(tool_name, 25.0, window_ms, store=store, now_ms=now_ms)
    return float(p75 - p25)


def get_windowed_global_latency_iqr_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fleet-wide IQR (p75 - p25) of pooled latency in the window.  Item 1000.

    Fleet-wide dual of get_windowed_tool_latency_iqr_ms (item 999).
    Pools ALL recent latencies from all tools before computing the IQR —
    NOT an average of per-tool IQR values.

    Computes: get_windowed_global_latency_percentile(75, ...) - get_windowed_global_latency_percentile(25, ...)

    Returns 0.0 when no recent calls exist.

    PRIMARY DISC.: tool_a [10,50] + tool_b [20,30] -> pooled [10,20,30,50]
      p75=35.0, p25=17.5, IQR=17.5 (kills avg-of-per-tool-IQR=12.5).
    """
    p75 = get_windowed_global_latency_percentile(75.0, window_ms, store=store, now_ms=now_ms)
    p25 = get_windowed_global_latency_percentile(25.0, window_ms, store=store, now_ms=now_ms)
    return float(p75 - p25)


def get_windowed_tool_latency_variance_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return per-tool population variance of latency in the window.  Item 1001.

    Population variance (divide by n, not n-1) of all latency values
    (success + failure calls) within the last *window_ms* ms.

    Complements get_windowed_tool_latency_stddev_ms: variance == stddev ** 2.

    Returns 0.0 for unknown tools or when fewer than 2 calls exist in the window
    (consistent with the stddev convention: single observation has no spread).

    PRIMARY DISC.: lats [10,20,30] -> var=200/3≈66.67
      (kills sample_var dividing by n-1=2 -> 100.0; kills stddev=sqrt(66.67)≈8.165).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(recent_lats)
    if n < 2:
        return 0.0
    mean = sum(recent_lats) / n
    variance = sum((lat - mean) ** 2 for lat in recent_lats) / n
    return float(variance)


def get_windowed_global_latency_variance_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fleet-wide population variance of pooled latency in the window.  Item 1002.

    Fleet-wide dual of get_windowed_tool_latency_variance_ms (item 1001).
    Pools ALL recent latencies from all tools before computing the population variance —
    NOT an average of per-tool variance values.

    Returns 0.0 when fewer than 2 pooled calls exist in the window.

    PRIMARY DISC.: tool_a [10,30] + tool_b [20,40] -> pooled [10,20,30,40]
      mean=25.0; var=125.0 (kills avg-of-per-tool-var=100.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    n = len(all_lats)
    if n < 2:
        return 0.0
    mean = sum(all_lats) / n
    variance = sum((lat - mean) ** 2 for lat in all_lats) / n
    return float(variance)


def get_windowed_tool_slow_call_count(
    tool_name: str,
    window_ms: float,
    threshold_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return the count of calls with latency_ms strictly > threshold_ms in the window.  Item 1003.

    SLO compliance query: "how many calls exceeded the threshold in the last window_ms ms?"

    Counts ALL calls (success + failures) whose recorded latency is strictly greater than
    *threshold_ms*.  Calls with latency exactly equal to *threshold_ms* do NOT count.

    Returns 0 for unknown tools or when no recent calls exist.

    PRIMARY DISC.: lats [10,50,200,300] with threshold=100 -> 2
      (kills count-all=4; strictly > so threshold=50 with lats [10,50,200] -> 1 not 2).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return int(sum(1 for ts, lat, _ok in records if ts >= cutoff_ms and lat > threshold_ms))


def get_windowed_tool_slow_call_rate(
    tool_name: str,
    window_ms: float,
    threshold_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fraction of calls with latency_ms > threshold_ms in the window.  Item 1004.

    SLO violation rate: slow_call_count / total_call_count.

    Returns 0.0 when the tool is unknown or no recent calls exist.
    Strictly greater than: latency exactly equal to threshold_ms does NOT count.

    PRIMARY DISC.: lats [10,50,200,300] threshold=100 -> 0.5 (2 slow / 4 total).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [(lat,) for ts, lat, _ok in records if ts >= cutoff_ms]
    total = len(recent)
    if total == 0:
        return 0.0
    slow = sum(1 for (lat,) in recent if lat > threshold_ms)
    return float(slow / total)


def get_windowed_global_slow_call_count(
    window_ms: float,
    threshold_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return fleet-wide count of calls with latency_ms > threshold_ms in the window.  Item 1005.

    Fleet-wide dual of get_windowed_tool_slow_call_count (item 1003).
    Pools ALL tools — a call from ANY tool that exceeds the threshold is counted.

    Returns 0 when no recent calls exist.
    Strictly greater than: calls with latency exactly equal to threshold_ms do NOT count.

    PRIMARY DISC.: tool_a [10,200,500] + tool_b [50] threshold=100 -> 2
      (2 slow from tool_a, 0 from tool_b; fleet total = 2).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    return int(sum(
        1
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms and lat > threshold_ms
    ))


def get_windowed_global_slow_call_rate(
    window_ms: float,
    threshold_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fleet-wide SLO violation rate: slow_count / total_count.  Item 1006.

    Pools ALL tools — slow_call_count_all_tools / total_call_count_all_tools.
    Returns float in [0, 1].  0.0 when no recent calls.
    Strictly greater than: calls with latency exactly equal to threshold_ms do NOT count.

    PRIMARY DISC.: tool_a [10,200] + tool_b [300,50] threshold=100 -> 0.5
      (2 slow [200,300] / 4 total = 0.5; kills slow_count=2 int; kills total=4 int).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_recent = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    total = len(all_recent)
    if total == 0:
        return 0.0
    slow = sum(1 for lat in all_recent if lat > threshold_ms)
    return float(slow / total)


def get_windowed_tool_latency_cv(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the per-tool coefficient of variation (CV) of latency.  Item 1012.

    CV = stddev_ms / mean_ms — a dimensionless ratio measuring relative spread.
    0.0 for unknown tools, empty windows, single calls, or when mean=0 (divide-by-zero guard).
    CV > 1 means high relative variability; CV < 0.5 means tight/predictable.

    PRIMARY DISC.: lats [10,20,30,40,50]
      mean=30, variance=200 (population), stddev=sqrt(200)≈14.1421
      CV=14.1421/30≈0.4714 (kills stddev float; kills mean float; correct CV float).
    """
    mean = get_windowed_tool_mean_latency_ms(tool_name, window_ms, store=store, now_ms=now_ms)
    if mean == 0.0:
        return 0.0
    stddev = get_windowed_tool_latency_stddev_ms(tool_name, window_ms, store=store, now_ms=now_ms)
    return float(stddev / mean)


def get_windowed_global_latency_cv(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the fleet-wide coefficient of variation (CV) of latency.  Item 1013.

    CV = fleet_stddev_ms / fleet_mean_ms — both computed from pooled latencies.
    NOT an average of per-tool CVs.
    0.0 when no recent calls exist or fleet mean=0.

    PRIMARY DISC.: tool_a [10,50] + tool_b [90,150]
      pooled mean=75, pooled variance=((65^2+25^2+15^2+75^2)/4)=2362.5,
      stddev≈48.606, CV=48.606/75≈0.6481
      (kills avg-per-tool-CV; correct pooled-CV≈0.6481).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats = [
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ]
    n = len(all_lats)
    if n == 0:
        return 0.0
    mean = sum(all_lats) / n
    if mean == 0.0:
        return 0.0
    if n < 2:
        return 0.0
    variance = sum((lat - mean) ** 2 for lat in all_lats) / n
    stddev = variance ** 0.5
    return float(stddev / mean)


def get_windowed_tool_consecutive_error_count(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> int:
    """Return number of consecutive errors at the END of the window.  Item 1014.

    Counts from the most-recent call backwards until a success is found.
    Detects active error storms / outages.
    0 when the last call succeeded, or when no recent calls exist.

    PRIMARY DISC.: [True, False, True, False, False] (oldest->newest) -> 2
      (not total_errors=3; streak stops at the True in position -3).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = sorted(
        [(ts, ok) for ts, _lat, ok in records if ts >= cutoff_ms],
        key=lambda x: x[0],  # sort oldest-first by timestamp
    )
    count = 0
    for _ts, ok in reversed(recent):  # iterate newest-first
        if not ok:
            count += 1
        else:
            break
    return int(count)


def get_windowed_tool_last_call_success(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> bool | None:
    """Return the success flag of the most-recent call in the window.  Item 1015.

    True  — most-recent call succeeded.
    False — most-recent call errored.
    None  — no recent calls exist (unknown/empty tool or all calls outside window).

    Instant health pulse without rate aggregation.

    PRIMARY DISC.: records where last call (highest ts) has success=False -> False
      (not float error_rate; not bool True; not None; strictly the last call's success flag).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [(ts, ok) for ts, _lat, ok in records if ts >= cutoff_ms]
    if not recent:
        return None
    _ts, ok = max(recent, key=lambda x: x[0])  # most-recent by timestamp
    return bool(ok)


def get_windowed_tool_first_call_ts(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float | None:
    """Return the timestamp (ms) of the oldest call in the window.  Item 1016.

    Lowest ts_ms among recent records. None if no recent calls.
    Used to compute window age and detect cold-start vs warm-path.

    PRIMARY DISC.: ts [_NOW-40, _NOW-20, _NOW-10] -> _NOW-40
      (kills last_ts=_NOW-10; kills None when records exist).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_ts = [ts for ts, _lat, _ok in records if ts >= cutoff_ms]
    if not recent_ts:
        return None
    return float(min(recent_ts))


def get_windowed_tool_last_call_ts(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float | None:
    """Return the timestamp (ms) of the most-recent call in the window.  Item 1017.

    Highest ts_ms among recent records. None if no recent calls.
    Dual of get_windowed_tool_first_call_ts; pair gives window coverage [first_ts, last_ts].

    PRIMARY DISC.: ts [_NOW-40, _NOW-20, _NOW-10] -> _NOW-10
      (kills first_ts=_NOW-40; kills mean-ts; correct newest ts).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent_ts = [ts for ts, _lat, _ok in records if ts >= cutoff_ms]
    if not recent_ts:
        return None
    return float(max(recent_ts))


def get_windowed_tool_call_rate_per_sec(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return per-tool call rate in calls/second over the recent window.  Item 1018.

    Semantic alias for get_windowed_tool_throughput_per_sec — same computation,
    "rate" vocabulary for callers that prefer it over "throughput".
    0.0 for unknown tools or when no recent calls exist.

    Formula: call_count_in_window / (window_ms / 1000.0)

    PRIMARY DISC.: 10 calls in 2000ms window -> 10/(2000/1000) = 5.0 calls/sec
      (kills count=10 int; kills calls/ms=0.005; correct calls/sec=5.0).
    """
    return get_windowed_tool_throughput_per_sec(
        tool_name, window_ms, store=store, now_ms=now_ms
    )


def get_windowed_tool_latency_sum_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return the sum of all latencies in the window for *tool_name*.  Item 1019.

    total_latency_ms = sum(latency_ms for all calls in window).
    0.0 for unknown tools or when no recent calls exist.
    Enables mean recomputation without another pass: mean = sum / count.

    PRIMARY DISC.: lats [10, 50, 200] -> sum=260.0
      (kills count=3 int; kills mean=86.67 float; kills max=200; correct sum=260.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return float(sum(lat for ts, lat, _ok in records if ts >= cutoff_ms))


def get_windowed_global_latency_sum_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fleet-wide sum of all latencies in the window.  Item 1020.

    Pools ALL tool latencies. 0.0 when no recent calls exist.
    Enables fleet mean without per-tool iteration:
      fleet_mean = global_latency_sum_ms / global_call_count.

    PRIMARY DISC.: tool_a [10,50] + tool_b [200,300] -> 560.0
      (kills per-tool-sum-a=60; kills per-tool-sum-b=500; correct pooled=560.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    return float(sum(
        lat
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ))


def get_windowed_tool_latency_skewness(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool latency skewness (3rd standardised moment).  Item 1022.

    population_skewness = (1/n) * sum((lat - mean)^3) / pop_stddev^3

    0.0 for <3 calls (not enough data) or stddev=0 (uniform distribution).
    Injectable store.  Pure function.

    Positive skew -> right tail (slow outliers).
    Negative skew -> left tail (fast outliers).

    PRIMARY DISC.: lats [10, 10, 10, 100]
      n=4, mean=32.5, pop_variance=1518.75, pop_stddev≈38.9712
      skewness ≈ 1.1554 (positive right-tail outlier at 100ms)
      kills stddev≈38.97 (wrong answer); kills variance≈1518.75 (wrong answer).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n < 3:
        return 0.0
    mean = sum(lats) / n
    pop_variance = sum((lat - mean) ** 2 for lat in lats) / n
    if pop_variance == 0.0:
        return 0.0
    pop_stddev = pop_variance ** 0.5
    return float(sum((lat - mean) ** 3 for lat in lats) / (n * pop_stddev ** 3))


def get_windowed_tool_latency_above_budget_ms(
    tool_name: str,
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return total excess latency above *budget_ms* for *tool_name* in the window.  Item 1023.

    Computes sum(max(0, lat - budget_ms)) for every call in the window.
    Measures cumulative latency "debt" above SLA.
    Returns 0.0 when the tool is absent, has no recent calls, or all calls
    are at or below budget.

    PRIMARY DISC.: lats [50, 150, 300] budget=100 -> excess_sum=250.0
      (kills count_above=2 int; kills sum_all=500.0 float; correct excess_sum=250.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    return float(sum(
        max(0.0, lat - budget_ms)
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ))


def get_windowed_global_latency_above_budget_ms(
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide total excess latency above SLA budget.  Item 1024.

    global_excess = sum(max(0, lat - budget_ms)) for ALL tools × calls in window.

    0.0 for empty store or all calls at/below budget.  Injectable store.  Pure.
    Fleet-wide dual of get_windowed_tool_latency_above_budget_ms (item 1023).

    PRIMARY DISC.: tool_a [50,150] + tool_b [200,300] budget=100
      tool_a excess = 50; tool_b excess = 300; global = 350.0
      (kills per-tool-a=50; kills per-tool-b=300; correct pooled=350.0 float).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    return float(sum(
        max(0.0, lat - budget_ms)
        for records in store.values()
        for ts, lat, _ok in records
        if ts >= cutoff_ms
    ))


def get_windowed_tool_above_budget_call_rate(
    tool_name: str,
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Return fraction of calls exceeding *budget_ms* for *tool_name*.  Item 1025.

    above_budget_count / total_count in window.
    0.0 for unknown tools or when no recent calls exist.
    Complements item-1023 (excess sum) with a rate/fraction view.

    PRIMARY DISC.: lats [50, 150, 200, 300] budget=100 -> 3 of 4 above -> 0.75
      (kills count=3 int; kills excess_sum=350.0 float; correct rate=0.75).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    recent = [(ts, lat) for ts, lat, _ok in records if ts >= cutoff_ms]
    total = len(recent)
    if total == 0:
        return 0.0
    above = sum(1 for _ts, lat in recent if lat > budget_ms)
    return float(above / total)


def get_windowed_global_above_budget_call_rate(
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide SLA breach rate across all tools in the window.  Item 1026.

    global_rate = count(lat > budget_ms, all tools) / total_count(all tools)

    0.0 for empty store.  Pools ALL calls before dividing (not average of per-tool rates).
    Injectable store.  Pure function.
    Fleet-wide dual of get_windowed_tool_above_budget_call_rate (item 1025).

    PRIMARY DISC.: tool_a [100, 200] + tool_b [200] budget=100
      pooled above=2, pooled total=3 -> rate=2/3≈0.6667
      (kills naive-avg-per-tool=(0.5+1.0)/2=0.75; correct pooled=0.6667 float).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    above = 0
    total = 0
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                total += 1
                if lat > budget_ms:
                    above += 1
    if total == 0:
        return 0.0
    return float(above / total)


def get_windowed_tool_p5_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """5th-percentile latency alias for get_windowed_latency_percentile(tool, 5.0, ...).  Item 1043.

    Thin delegate extending the percentile family to the lower extreme tail.
    Linear interpolation.  Returns 0.0 for unknown/empty tool.

    PRIMARY DISC.: lats [10,20,...,100] n=10 -> idx=0.05*9=0.45
      -> 10 + 0.45*(20-10) = 14.5
      (kills p10=19.0; kills nearest-rank=10.0; correct=14.5).
    """
    return get_windowed_latency_percentile(tool_name, 5.0, window_ms, store=store, now_ms=now_ms)


def get_windowed_tool_p5_p95_ratio(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """p5/p95 tail symmetry index for a single tool in the window.  Item 1045.

    Thin composition: p5 / p95.  Returns 0.0 if p95 == 0.0 (no data or all zero).
    Wider tail coverage than p10/p90 ratio (item 1029).
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,...,100] n=10
      -> p5=14.5, p95=95.5, ratio=14.5/95.5≈0.1518
      (kills p10/p90 ratio≈0.2088 -- wrong percentile pair;
       kills ratio=1.0 -- symmetric assumption;
       correct=14.5/95.5≈0.1518 via linear interpolation).
    """
    p5 = get_windowed_latency_percentile(tool_name, 5.0, window_ms, store=store, now_ms=now_ms)
    p95 = get_windowed_latency_percentile(tool_name, 95.0, window_ms, store=store, now_ms=now_ms)
    if p95 == 0.0:
        return 0.0
    return float(p5 / p95)


def get_windowed_tool_p10_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """10th-percentile latency alias for get_windowed_latency_percentile(tool, 10.0, ...).  Item 1027.

    Extends the percentile family below p25.  Linear interpolation.
    Returns 0.0 for unknown/empty tool (consistent with other p-series delegates).

    PRIMARY DISC.: lats [10,20,30,40,50] -> idx=0.4 -> 10+0.4*(20-10)=14.0
      (kills min=10.0; kills p25=17.5; correct interpolated p10=14.0).
    """
    return get_windowed_latency_percentile(tool_name, 10.0, window_ms, store=store, now_ms=now_ms)


def get_windowed_tool_p90_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """90th-percentile latency alias for get_windowed_latency_percentile(tool, 90.0, ...).  Item 1028.

    Extends percentile family above p75.  Linear interpolation.
    Returns 0.0 for unknown/empty tool (consistent with other p-series delegates).

    PRIMARY DISC.: lats [10,20,30,40,50] -> idx=3.6 -> 40+0.6*(50-40)=46.0
      (kills max=50.0; kills p75=32.5; correct interpolated p90=46.0).
    """
    return get_windowed_latency_percentile(tool_name, 90.0, window_ms, store=store, now_ms=now_ms)


def get_windowed_tool_p10_p90_ratio(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """p10/p90 tail symmetry index for per-tool latency.  Item 1029.

    ratio = p10 / p90.
    0.0 if p90 == 0.0 (guard against division by zero).
    Always in (0, 1] for non-degenerate distributions (p10 <= p90).

    ratio → 1.0  symmetric distribution (e.g. all-equal latencies).
    ratio → 0.0  extreme right tail (slow outliers dominate).

    Uses the same injectable store/now_ms path as p10 and p90 delegates.

    PRIMARY DISC.: lats [10,20,30,40,50] -> p10=14.0, p90=46.0 -> ratio≈0.30435
      (kills p90/p10≈3.286 inverted; kills p10-p90=32.0 difference; correct=0.30435).
    """
    p10 = get_windowed_latency_percentile(tool_name, 10.0, window_ms, store=store, now_ms=now_ms)
    p90 = get_windowed_latency_percentile(tool_name, 90.0, window_ms, store=store, now_ms=now_ms)
    if p90 == 0.0:
        return 0.0
    return float(p10 / p90)


def get_windowed_tool_latency_kurtosis(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool excess kurtosis (4th standardised moment, Fisher definition).  Item 1030.

    excess_kurtosis = (1/n) * sum((lat - mean)^4) / pop_stddev^4 - 3.0

    Fisher definition: normal distribution = 0.0.
    Positive = heavy-tailed (outlier-prone); negative = light-tailed.
    0.0 for n<4 or stddev=0.  Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,10,10,10,100]
      mean=28, stddev=36, raw_kurt=3.25, excess=0.25
      (kills variance=1296; kills stddev=36; kills raw_kurt=3.25; correct excess=0.25).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n < 4:
        return 0.0
    mean = sum(lats) / n
    pop_variance = sum((lat - mean) ** 2 for lat in lats) / n
    if pop_variance == 0.0:
        return 0.0
    pop_stddev = pop_variance ** 0.5
    raw_kurt = sum((lat - mean) ** 4 for lat in lats) / (n * pop_stddev ** 4)
    return float(raw_kurt - 3.0)


def get_windowed_tool_latency_mad_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Median Absolute Deviation (MAD) of per-tool latency in the window.  Item 1032.

    MAD = median(|lat - median(lats)|) for all calls in window.
    0.0 for unknown/empty tool.  Injectable store.  Pure function.

    Robust spread measure: unaffected by outliers until >50% of calls are extreme.
    Complementary to stddev (sensitive to outliers) and IQR (quartile-based).

    PRIMARY DISC.: lats [10,20,30,40,100]
      median=30, abs_devs=[20,10,0,10,70], sorted=[0,10,10,20,70], MAD=10.0
      (kills stddev≈32; kills mean_abs_dev=24; kills range=90; correct MAD=10.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(lats)
    if n == 0:
        return 0.0
    # compute median of latencies
    mid = n // 2
    med = lats[mid] if n % 2 == 1 else (lats[mid - 1] + lats[mid]) / 2.0
    # compute median of absolute deviations
    devs = sorted(abs(lat - med) for lat in lats)
    mid2 = n // 2
    mad = devs[mid2] if n % 2 == 1 else (devs[mid2 - 1] + devs[mid2]) / 2.0
    return float(mad)


def get_windowed_tool_latency_mad_stddev_ratio(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """MAD/stddev ratio — outlier sensitivity index.  Item 1033.

    ratio = MAD / stddev.
    0.0 if stddev == 0 (guard) or no recent calls.

    For a normal distribution: ratio ≈ 0.7979.
    ratio → 0.0  stddev is outlier-dominated (MAD stayed near 0, stddev inflated).
    ratio → 1.0  uniform-ish data, both measures agree.

    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,10,10,10,100]
      median=10, MAD=0.0, stddev=36.0, ratio=0.0
      (kills MAD/stddev standalone; kills ratio=1.0; correct ratio=0.0).
    """
    mad = get_windowed_tool_latency_mad_ms(tool_name, window_ms, store=store, now_ms=now_ms)
    stddev = get_windowed_tool_latency_stddev_ms(tool_name, window_ms, store=store, now_ms=now_ms)
    if stddev == 0.0:
        return 0.0
    return float(mad / stddev)


def get_windowed_tool_latency_trimmed_mean_ms(
    tool_name: str,
    window_ms: float,
    trim_pct: float = 0.1,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Trimmed (truncated) mean of per-tool latency.  Item 1034.

    Discards floor(trim_pct * n) values from EACH tail, returns mean of remainder.
    0.0 for unknown/empty tool or when nothing remains after trimming.
    Default trim_pct=0.1 (10% each tail).  Injectable store.  Pure function.

    More robust than full mean (outliers discarded), less extreme than median.

    PRIMARY DISC.: lats [10,20,30,40,100] trim_pct=0.2
      k=floor(0.2*5)=1 -> keep [20,30,40] -> trimmed_mean=30.0
      (kills full_mean=40.0; kills k=0/no-trim=40.0; correct=30.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(lats)
    if n == 0:
        return 0.0
    k = int(n * trim_pct)  # floor via int
    trimmed = lats[k: n - k] if k > 0 else lats
    if not trimmed:
        return 0.0
    return float(sum(trimmed) / len(trimmed))


def get_windowed_tool_latency_winsorized_mean_ms(
    tool_name: str,
    window_ms: float,
    winsor_pct: float = 0.1,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Winsorized mean of per-tool latency in the window.  Item 1035.

    Clamp the bottom and top floor(winsor_pct * n) values to their respective
    boundary values; compute the mean of all n clamped values.
    0.0 for unknown/empty tool.  Injectable store.  Pure function.
    Default winsor_pct=0.1 (clamp 10% each tail).

    Unlike trimmed mean (which discards k values from each tail, reducing n),
    winsorized mean RETAINS all n values in the denominator — outliers are
    replaced by the boundary value, not removed.  This preserves statistical
    power while reducing outlier sensitivity.

    PRIMARY DISC.: lats [10,20,30,40,100] winsor_pct=0.2
      n=5, k=floor(0.2*5)=1
      sorted=[10,20,30,40,100]; lo=sorted[1]=20, hi=sorted[3]=40
      clamped=[20,20,30,40,40]   (10→20, 100→40)
      winsor_mean=(20+20+30+40+40)/5=150/5=30.0
      (kills full_mean=40.0; kills boundary_pair=[20,40]; correct=30.0 with n=5).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(lats)
    if n == 0:
        return 0.0
    k = int(n * winsor_pct)  # floor via int
    if k == 0:
        # no clamping — identical to full mean
        return float(sum(lats) / n)
    lo = lats[k]
    hi = lats[n - 1 - k]
    clamped = [max(lo, min(hi, lat)) for lat in lats]
    return float(sum(clamped) / n)


def get_windowed_global_latency_mad_stddev_ratio(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide MAD/stddev ratio (outlier sensitivity index).  Item 1042.

    ratio = pooled_MAD / pooled_stddev
    0.0 if pooled_stddev == 0.0 (guard against division by zero).
    Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_mad_stddev_ratio (item 1033).
    Composes get_windowed_global_latency_mad_ms + get_windowed_global_latency_stddev_ms.

    PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
      pooled median=10, MAD=0.0, stddev=36.0 -> ratio=0.0
      (kills ratio=1.0; correct=0.0 showing outlier-dominated stddev).
    """
    mad = get_windowed_global_latency_mad_ms(window_ms, store=store, now_ms=now_ms)
    stddev = get_windowed_global_latency_stddev_ms(window_ms, store=store, now_ms=now_ms)
    if stddev == 0.0:
        return 0.0
    return float(mad / stddev)


def get_windowed_global_latency_kurtosis(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide excess kurtosis (Fisher definition) of pooled latency.  Item 1041.

    Pools ALL latencies across ALL tools, then:
      raw_kurtosis = sum((lat - mean)^4) / (n * pop_stddev^4)
      excess_kurtosis = raw_kurtosis - 3.0
    0.0 for n < 4 or pop_stddev = 0.0 (all equal).
    Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_kurtosis (item 1030).
    NOT an average of per-tool kurtosis values.

    PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
      pooled n=5, mean=28, pop_std=36 (exact),
      sum4=27293760, raw_kurt=3.25, excess=0.25
      (kills per-tool-avg=0.0; kills raw_kurt=3.25 w/o -3; correct=0.25).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n < 4:
        return 0.0
    mean = sum(all_lats) / n
    pop_variance = sum((lat - mean) ** 2 for lat in all_lats) / n
    if pop_variance == 0.0:
        return 0.0
    pop_stddev = pop_variance ** 0.5
    raw_kurt = sum((lat - mean) ** 4 for lat in all_lats) / (n * pop_stddev ** 4)
    return float(raw_kurt - 3.0)


def get_windowed_global_latency_skewness(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide population skewness of pooled latency.  Item 1040.

    Pools ALL latencies across ALL tools, then:
      skewness = sum((lat - mean)^3) / (n * pop_stddev^3)
    0.0 for n < 3 or pop_stddev = 0.0 (all equal).
    Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_skewness (item 1022).
    NOT an average of per-tool skewness values.

    PRIMARY DISC.: tool_a=[10,10,10] + tool_b=[100]
      pooled n=4, mean=32.5, sum_cubed=273375.0, pop_std=38.971...
      skewness = 2/sqrt(3) ≈ 1.1547
      (kills per-tool-avg=0.0 — each tool alone has skewness=0;
       correct pooled skewness ≈ 1.1547).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n < 3:
        return 0.0
    mean = sum(all_lats) / n
    pop_variance = sum((lat - mean) ** 2 for lat in all_lats) / n
    if pop_variance == 0.0:
        return 0.0
    pop_stddev = pop_variance ** 0.5
    return float(sum((lat - mean) ** 3 for lat in all_lats) / (n * pop_stddev ** 3))


def get_windowed_global_latency_winsorized_mean_ms(
    window_ms: float,
    winsor_pct: float = 0.1,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide winsorized mean of pooled latency.  Item 1039.

    Pools ALL latencies across ALL tools, sorts them, clamps the bottom and
    top floor(winsor_pct * n) values to their respective boundary values,
    and returns the mean of all n clamped values.
    0.0 for empty store.  Default winsor_pct=0.1 (clamp 10% each tail).
    Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_winsorized_mean_ms (item 1035).
    NOT an average of per-tool winsorized means.  Unlike trimmed mean,
    retains all n values in the denominator — outliers replaced, not removed.

    PRIMARY DISC.: tool_a=[10,100] + tool_b=[20,30,40] winsor_pct=0.2
      pooled sorted=[10,20,30,40,100], n=5, k=1
      lo=20, hi=40, clamped=[20,20,30,40,40], mean=150/5=30.0
      (kills full_mean=40.0; kills trimmed n=3/5=different; correct=30.0 with n=5).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n == 0:
        return 0.0
    lats = sorted(all_lats)
    k = int(n * winsor_pct)  # floor via int
    if k == 0:
        return float(sum(lats) / n)
    lo = lats[k]
    hi = lats[n - 1 - k]
    clamped = [max(lo, min(hi, lat)) for lat in lats]
    return float(sum(clamped) / n)


def get_windowed_global_latency_trimmed_mean_ms(
    window_ms: float,
    trim_pct: float = 0.1,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide trimmed (truncated) mean of pooled latency.  Item 1038.

    Pools ALL latencies across ALL tools, sorts them, discards
    floor(trim_pct * n) values from each tail, and returns the mean
    of the remaining values.
    0.0 for empty store or when nothing remains after trimming.
    Default trim_pct=0.1 (10% each tail).  Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_trimmed_mean_ms (item 1034).
    NOT an average of per-tool trimmed means.

    PRIMARY DISC.: tool_a=[10,100] + tool_b=[20,30,40] trim_pct=0.2
      pooled sorted=[10,20,30,40,100], n=5, k=1
      keep [20,30,40] -> trimmed_mean=30.0
      (kills full_mean=40.0; kills per-tool-then-avg=42.5; correct=30.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n == 0:
        return 0.0
    lats = sorted(all_lats)
    k = int(n * trim_pct)  # floor via int
    trimmed = lats[k: n - k] if k > 0 else lats
    if not trimmed:
        return 0.0
    return float(sum(trimmed) / len(trimmed))


def get_windowed_global_latency_mad_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide Median Absolute Deviation (MAD) of pooled latency.  Item 1037.

    Pools ALL latencies across ALL tools in the window into one list, then:
      MAD = median(|lat - median(pooled)|)
    0.0 for empty store or all calls outside window.
    Injectable store.  Pure function.

    Fleet dual of get_windowed_tool_latency_mad_ms (item 1032).
    NOT an average of per-tool MADs — pooling first gives a different (correct)
    fleet-level spread measure.

    PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[100]
      pooled=[10,20,30,100], median=25.0,
      sorted_devs=[5,5,15,75], MAD=(5+15)/2=10.0
      (kills per_tool_avg=(10+0)/2=5.0; kills mean_abs_dev=25.0; correct=10.0).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n == 0:
        return 0.0
    lats = sorted(all_lats)
    # compute median of pooled latencies
    mid = n // 2
    med = lats[mid] if n % 2 == 1 else (lats[mid - 1] + lats[mid]) / 2.0
    # compute median of absolute deviations
    devs = sorted(abs(lat - med) for lat in lats)
    mid2 = n // 2
    mad = devs[mid2] if n % 2 == 1 else (devs[mid2 - 1] + devs[mid2]) / 2.0
    return float(mad)


def get_windowed_tool_latency_entropy_bits(
    tool_name: str,
    window_ms: float,
    n_bins: int = 10,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Shannon entropy of the per-tool latency distribution in the window.  Item 1050.

    Bins latency values into n_bins equal-width buckets over [min, max].
    H = -sum(p * log2(p)) over non-empty bins (bits).
    Returns 0.0 when fewer than 2 samples in window or all samples are equal.
    Injectable store.  Pure function.

    HIGH entropy = spread or multi-modal distribution.
    LOW entropy = concentrated/deterministic latency profile.

    PRIMARY DISC. (all-equal): [50]*8 -> H=0.0
      (kills H=log2(8)=3.0 uniform-8 assumption; correct H=0.0).
    PRIMARY DISC. (uniform 5-bin): [10,20,30,40,50] n_bins=5 -> H=log2(5)≈2.322
      (kills H=0.0; kills H=log2(10)≈3.32 wrong-bins; correct H=log2(5)≈2.322).
    """
    import math as _math

    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n < 2:
        return 0.0
    lo = min(lats)
    hi = max(lats)
    if hi == lo:
        return 0.0
    width = (hi - lo) / n_bins
    bins: list[int] = [0] * n_bins
    for lat in lats:
        idx = int((lat - lo) / width)
        if idx >= n_bins:
            idx = n_bins - 1
        bins[idx] += 1
    h = 0.0
    for b in bins:
        if b > 0:
            p = b / n
            h -= p * _math.log2(p)
    return float(h)


def get_windowed_global_latency_entropy_bits(
    window_ms: float,
    n_bins: int = 10,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide Shannon entropy of pooled latency distribution (bits).  Item 1051.

    Pools ALL tool latencies in window into one list, then bins into n_bins
    equal-width buckets over [min, max].
    H = -sum(p * log2(p)) over non-empty bins.
    Returns 0.0 when fewer than 2 pooled samples or all samples are equal.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1050.

    PRIMARY DISC.: tool_a=[10,10] + tool_b=[100,100]
      pooled [10,10,100,100] n=4, n_bins=2
      bin[0]={10,10} p=0.5, bin[1]={100,100} p=0.5 -> H=1.0 bit
      (kills per-tool entropy avg: each all-equal -> H=0.0 each -> avg=0.0;
       kills H=0.0 single-bin assumption; correct pooled H=1.0 bit).
    """
    import math as _math

    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    all_lats: list[float] = []
    for records in store.values():
        all_lats.extend(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(all_lats)
    if n < 2:
        return 0.0
    lo = min(all_lats)
    hi = max(all_lats)
    if hi == lo:
        return 0.0
    width = (hi - lo) / n_bins
    bins: list[int] = [0] * n_bins
    for lat in all_lats:
        idx = int((lat - lo) / width)
        if idx >= n_bins:
            idx = n_bins - 1
        bins[idx] += 1
    h = 0.0
    for b in bins:
        if b > 0:
            p = b / n
            h -= p * _math.log2(p)
    return float(h)


def get_windowed_tool_bimodality_coefficient(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Bimodality coefficient (BC) of per-tool latency distribution.  Item 1052.

    BC = (skewness^2 + 1) / kurtosis_raw
    where kurtosis_raw = kurtosis_excess + 3 = sum((x-mean)^4) / (n * std^4).
    BC > 5/9 ≈ 0.556 suggests a bimodal distribution.
    Returns 0.0 when n < 4 or std == 0.
    Injectable store.  Pure function.

    PRIMARY DISC.: uniform [10,20,...,100] n=10
      skewness=0, kurtosis_raw≈1.7758, BC=(0+1)/1.7758≈0.563 > 5/9
      (flat/uniform data triggers bimodal test;
       kills BC=0.0 (zero-for-non-bimodal assumption);
       kills BC=1.0 (maximum bimodal assumption)).
    """
    import math as _math

    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n < 4:
        return 0.0
    mean = sum(lats) / n
    variance = sum((x - mean) ** 2 for x in lats) / n
    if variance == 0.0:
        return 0.0
    std = _math.sqrt(variance)
    skewness = sum((x - mean) ** 3 for x in lats) / (n * std ** 3)
    kurtosis_raw = sum((x - mean) ** 4 for x in lats) / (n * std ** 4)
    return float((skewness ** 2 + 1.0) / kurtosis_raw)


def get_windowed_tool_latency_gini_coefficient(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool Gini coefficient of latency distribution.  Item 1058.

    Gini in [0,1]; 0.0 for n<2 or all-equal (sum==0).
    Formula: G = (2*sum(i*x_i) - (n+1)*sum(x_i)) / (n*sum(x_i))
      where x_i are sorted latencies (1-indexed).
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,50] n=5
      sorted_sum=150, sum(i*x_i)=550
      G=(2*550-6*150)/(5*150)=200/750=4/15≈0.2667
      (kills CV=std/mean≈0.471; kills G=0 (wrong for non-equal); correct=4/15).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(lats)
    if n < 2:
        return 0.0
    total = sum(lats)
    if total == 0.0:
        return 0.0
    ranked_sum = sum((i + 1) * x for i, x in enumerate(lats))
    return float((2 * ranked_sum - (n + 1) * total) / (n * total))


def get_windowed_tool_latency_coefficient_of_quartile_variation(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Coefficient of Quartile Variation (CQV) of per-tool latency.  Item 1053.

    CQV = (Q3 - Q1) / (Q3 + Q1) — robust relative spread measure.
    Returns 0.0 when Q3 + Q1 == 0 or fewer than 4 samples in window.
    Uses linear interpolation for Q1/Q3 (same as get_windowed_latency_percentile).
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,50] n=5
      Q1=20.0 (idx=0.25*4=1.0, exact), Q3=40.0 (idx=0.75*4=3.0, exact)
      CQV=(40-20)/(40+20)=20/60=1/3≈0.3333
      (kills CV=stddev/mean≈0.526 -- wrong formula;
       kills range/(max+min)=40/60≈0.667 -- range-based not quartile;
       correct CQV=(Q3-Q1)/(Q3+Q1)=1/3).
    """
    _store = store if store is not None else _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = _store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    if len(lats) < 4:
        return 0.0
    q1 = get_windowed_latency_percentile(tool_name, 25.0, window_ms, store=store, now_ms=now_ms)
    q3 = get_windowed_latency_percentile(tool_name, 75.0, window_ms, store=store, now_ms=now_ms)
    denom = q3 + q1
    if denom == 0.0:
        return 0.0
    return float((q3 - q1) / denom)


def get_windowed_tool_latency_robust_cv(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool robust coefficient of variation = IQR / median.  Item 1061.

    Outlier-resistant relative spread (unlike CV = std/mean which is sensitive
    to extreme latency outliers).
    Returns 0.0 for n < 4 or median == 0.
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,10000] n=5
      Q1=20, Q3=40, IQR=20, median=30
      robust_CV=20/30=2/3≈0.6667
      (kills CV=std/mean≈1.975 because outlier 10000 inflates std/mean dramatically;
       robust_CV unchanged by outlier; correct=2/3).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = sorted(lat for ts, lat, _ok in records if ts >= cutoff_ms)
    n = len(lats)
    if n < 4:
        return 0.0
    # Median via linear interpolation (consistent with other percentile functions)
    med = get_windowed_latency_percentile(tool_name, 50.0, window_ms, store=store, now_ms=now_ms)
    if med == 0.0:
        return 0.0
    q1 = get_windowed_latency_percentile(tool_name, 25.0, window_ms, store=store, now_ms=now_ms)
    q3 = get_windowed_latency_percentile(tool_name, 75.0, window_ms, store=store, now_ms=now_ms)
    return float((q3 - q1) / med)


def get_windowed_tool_latency_z_score_max(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool maximum z-score = (max_lat - mean) / std.  Item 1063.

    Measures worst-case outlier severity in standard deviation units.
    Returns 0.0 for n < 2 or std == 0.
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,200] n=5
      mean=60, std=70.7107
      z_max=(200-60)/70.7107≈1.9799
      (kills max/mean≈3.33; kills (max-mean)/IQR≠1.9799; correct z_max≈1.9799).
    """
    import math as _math

    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n < 2:
        return 0.0
    mean = sum(lats) / n
    variance = sum((x - mean) ** 2 for x in lats) / n
    if variance == 0.0:
        return 0.0
    std = _math.sqrt(variance)
    return float((max(lats) - mean) / std)


def get_windowed_tool_latency_tail_ratio_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool tail ratio = p99 / p50.  Item 1066.

    Thin composition: p99 / p50.
    Returns 0.0 for empty window or p50 == 0.
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,200] n=5
      p50=30.0, p99=193.6, tail_ratio=193.6/30≈6.4533
      (kills p99/mean≈3.227; kills p95/p50=5.6; correct p99/p50≈6.4533).
    """
    p50 = get_windowed_latency_percentile(tool_name, 50.0, window_ms, store=store, now_ms=now_ms)
    if p50 == 0.0:
        return 0.0
    p99 = get_windowed_latency_percentile(tool_name, 99.0, window_ms, store=store, now_ms=now_ms)
    return float(p99 / p50)


def get_windowed_tool_latency_percentile_at_budget_ms(
    tool_name: str,
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool fraction of windowed calls with latency <= budget_ms.  Item 1064.

    Empirical CDF evaluated at budget_ms.  Returns fraction in [0, 1].
    Returns 0.0 for empty window.
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,30,40,50,60,70,80,90,100] n=10, budget_ms=50
      count_within=5 (boundary-inclusive), fraction=5/10=0.5
      (kills boundary-exclusive count=4/10=0.4;
       kills sum-based≈0.273; correct=0.5).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    records = store.get(tool_name, [])
    lats = [lat for ts, lat, _ok in records if ts >= cutoff_ms]
    n = len(lats)
    if n == 0:
        return 0.0
    within = sum(1 for lat in lats if lat <= budget_ms)
    return float(within / n)


def get_windowed_global_latency_cqv(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide Coefficient of Quartile Variation (CQV) — pooled raw values.  Item 1054.

    CQV = (global_Q3 - global_Q1) / (global_Q3 + global_Q1).
    Returns 0.0 when denominator == 0 or fewer than 4 pooled samples.
    Uses get_windowed_global_latency_percentile for Q1/Q3 (linear interpolation).
    Injectable store.  Pure function.  Fleet dual of per-tool item 1053.

    PRIMARY DISC.: tool_a=[10,30] + tool_b=[70,90]
      pooled [10,30,70,90] n=4, Q1=25.0, Q3=75.0
      CQV=(75-25)/(75+25)=50/100=0.5
      (kills per-tool CQV avg=(0.5+0.125)/2=0.3125 -- NOT pooled;
       correct pooled CQV=0.5).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    n_pooled = sum(
        1 for records in store.values()
        for ts, _lat, _ok in records if ts >= cutoff_ms
    )
    if n_pooled < 4:
        return 0.0
    q1 = get_windowed_global_latency_percentile(25.0, window_ms, store=store, now_ms=now_ms)
    q3 = get_windowed_global_latency_percentile(75.0, window_ms, store=store, now_ms=now_ms)
    denom = q3 + q1
    if denom == 0.0:
        return 0.0
    return float((q3 - q1) / denom)


def get_windowed_tool_latency_decile_range_ms(
    tool_name: str,
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Per-tool D9-D1 inter-decile range (p90 - p10) in the window.  Item 1055.

    Thin composition: p90 - p10.
    Wider than IQR (p75-p25) but tighter than full range (max-min).
    Returns 0.0 for unknown/empty tool (both p10 and p90 return 0.0 then).
    Injectable store.  Pure function.

    PRIMARY DISC.: lats [10,20,...,100] n=10
      p10=19.0 (idx=0.9 -> 10+0.9*(20-10)=19.0),
      p90=91.0 (idx=8.1 -> 90+0.1*(100-90)=91.0),
      decile_range=91.0-19.0=72.0
      (kills IQR=45.0 -- narrower p75-p25;
       kills range=90 -- max-min too wide;
       correct D9-D1=72.0).
    """
    p10 = get_windowed_latency_percentile(tool_name, 10.0, window_ms, store=store, now_ms=now_ms)
    p90 = get_windowed_latency_percentile(tool_name, 90.0, window_ms, store=store, now_ms=now_ms)
    return float(p90 - p10)


def get_windowed_global_latency_decile_range_ms(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide D9-D1 (global_p90 - global_p10) inter-decile range.  Item 1056.

    Thin composition: global_p90 - global_p10.
    Pools ALL tool latencies before computing percentiles (NOT per-tool avg).
    Returns 0.0 for empty pool.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1055.

    PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[70,80,90,100]
      pooled [10,20,30,70,80,90,100] n=7
      p10=16.0 (idx=0.6 -> 10+0.6*10=16),
      p90=94.0 (idx=5.4 -> 90+0.4*10=94),
      D9-D1=94.0-16.0=78.0
      (kills per-tool D9-D1 avg≈22.1;
       kills range=max-min=90;
       correct pooled D9-D1=78.0).
    """
    p10 = get_windowed_global_latency_percentile(10.0, window_ms, store=store, now_ms=now_ms)
    p90 = get_windowed_global_latency_percentile(90.0, window_ms, store=store, now_ms=now_ms)
    return float(p90 - p10)


def get_windowed_global_latency_bimodality_coefficient(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide bimodality coefficient BC=(skewness^2+1)/kurtosis_raw.  Item 1057.

    Pools ALL tool latencies before computing BC (NOT per-tool then average).
    Returns 0.0 for n_pooled < 4 or variance == 0.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1052.

    PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100,100,100,100]
      pooled [10,10,10,10,100,100,100,100] n=8
      mean=55, var=2025, std=45, skewness=0 (symmetric bimodal),
      kurtosis_raw=1.0, BC=(0+1)/1.0=1.0
      (kills per-tool BC avg: each all-equal -> variance=0 -> BC=0, avg=0.0 != 1.0;
       correct pooled bimodal BC=1.0).
    """
    import math as _math

    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    lats: list[float] = []
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                lats.append(lat)
    n = len(lats)
    if n < 4:
        return 0.0
    mean = sum(lats) / n
    variance = sum((x - mean) ** 2 for x in lats) / n
    if variance == 0.0:
        return 0.0
    std = _math.sqrt(variance)
    skewness = sum((x - mean) ** 3 for x in lats) / (n * std ** 3)
    kurtosis_raw = sum((x - mean) ** 4 for x in lats) / (n * std ** 4)
    return float((skewness ** 2 + 1.0) / kurtosis_raw)


def get_windowed_global_latency_gini_coefficient(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide Gini coefficient (pooled).  Item 1059.

    Pools ALL tool latencies then applies the Gini formula on sorted values.
    G = (2*sum(i*x_i) - (n+1)*sum(x_i)) / (n*sum(x_i)), x_i sorted 1-indexed.
    Returns 0.0 for n_pooled < 2 or sum == 0.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1058.

    PRIMARY DISC.: tool_a=[10,10] + tool_b=[50,50]
      pooled sorted=[10,10,50,50] n=4, sum=120, ranked_sum=380
      G=(2*380-5*120)/(4*120)=160/480=1/3≈0.3333
      (kills per-tool Gini avg: each all-equal -> G=0, avg=0.0 != 1/3;
       correct pooled Gini=1/3).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    global_lats: list[float] = []
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                global_lats.append(lat)
    global_lats.sort()
    n_g = len(global_lats)
    if n_g < 2:
        return 0.0
    total_g = sum(global_lats)
    if total_g == 0.0:
        return 0.0
    ranked_sum_g = sum((i + 1) * x for i, x in enumerate(global_lats))
    return float((2 * ranked_sum_g - (n_g + 1) * total_g) / (n_g * total_g))


def get_windowed_global_latency_robust_cv(
    window_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide robust coefficient of variation = pooled_IQR / pooled_median.  Item 1062.

    Pools ALL tool latencies before computing IQR and median.
    Returns 0.0 for n_pooled < 4 or pooled_median == 0.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1061.

    PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[90,90,90,90]
      pooled n=8, Q1=10, Q3=90, IQR=80, median=50
      robust_CV=80/50=1.6
      (kills per-tool robust_CV avg: each all-same -> IQR=0 -> 0.0, avg=0 != 1.6;
       correct pooled robust_CV=1.6).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    fleet_lats: list[float] = []
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                fleet_lats.append(lat)
    n_f = len(fleet_lats)
    if n_f < 4:
        return 0.0
    fleet_lats.sort()
    # Linear interpolation for Q1, Q3, median
    def _interp(arr: list[float], pct: float) -> float:
        n = len(arr)
        idx = (pct / 100.0) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return arr[lo] + (idx - lo) * (arr[hi] - arr[lo])

    med_f = _interp(fleet_lats, 50.0)
    if med_f == 0.0:
        return 0.0
    q1_f = _interp(fleet_lats, 25.0)
    q3_f = _interp(fleet_lats, 75.0)
    return float((q3_f - q1_f) / med_f)


def get_windowed_global_latency_percentile_at_budget_ms(
    window_ms: float,
    budget_ms: float,
    *,
    store: dict | None = None,
    now_ms: float | None = None,
) -> float:
    """Fleet-wide fraction of calls with latency <= budget_ms.  Item 1065.

    Pools ALL tool calls then computes the empirical CDF at budget_ms.
    Returns fraction in [0, 1]; 0.0 for empty pool.
    Injectable store.  Pure function.  Fleet dual of per-tool item 1064.

    PRIMARY DISC.: tool_a=[10,20,30,40] + tool_b=[90,100]
      pooled n=6, budget_ms=50 -> count_within=4, fraction=4/6=2/3≈0.6667
      (kills per-tool fraction avg: (1.0+0.0)/2=0.5 != pooled 2/3;
       correct pooled=4/6=2/3).
    """
    if store is None:
        store = _WINDOWED_TELEMETRY
    if now_ms is None:
        now_ms = _time.time() * 1000.0
    cutoff_ms = now_ms - window_ms
    total = 0
    within = 0
    for records in store.values():
        for ts, lat, _ok in records:
            if ts >= cutoff_ms:
                total += 1
                if lat <= budget_ms:
                    within += 1
    if total == 0:
        return 0.0
    return float(within / total)
