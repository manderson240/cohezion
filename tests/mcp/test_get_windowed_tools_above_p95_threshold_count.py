"""Item 1074: get_windowed_tools_above_p95_threshold_count(window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- count of tools whose windowed p95 latency exceeds threshold_ms.

Operational SLO-violation headcount. 0 for empty store or all tools within SLO.
Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,20,30,40,50] (p95=48.0), tool_b=[100,200,300,400,500] (p95=480.0),
               tool_c=[5,10,15,20,25] (p95=24.0); threshold=50ms
  -> count=1 (only tool_b exceeds threshold)
  (PRIMARY DISC.: kills per-call-count: counting calls>50ms != counting tools above SLO;
   kills count=0 (wrong -- tool_b p95=480>>50);
   correct SLO-violation tool-headcount=1).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tools_above_p95_threshold_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_slo_count_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, threshold=50ms -> only tool_b (p95=480) violates -> count=1.

    Kills per-call-count (different semantics).
    Kills count=0 (misses tool_b p95=480>>50).
    Correct: tool-level SLO-headcount=1.
    """
    _reset()
    store = _make_store(
        {
            "slo_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],  # p95=48.0
            "slo_b": [(_NOW - 10, float(v), True) for v in [100, 200, 300, 400, 500]],  # p95=480.0
            "slo_c": [(_NOW - 10, float(v), True) for v in [5, 10, 15, 20, 25]],  # p95=24.0
        }
    )
    result = get_windowed_tools_above_p95_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1, (
        f"threshold=50: only tool_b p95=480 violates; kills per-call-count; got {result}"
    )


def test_slo_count_all_within_threshold_returns_zero() -> None:
    """All tools well within threshold -> count=0."""
    _reset()
    store = _make_store(
        {
            "slo_ok_a": [(_NOW - 10, 10.0, True)] * 5,
            "slo_ok_b": [(_NOW - 10, 20.0, True)] * 5,
        }
    )
    result = get_windowed_tools_above_p95_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0, f"all within threshold -> count=0; got {result}"


def test_slo_count_all_violate_threshold() -> None:
    """All tools exceed threshold -> count=all tools."""
    _reset()
    store = _make_store(
        {
            "slo_viol_a": [(_NOW - 10, 200.0, True)] * 5,
            "slo_viol_b": [(_NOW - 10, 300.0, True)] * 5,
            "slo_viol_c": [(_NOW - 10, 400.0, True)] * 5,
        }
    )
    result = get_windowed_tools_above_p95_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 3, f"all 3 tools violate -> count=3; got {result}"


def test_slo_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    assert get_windowed_tools_above_p95_threshold_count(_WIN, 100.0, store={}, now_ms=_NOW) == 0


def test_slo_count_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "slo_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
        }
    )
    assert get_windowed_tools_above_p95_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW) == 0


def test_slo_count_boundary_exclusive() -> None:
    """p95 == threshold exactly -> does NOT exceed (strictly greater), count=0."""
    _reset()
    # [10,20,30,40,50] -> p95=48.0; threshold=48.0 -> NOT exceeded (48 is not > 48)
    store = _make_store(
        {
            "slo_bound": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tools_above_p95_threshold_count(_WIN, 48.0, store=store, now_ms=_NOW)
    assert result == 0, f"p95==threshold: boundary-exclusive -> count=0; got {result}"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({"slo_rt": [(_NOW - 10, 50.0, True)] * 5})
    assert isinstance(
        get_windowed_tools_above_p95_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW), int
    )
