"""Item 1017: get_windowed_tool_last_call_ts(tool_name, window_ms, *, store=None, now_ms=None) -> float | None
-- timestamp of the most-recent (last) call in the window.

Highest ts_ms among records within window. None if no recent calls.
Injectable store. Pure function. Dual of item-1016 (first_call_ts).

PRIMARY DISC.: records at ts [_NOW-40, _NOW-20, _NOW-10]
  -> last_ts = _NOW-10 (newest/highest)
  (kills first_ts=_NOW-40; kills mean-ts=_NOW-23; correct newest ts).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_last_call_ts,
    get_windowed_tool_first_call_ts,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_last_call_ts_primary_discriminator() -> None:
    """PRIMARY DISC.: ts [_NOW-40, _NOW-20, _NOW-10] -> _NOW-10.

    Kills first_ts=_NOW-40.
    Kills mean_ts=_NOW-23.33.
    Kills None (records do exist).
    """
    _reset()
    store = _make_store({
        "lts_a": [
            (_NOW - 40, 10.0, True),
            (_NOW - 20, 20.0, True),
            (_NOW - 10, 30.0, True),
        ],
    })
    result = get_windowed_tool_last_call_ts("lts_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - (_NOW - 10)) < 1e-9, (
        f"newest ts=_NOW-10={_NOW-10}; kills first_ts=_NOW-40; got {result}"
    )


def test_single_call_returns_its_ts() -> None:
    """Single call -> returns that call's timestamp."""
    _reset()
    store = _make_store({
        "lts_one": [(_NOW - 25, 10.0, True)],
    })
    result = get_windowed_tool_last_call_ts("lts_one", _WIN, store=store, now_ms=_NOW)
    assert result is not None
    assert abs(result - (_NOW - 25)) < 1e-9, f"single call -> ts=_NOW-25; got {result}"


def test_unknown_tool_returns_none() -> None:
    """Unknown tool -> None."""
    _reset()
    assert get_windowed_tool_last_call_ts("no_such_lts", _WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    _reset()
    store = _make_store({
        "lts_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
    })
    assert get_windowed_tool_last_call_ts("lts_old", _WIN, store=store, now_ms=_NOW) is None


def test_last_ts_ge_first_ts() -> None:
    """last_ts >= first_ts for any non-empty window (dual of first_call_ts test)."""
    _reset()
    store = _make_store({
        "lts_ord": [
            (_NOW - 50, 10.0, True),
            (_NOW - 30, 20.0, True),
            (_NOW - 10, 30.0, True),
        ],
    })
    first = get_windowed_tool_first_call_ts("lts_ord", _WIN, store=store, now_ms=_NOW)
    last = get_windowed_tool_last_call_ts("lts_ord", _WIN, store=store, now_ms=_NOW)
    assert first is not None and last is not None
    assert last >= first, f"last_ts={last} must be >= first_ts={first}"


def test_uses_highest_timestamp_not_list_order() -> None:
    """Returns highest timestamp regardless of list insertion order."""
    _reset()
    store = _make_store({
        "lts_unordered": [
            (_NOW - 50, 10.0, True),   # stored first but OLDEST ts
            (_NOW - 10, 20.0, True),   # stored second but NEWEST ts
            (_NOW - 30, 30.0, True),
        ],
    })
    result = get_windowed_tool_last_call_ts("lts_unordered", _WIN, store=store, now_ms=_NOW)
    assert result is not None
    assert abs(result - (_NOW - 10)) < 1e-9, (
        f"newest by ts=_NOW-10 regardless of list order; got {result}"
    )


def test_window_span_equals_last_minus_first() -> None:
    """Window span = last_ts - first_ts >= 0."""
    _reset()
    store = _make_store({
        "lts_span": [
            (_NOW - 40, 10.0, True),
            (_NOW - 20, 20.0, True),
            (_NOW - 5,  30.0, True),
        ],
    })
    first = get_windowed_tool_first_call_ts("lts_span", _WIN, store=store, now_ms=_NOW)
    last = get_windowed_tool_last_call_ts("lts_span", _WIN, store=store, now_ms=_NOW)
    assert first is not None and last is not None
    span = last - first
    assert abs(span - 35.0) < 1e-9, f"span=last-first=35.0; got {span}"


def test_returns_float_not_int() -> None:
    """Return type for non-empty is float."""
    _reset()
    store = _make_store({"lts_rt": [(_NOW - 10, 10.0, True)]})
    result = get_windowed_tool_last_call_ts("lts_rt", _WIN, store=store, now_ms=_NOW)
    assert result is not None and isinstance(result, float)
