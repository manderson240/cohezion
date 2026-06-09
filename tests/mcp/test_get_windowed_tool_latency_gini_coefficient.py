"""Item 1058: get_windowed_tool_latency_gini_coefficient(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool Gini coefficient of latency distribution (inequality measure).

Gini in [0,1]. 0.0 for empty/all-equal or n<2.
Formula: G = (2*sum(i*x_i) - (n+1)*sum(x_i)) / (n*sum(x_i))
  where x_i are sorted latencies (1-indexed), sum(x_i) > 0.

PRIMARY DISC.: lats [10,20,30,40,50] sorted, n=5, sum=150
  sum(i*x_i) = 1*10+2*20+3*30+4*40+5*50 = 10+40+90+160+250 = 550
  G = (2*550 - 6*150) / (5*150) = (1100-900)/750 = 200/750 = 4/15 ≈ 0.2667
  (PRIMARY DISC.: kills CV=std/mean≈14.14/30≈0.471 (not Gini);
   kills G=0 (wrong zero for non-equal data);
   correct Gini=4/15≈0.2667).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_gini_coefficient,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> Gini=4/15≈0.2667.

    Kills CV=std/mean≈0.471 (different formula).
    Kills Gini=0 (wrong zero for non-equal data).
    Correct: G=(2*550-6*150)/(5*150)=200/750=4/15≈0.2667.
    """
    _reset()
    store = _make_store({
        "gini_disc": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_latency_gini_coefficient("gini_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 4 / 15) < 1e-9, (
        f"Gini=4/15≈0.2667; kills CV≈0.471; got {result}"
    )


def test_all_equal_gini_zero() -> None:
    """All equal -> Gini=0.0 (perfect equality)."""
    _reset()
    store = _make_store({
        "gini_eq": [(_NOW - 10, 50.0, True)] * 6,
    })
    result = get_windowed_tool_latency_gini_coefficient("gini_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> Gini=0.0; got {result}"


def test_single_sample_returns_zero() -> None:
    """n<2 -> 0.0."""
    _reset()
    store = _make_store({
        "gini_one": [(_NOW - 10, 50.0, True)],
    })
    assert get_windowed_tool_latency_gini_coefficient("gini_one", _WIN, store=store, now_ms=_NOW) == 0.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_gini_coefficient("no_such_gini", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gini_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_tool_latency_gini_coefficient("gini_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_gini_in_range_zero_to_one() -> None:
    """Gini in [0, 1] for any realistic input."""
    _reset()
    store = _make_store({
        "gini_range": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 1000, 5000]],
    })
    result = get_windowed_tool_latency_gini_coefficient("gini_range", _WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0, f"Gini must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gini_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40]]})
    assert isinstance(get_windowed_tool_latency_gini_coefficient("gini_rt", _WIN, store=store, now_ms=_NOW), float)
