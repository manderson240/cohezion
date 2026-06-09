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

import time as _time


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
