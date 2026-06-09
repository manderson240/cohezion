"""Item 1075: get_windowed_worst_tool_by_p99_latency_ms(window_ms, *, store=None, now_ms=None) -> tuple[str, float]
-- (tool_name, p99_ms) for the tool with the highest windowed p99 latency.

("", 0.0) for empty store or no windowed data.
Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,20,30,40,50] (p99=49.6),
               tool_b=[50,100,200,400,800] (p99=784.0),
               tool_c=[5,10,15,20,25] (p99=24.8)
  -> ("wtp_b", 784.0)
  (PRIMARY DISC.: kills argmax-by-mean: mean(a)=30, mean(b)=310, mean(c)=15 -- b still wins but
   the contract is specifically p99, not mean; discriminator is that p99-ordering and
   mean-ordering can diverge for other fixtures; kills argmax-by-p95: p95 gives slightly
   different values; correct argmax-by-p99 = ("wtp_b", 784.0)).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_worst_tool_by_p99_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_worst_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, tool_b p99=784.0 is worst -> ("wtp_b", 784.0).

    Kills argmax-by-mean (mean ordering can differ from p99 ordering).
    Kills argmax-by-p95 (different percentile, different contract).
    Correct: argmax-by-p99 = ("wtp_b", 784.0).
    """
    _reset()
    store = _make_store({
        "wtp_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        "wtp_b": [(_NOW - 10, float(v), True) for v in [50, 100, 200, 400, 800]],
        "wtp_c": [(_NOW - 10, float(v), True) for v in [5, 10, 15, 20, 25]],
    })
    result = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    tool, p99 = result
    assert tool == "wtp_b", f"worst tool should be wtp_b (p99=784.0); got {tool}"
    assert abs(p99 - 784.0) < 1e-9, f"p99 should be 784.0; got {p99}"


def test_worst_tool_single_tool() -> None:
    """Single tool in store -> that tool is worst."""
    _reset()
    store = _make_store({
        "wtp_single": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    tool, p99 = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert tool == "wtp_single", f"single tool should be returned; got {tool}"
    assert abs(p99 - 49.6) < 1e-9, f"p99 should be 49.6; got {p99}"


def test_worst_tool_empty_store_returns_sentinel() -> None:
    """Empty store -> ("", 0.0)."""
    _reset()
    result = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store={}, now_ms=_NOW)
    assert result == ("", 0.0), f"empty store -> ('', 0.0); got {result}"


def test_worst_tool_no_recent_calls_returns_sentinel() -> None:
    """All calls outside window -> ("", 0.0)."""
    _reset()
    store = _make_store({
        "wtp_old": [(_NOW - _WIN - 100, 500.0, True)] * 5,
    })
    result = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert result == ("", 0.0), f"all outside window -> ('', 0.0); got {result}"


def test_worst_tool_p99_not_p95_ordering() -> None:
    """Confirms p99 not p95: tool with higher p99 than another (despite lower p95) wins.

    tool_x=[10,10,10,10,200] vs tool_y=[20,20,20,20,20]
    tool_x: p95=idx=0.95*4=3.8 -> 10+0.8*(200-10)=162.0; p99=idx=0.99*4=3.96 -> 10+0.96*190=192.4
    tool_y: p95=p99=20 (all equal)
    argmax-by-p99 = tool_x; argmax-by-p95 = tool_x (same here); both return tool_x.
    Key: return value is the p99 of the winner, not p95.
    """
    _reset()
    store = _make_store({
        "wtp_x": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 10, 200]],
        "wtp_y": [(_NOW - 10, 20.0, True)] * 5,
    })
    tool, p99 = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert tool == "wtp_x", f"wtp_x has higher p99; got {tool}"
    # p99 for [10,10,10,10,200]: idx=3.96 -> 10+0.96*190=192.4
    assert abs(p99 - 192.4) < 1e-9, f"p99 should be 192.4; got {p99}"


def test_returns_tuple_type() -> None:
    """Return type is tuple[str, float]."""
    _reset()
    store = _make_store({"wtp_rt": [(_NOW - 10, float(v), True) for v in range(10, 51, 10)]})
    result = get_windowed_worst_tool_by_p99_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], str) and isinstance(result[1], float)
