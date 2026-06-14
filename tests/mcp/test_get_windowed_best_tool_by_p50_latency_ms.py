"""Item 1076: get_windowed_best_tool_by_p50_latency_ms(window_ms, *, store=None, now_ms=None) -> tuple[str, float]
-- (tool_name, p50_ms) for the tool with the LOWEST windowed p50 (most responsive).

("", 0.0) for empty store or no tool with windowed data.
Injectable store. Pure function. Complement of item 1075 (worst by p99).

PRIMARY DISC.: tool_a=[10,20,30,40,50] (p50=30.0),
               tool_b=[100,200,300] (p50=200.0),
               tool_c=[5,8,12] (p50=8.0)
  -> ("wbp_c", 8.0)
  (PRIMARY DISC.: kills argmax (inverted direction -- we want the MINIMUM p50, not maximum);
   kills argmin-by-mean: mean(c)≈8.33, mean(a)=30 -- c still wins but the contract is p50;
   correct argmin-by-p50 = ("wbp_c", 8.0)).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_best_tool_by_p50_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_best_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, tool_c p50=8.0 is best -> ("wbp_c", 8.0).

    Kills argmax (wrong direction -- worst instead of best).
    Kills argmin-by-mean (different metric).
    Correct: argmin-by-p50 = ("wbp_c", 8.0).
    """
    _reset()
    store = _make_store(
        {
            "wbp_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],  # p50=30.0
            "wbp_b": [(_NOW - 10, float(v), True) for v in [100, 200, 300]],  # p50=200.0
            "wbp_c": [(_NOW - 10, float(v), True) for v in [5, 8, 12]],  # p50=8.0
        }
    )
    result = get_windowed_best_tool_by_p50_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    tool, p50 = result
    assert tool == "wbp_c", f"best tool should be wbp_c (p50=8.0); got {tool}"
    assert abs(p50 - 8.0) < 1e-9, f"p50 should be 8.0; got {p50}"


def test_best_tool_single_tool() -> None:
    """Single tool in store -> that tool is best."""
    _reset()
    store = _make_store(
        {
            "wbp_single": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    tool, p50 = get_windowed_best_tool_by_p50_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert tool == "wbp_single", f"single tool returned; got {tool}"
    assert abs(p50 - 30.0) < 1e-9, f"p50=30.0; got {p50}"


def test_best_tool_empty_store_returns_sentinel() -> None:
    """Empty store -> ("", 0.0)."""
    _reset()
    result = get_windowed_best_tool_by_p50_latency_ms(_WIN, store={}, now_ms=_NOW)
    assert result == ("", 0.0), f"empty store -> ('', 0.0); got {result}"


def test_best_tool_no_recent_calls_returns_sentinel() -> None:
    """All calls outside window -> ("", 0.0)."""
    _reset()
    store = _make_store(
        {
            "wbp_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    result = get_windowed_best_tool_by_p50_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert result == ("", 0.0), f"all outside window -> ('', 0.0); got {result}"


def test_best_tool_direction_is_minimum() -> None:
    """Confirms direction is minimum: tool with lower p50 wins over one with higher p50."""
    _reset()
    store = _make_store(
        {
            "wbp_low": [(_NOW - 10, 5.0, True)] * 5,  # p50=5.0
            "wbp_high": [(_NOW - 10, 100.0, True)] * 5,  # p50=100.0
        }
    )
    tool, p50 = get_windowed_best_tool_by_p50_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert tool == "wbp_low", f"lower p50 wins; got {tool}"
    assert abs(p50 - 5.0) < 1e-9, f"p50=5.0; got {p50}"


def test_returns_tuple_type() -> None:
    """Return type is tuple[str, float]."""
    _reset()
    store = _make_store({"wbp_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30]]})
    result = get_windowed_best_tool_by_p50_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], str) and isinstance(result[1], float)
