"""Item 1005: get_windowed_global_slow_call_count(window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- fleet-wide count of calls with latency_ms > threshold_ms in window.

Fleet-wide dual of get_windowed_tool_slow_call_count (item 1003).
Pools ALL tools. 0 when empty. Strictly >. Returns int.

PRIMARY DISC.:
  tool_a lats [10, 200] + tool_b lats [300, 50] with threshold=100
  -> slow: tool_a.200>100 and tool_b.300>100 -> 2 (not per-tool max=1).
  Note: sum-of-per-tool also gives 2 in this case but from different tool distribution.
  Better disc fixture: unequal per-tool:
    tool_a lats [10, 200, 500] + tool_b lats [50] threshold=100
    -> tool_a slow=2, tool_b slow=0, total=2 (not per-tool-a-count=2 which is a coincidence).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_slow_call_count,
    get_windowed_tool_slow_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_slow_count_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a [10,200,500] + tool_b [50] threshold=100 -> 2.

    tool_a: 200>100 and 500>100 -> 2 slow
    tool_b: 50 not > 100         -> 0 slow
    total = 2

    Kills impl returning per-tool-a-max-count (which is 2 but by accident of fixture).
    Real discrim: fleet total = 2, but only from tool_a — both tools matter.
    """
    _reset()
    store = _make_store(
        {
            "gsc_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 200.0, True), (_NOW - 10, 500.0, True)],
            "gsc_b": [(_NOW - 10, 50.0, True)],
        }
    )
    result = get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2, f"tool_a 2 slow + tool_b 0 slow -> fleet 2; got {result}"


def test_cross_tool_counting() -> None:
    """Both tools contribute slow calls.

    tool_a [200] + tool_b [150] with threshold=100 -> 2 (1 from each).
    Kills impl counting only tool_a or only tool_b.
    """
    _reset()
    store = _make_store(
        {
            "gsc_cross_a": [(_NOW - 10, 200.0, True)],
            "gsc_cross_b": [(_NOW - 10, 150.0, True)],
        }
    )
    result = get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 2, f"tool_a slow=1 + tool_b slow=1 -> fleet=2; got {result}"


def test_single_tool_matches_per_tool() -> None:
    """With one tool, global count == per-tool count."""
    _reset()
    store = _make_store(
        {
            "gsc_one": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 300]],
        }
    )
    global_count = get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_slow_call_count("gsc_one", _WIN, 100.0, store=store, now_ms=_NOW)
    assert global_count == per_tool == 2, (
        f"single tool: global={global_count} must equal per_tool={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_slow_call_count(_WIN, 100.0, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "gsc_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
        }
    )
    assert get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW) == 0


def test_strictly_greater_than() -> None:
    """Latency exactly equal to threshold is NOT slow."""
    _reset()
    store = _make_store(
        {
            "gsc_exact": [(_NOW - 10, 100.0, True)] * 3 + [(_NOW - 10, 200.0, True)],
        }
    )
    result = get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 1, (
        f"3 calls at exactly 100ms (not slow) + 1 at 200ms (slow) -> 1; got {result}"
    )


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({"gsc_rt": [(_NOW - 10, 200.0, True)] * 3})
    assert isinstance(
        get_windowed_global_slow_call_count(_WIN, 100.0, store=store, now_ms=_NOW), int
    )
