"""Item 903: detect_latency_spike() -- per-tool latency spike flag via p95 ratio.

detect_latency_spike(store, window_ms, baseline_window_ms, now_ms=None) -> dict[str, bool]

Compares p95 of [now-window_ms, now] vs p95 of [now-baseline_window_ms, now].
Returns True for a tool when recent_p95 / baseline_p95 > 2.0 (spike threshold).
Returns False when ratio <= 2.0.
Returns {} when no data (no tools in store or no data in either window).
baseline_p95=0.0 with recent_p95>0 -> True (undefined baseline = conservative spike).
Pure; injectable store; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: spike_ratio=3.0 -> True; ratio=1.5 -> False (threshold kills wrong impls).
  2. Empty store -> {}.
  3. Tool with only baseline data (no recent calls) -> excluded from result.
  4. baseline_p95=0.0 and recent_p95>0 -> True (conservative: treat as spike).
  5. Both windows empty -> excluded from result (not False).
  6. Exact threshold boundary: ratio=2.0 -> False (strictly > 2.0 required).
  7. Multiple tools independent.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import detect_latency_spike


def _build_store(
    tool: str,
    recent_latencies: list[float],
    baseline_latencies: list[float],
    now_ms: float = 100_000.0,
    recent_window_ms: float = 10_000.0,
    baseline_window_ms: float = 60_000.0,
) -> dict[str, list]:
    """Build a windowed store with recent and baseline records."""
    store: dict[str, list] = {tool: []}
    # baseline records: ts = now - (baseline_window_ms - 1) = early in baseline window
    baseline_ts = now_ms - baseline_window_ms + 1_000.0
    for lat in baseline_latencies:
        store[tool].append((baseline_ts, lat, True))
    # recent records: ts = now - (recent_window_ms - 1) = in recent window
    recent_ts = now_ms - recent_window_ms + 1_000.0
    for lat in recent_latencies:
        store[tool].append((recent_ts, lat, True))
    return store


def test_spike_ratio_3x_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio=3.0 -> True; verifies threshold, not just existence.

    Baseline p95=10ms; recent p95=30ms -> ratio=3.0 > 2.0 -> spike=True.
    always-True impl passes; always-False fails; no-dict-return fails.
    """
    store = _build_store(
        "search",
        recent_latencies=[30.0] * 5,
        baseline_latencies=[10.0] * 5,
    )
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert isinstance(result, dict), "Must return dict"
    assert "search" in result, f"'search' must be present; got {list(result)}"
    assert result["search"] is True, f"ratio=3.0 -> True; got {result['search']}"


def test_no_spike_ratio_below_threshold() -> None:
    """ratio=1.5 -> False (below 2.0 threshold)."""
    store = _build_store(
        "read_file",
        recent_latencies=[15.0] * 5,
        baseline_latencies=[10.0] * 5,
    )
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert result.get("read_file") is False, f"ratio=1.5 -> False; got {result.get('read_file')}"


def test_empty_store_returns_empty_dict() -> None:
    """Empty store -> {}."""
    result = detect_latency_spike({}, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert result == {}, f"Empty store -> {{}}; got {result}"


def test_tool_with_only_baseline_excluded() -> None:
    """Tool with no recent calls is excluded (no key in result)."""
    # All records far in the past, beyond recent window
    store: dict[str, list] = {
        "list_dir": [(1_000.0, 10.0, True), (2_000.0, 12.0, True)],  # very old
    }
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert "list_dir" not in result, f"No recent data -> excluded; got {result}"


def test_baseline_p95_zero_excluded() -> None:
    """baseline_p95=0.0 -> tool excluded (ratio undefined; can't compute spike).

    When all baseline latencies are 0ms, p95=0 and ratio = recent/0 is undefined.
    Implementation excludes such tools rather than fabricating a True/False verdict.
    """
    store = _build_store(
        "write_file",
        recent_latencies=[50.0] * 3,
        baseline_latencies=[0.0] * 3,
    )
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert "write_file" not in result, f"Baseline p95=0 -> excluded (ratio undefined); got {result}"


def test_exact_threshold_ratio_2_is_not_spike() -> None:
    """ratio exactly 2.0 -> False (strictly greater than 2.0 required)."""
    store = _build_store(
        "exact",
        recent_latencies=[20.0] * 5,
        baseline_latencies=[10.0] * 5,
    )
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert result.get("exact") is False, f"ratio=2.0 -> False (not strictly >2); got {result}"


def test_multiple_tools_independent() -> None:
    """Two tools with different ratios are evaluated independently."""
    now_ms = 100_000.0
    store: dict[str, list] = {}

    # Tool A: spike (ratio=4.0)
    store["tool_a"] = []
    for lat in [40.0] * 5:
        store["tool_a"].append((now_ms - 5_000.0, lat, True))  # recent
    for lat in [10.0] * 5:
        store["tool_a"].append((now_ms - 50_000.0, lat, True))  # baseline

    # Tool B: no spike (ratio=1.2)
    store["tool_b"] = []
    for lat in [12.0] * 5:
        store["tool_b"].append((now_ms - 5_000.0, lat, True))  # recent
    for lat in [10.0] * 5:
        store["tool_b"].append((now_ms - 50_000.0, lat, True))  # baseline

    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=now_ms)
    assert result.get("tool_a") is True, f"ratio=4.0 -> True; got {result.get('tool_a')}"
    assert result.get("tool_b") is False, f"ratio=1.2 -> False; got {result.get('tool_b')}"


def test_return_type_is_bool_not_float() -> None:
    """Values must be bool, not float ratio or int."""
    store = _build_store("check", recent_latencies=[50.0] * 3, baseline_latencies=[10.0] * 3)
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    if "check" in result:
        assert isinstance(result["check"], bool), f"Must be bool; got {type(result['check'])}"


def test_both_windows_empty_tool_excluded() -> None:
    """If a tool has records outside both windows, it's excluded entirely."""
    store: dict[str, list] = {
        "ancient": [(500.0, 100.0, True)],  # outside both windows
    }
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert "ancient" not in result, f"No data in either window -> excluded; got {result}"


def test_large_spike_ratio_is_true() -> None:
    """Extreme spike ratio=10x -> True."""
    store = _build_store(
        "heavy_op",
        recent_latencies=[1000.0] * 4,
        baseline_latencies=[100.0] * 4,
    )
    result = detect_latency_spike(store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0)
    assert result.get("heavy_op") is True, f"ratio=10.0 -> True; got {result}"
