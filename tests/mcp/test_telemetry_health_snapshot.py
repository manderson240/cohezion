"""Item 905: get_telemetry_health_snapshot() -- unified per-tool health dict.

Returns {tool: {latency_spike, error_spike, recent_p95, recent_error_rate}}
for every tool that has calls in the recent window.

PRIMARY DISC.:
  1. Tools with BOTH spikes -> latency_spike=True AND error_spike=True (not just one).
  2. Tools with NO spikes -> latency_spike=False AND error_spike=False.
  3. Empty store -> {} (not None or raised exception).
  4. recent_p95 and recent_error_rate come from actual recent data (not baseline).
  5. Tool with recent data but no baseline -> latency_spike=False, error_spike=False.
  6. Result values are bools for spike fields, floats for metric fields.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import get_telemetry_health_snapshot


def _build(
    tool: str,
    recent_lats: list[float],
    recent_successes: list[bool],
    baseline_lats: list[float] | None = None,
    baseline_successes: list[bool] | None = None,
    now_ms: float = 100_000.0,
    window_ms: float = 10_000.0,
    baseline_window_ms: float = 60_000.0,
) -> dict[str, list]:
    store: dict[str, list] = {tool: []}
    recent_ts = now_ms - window_ms + 1_000.0  # inside recent window
    for lat, ok in zip(recent_lats, recent_successes):
        store[tool].append((recent_ts, lat, ok))
    if baseline_lats is not None:
        baseline_ts = now_ms - window_ms - baseline_window_ms + 1_000.0
        bsuc = baseline_successes or [True] * len(baseline_lats)
        for lat, ok in zip(baseline_lats, bsuc):
            store[tool].append((baseline_ts, lat, ok))
    return store


def test_both_spikes_returns_both_true_primary_discriminator() -> None:
    """PRIMARY DISC.: tool with latency AND error spikes -> both True.
    Kills impl that returns False for one of the spikes, or uses wrong thresholds."""
    # latency spike: recent_p95=60ms vs baseline_p95=10ms -> ratio=6.0 > 2.0
    # error spike: recent_err=0.5 vs baseline_err=0.0 -> delta=0.5 > 0.2
    store = _build(
        "t1",
        recent_lats=[60.0] * 5,
        recent_successes=[True, True, False, False, False],  # err=0.6
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,  # err=0.0
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert "t1" in result, f"t1 must be present; got {list(result)}"
    r = result["t1"]
    assert r["latency_spike"] is True, f"latency_spike must be True; got {r}"
    assert r["error_spike"] is True, f"error_spike must be True; got {r}"


def test_no_spikes_returns_both_false() -> None:
    """Tool with no latency/error spikes -> both False."""
    # latency: recent=11ms vs baseline=10ms -> ratio=1.1 (below 2.0)
    # error: recent=0.0 vs baseline=0.0 -> delta=0.0 (below 0.2)
    store = _build(
        "t2",
        recent_lats=[11.0] * 5,
        recent_successes=[True] * 5,
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert "t2" in result
    r = result["t2"]
    assert r["latency_spike"] is False, f"latency_spike must be False; got {r}"
    assert r["error_spike"] is False, f"error_spike must be False; got {r}"


def test_empty_store_returns_empty_dict() -> None:
    """Empty store -> {}."""
    result = get_telemetry_health_snapshot(
        {}, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert result == {}, f"Empty store -> {{}}; got {result}"


def test_recent_p95_reflects_actual_recent_latencies() -> None:
    """recent_p95 must be computed from RECENT window data only, not baseline."""
    store = _build(
        "t3",
        recent_lats=[50.0] * 5,
        recent_successes=[True] * 5,
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    r = result.get("t3", {})
    assert abs(r.get("recent_p95", -1) - 50.0) < 1.0, (
        f"recent_p95 should be ~50ms (recent data); got {r}"
    )


def test_recent_error_rate_reflects_actual_recent_calls() -> None:
    """recent_error_rate must come from RECENT window calls, not baseline."""
    # 2 success + 2 fail in recent = 0.5 error rate; baseline all success
    store = _build(
        "t4",
        recent_lats=[10.0, 10.0, 10.0, 10.0],
        recent_successes=[True, True, False, False],
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    r = result.get("t4", {})
    assert abs(r.get("recent_error_rate", -1) - 0.5) < 0.01, (
        f"recent_error_rate should be 0.5; got {r}"
    )


def test_tool_with_only_recent_no_baseline_included_with_false_spikes() -> None:
    """Tool with recent data but no baseline -> present with spike=False (can't compute)."""
    store = _build(
        "t5",
        recent_lats=[50.0] * 5,
        recent_successes=[True] * 3 + [False] * 2,
        # no baseline
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert "t5" in result, "Tool with recent data should be present even without baseline"
    r = result["t5"]
    assert r["latency_spike"] is False
    assert r["error_spike"] is False


def test_result_has_required_keys() -> None:
    """Each tool dict must have exactly: latency_spike, error_spike, recent_p95, recent_error_rate."""
    store = _build(
        "t6",
        recent_lats=[10.0] * 3,
        recent_successes=[True] * 3,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert "t6" in result
    r = result["t6"]
    required = {"latency_spike", "error_spike", "recent_p95", "recent_error_rate"}
    missing = required - set(r.keys())
    assert not missing, f"Missing keys: {missing}; got {list(r.keys())}"


def test_spike_fields_are_bool_metric_fields_are_float() -> None:
    """latency_spike and error_spike must be bool; p95/error_rate must be float."""
    store = _build(
        "t7",
        recent_lats=[30.0] * 5,
        recent_successes=[True] * 5,
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    r = result["t7"]
    assert isinstance(r["latency_spike"], bool)
    assert isinstance(r["error_spike"], bool)
    assert isinstance(r["recent_p95"], float)
    assert isinstance(r["recent_error_rate"], float)


def test_tool_no_recent_calls_excluded() -> None:
    """Tool with no recent calls (all old data) is excluded from the snapshot."""
    store: dict[str, list] = {
        "old_tool": [(500.0, 20.0, True), (600.0, 25.0, False)],  # very old ts
    }
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    assert "old_tool" not in result, f"Old data only -> excluded; got {result}"


def test_latency_only_spike() -> None:
    """Tool with latency spike but no error spike -> latency_spike=True, error_spike=False."""
    # latency: recent=60ms vs baseline=10ms -> ratio=6.0 > 2.0 -> True
    # error: recent=0.0 vs baseline=0.0 -> delta=0.0 -> False
    store = _build(
        "t8",
        recent_lats=[60.0] * 5,
        recent_successes=[True] * 5,  # no errors
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    r = result.get("t8", {})
    assert r.get("latency_spike") is True
    assert r.get("error_spike") is False


def test_error_only_spike() -> None:
    """Tool with error spike but no latency spike -> latency_spike=False, error_spike=True."""
    # latency: recent=11ms vs baseline=10ms -> ratio=1.1 < 2.0 -> False
    # error: recent=0.8 vs baseline=0.0 -> delta=0.8 > 0.2 -> True
    store = _build(
        "t9",
        recent_lats=[11.0] * 5,
        recent_successes=[False, False, False, False, True],  # err=0.8
        baseline_lats=[10.0] * 5,
        baseline_successes=[True] * 5,  # err=0.0
    )
    result = get_telemetry_health_snapshot(
        store, window_ms=10_000.0, baseline_window_ms=60_000.0, now_ms=100_000.0
    )
    r = result.get("t9", {})
    assert r.get("latency_spike") is False
    assert r.get("error_spike") is True
