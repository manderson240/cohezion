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
