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
