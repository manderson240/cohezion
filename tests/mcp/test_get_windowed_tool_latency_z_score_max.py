"""Item 1063: get_windowed_tool_latency_z_score_max(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool maximum z-score = (max_lat - mean) / std.

Measures how many standard deviations above the mean the worst observation sits.
0.0 for n<2 or std==0. Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,200] n=5
  mean=60, var=5000, std=70.7107
  z_max=(200-60)/70.7107=140/70.7107≈1.9799
  (PRIMARY DISC.: kills z_max=(max-mean)/IQR (wrong denominator -- IQR≠std);
   kills z_max=max/mean=200/60≈3.33 (not z-score formula);
   correct z_max=(max-mean)/std≈1.9799).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_z_score_max,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_z_score_max_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,200] -> z_max=(200-60)/70.7107≈1.9799.

    Kills z_max=max/mean=200/60≈3.33 (not z-score formula).
    Kills z_max=(max-mean)/IQR (wrong denominator).
    Correct: z_max=(max-mean)/std≈1.9799.
    """
    _reset()
    lats = [10, 20, 30, 40, 200]
    n = len(lats)
    mean = sum(lats) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in lats) / n)
    expected = (max(lats) - mean) / std
    store = _make_store(
        {
            "zsm_disc": [(_NOW - 10, float(v), True) for v in lats],
        }
    )
    result = get_windowed_tool_latency_z_score_max("zsm_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - expected) < 1e-9, (
        f"z_max={expected:.6f}; kills max/mean={max(lats) / mean:.4f}; got {result}"
    )


def test_z_score_max_all_equal_returns_zero() -> None:
    """All equal -> std=0 -> 0.0."""
    _reset()
    store = _make_store(
        {
            "zsm_eq": [(_NOW - 10, 50.0, True)] * 6,
        }
    )
    result = get_windowed_tool_latency_z_score_max("zsm_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> z_max=0.0; got {result}"


def test_z_score_max_single_sample_returns_zero() -> None:
    """n < 2 -> 0.0."""
    _reset()
    store = _make_store(
        {
            "zsm_one": [(_NOW - 10, 50.0, True)],
        }
    )
    assert get_windowed_tool_latency_z_score_max("zsm_one", _WIN, store=store, now_ms=_NOW) == 0.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_z_score_max("no_such_zsm", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "zsm_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert get_windowed_tool_latency_z_score_max("zsm_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_z_score_max_non_negative() -> None:
    """z_max >= 0 (max >= mean always for positive data)."""
    _reset()
    store = _make_store(
        {
            "zsm_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10, 300]],
        }
    )
    result = get_windowed_tool_latency_z_score_max("zsm_pos", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"z_max must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"zsm_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 100]]})
    assert isinstance(
        get_windowed_tool_latency_z_score_max("zsm_rt", _WIN, store=store, now_ms=_NOW), float
    )
