"""Item 1016: get_windowed_tool_first_call_ts(tool_name, window_ms, *, store=None, now_ms=None) -> float | None
-- timestamp of the oldest (first) call in the window.

Lowest ts_ms among records within window. None if no recent calls.
Injectable store. Pure function.

PRIMARY DISC.: records at ts [_NOW-40, _NOW-20, _NOW-10]
  -> first_ts = _NOW-40 (oldest/lowest)
  (kills last_ts=_NOW-10; kills None-when-records-exist; correct oldest ts).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_first_call_ts,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_first_call_ts_primary_discriminator() -> None:
    """PRIMARY DISC.: ts [_NOW-40, _NOW-20, _NOW-10] -> _NOW-40.

    Kills last_ts=_NOW-10.
    Kills mean_ts=_NOW-23.33.
    Kills None (records do exist).
    """
    _reset()
    store = _make_store({
        "fts_a": [
            (_NOW - 40, 10.0, True),
            (_NOW - 20, 20.0, True),
            (_NOW - 10, 30.0, True),
        ],
    })
    result = get_windowed_tool_first_call_ts("fts_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - (_NOW - 40)) < 1e-9, (
        f"oldest ts=_NOW-40={_NOW-40}; kills last_ts=_NOW-10; got {result}"
    )


def test_single_call_returns_its_ts() -> None:
    """Single call -> returns that call's timestamp."""
    _reset()
    store = _make_store({
        "fts_one": [(_NOW - 15, 10.0, True)],
    })
    result = get_windowed_tool_first_call_ts("fts_one", _WIN, store=store, now_ms=_NOW)
    assert result is not None
    assert abs(result - (_NOW - 15)) < 1e-9, f"single call -> ts=_NOW-15; got {result}"


def test_unknown_tool_returns_none() -> None:
    """Unknown tool -> None."""
    _reset()
    assert get_windowed_tool_first_call_ts("no_such_fts", _WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    _reset()
    store = _make_store({
        "fts_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
    })
    assert get_windowed_tool_first_call_ts("fts_old", _WIN, store=store, now_ms=_NOW) is None


def test_first_ts_le_last_ts() -> None:
    """first_ts <= last_ts for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_last_call_ts
    _reset()
    store = _make_store({
        "fts_ord": [
            (_NOW - 50, 10.0, True),
            (_NOW - 30, 20.0, True),
            (_NOW - 10, 30.0, True),
        ],
    })
    first = get_windowed_tool_first_call_ts("fts_ord", _WIN, store=store, now_ms=_NOW)
    last = get_windowed_tool_last_call_ts("fts_ord", _WIN, store=store, now_ms=_NOW)
    assert first is not None and last is not None
    assert first <= last, f"first_ts={first} must be <= last_ts={last}"


def test_uses_timestamp_not_list_order() -> None:
    """Returns lowest timestamp regardless of list insertion order."""
    _reset()
    store = _make_store({
        "fts_unordered": [
            (_NOW - 10, 10.0, True),   # stored first but NEWEST ts
            (_NOW - 50, 20.0, True),   # stored last but OLDEST ts
            (_NOW - 30, 30.0, True),
        ],
    })
    result = get_windowed_tool_first_call_ts("fts_unordered", _WIN, store=store, now_ms=_NOW)
    assert result is not None
    assert abs(result - (_NOW - 50)) < 1e-9, (
        f"oldest by ts=_NOW-50 regardless of list order; got {result}"
    )


def test_returns_float_not_int() -> None:
    """Return type for non-empty is float."""
    _reset()
    store = _make_store({"fts_rt": [(_NOW - 10, 10.0, True)]})
    result = get_windowed_tool_first_call_ts("fts_rt", _WIN, store=store, now_ms=_NOW)
    assert result is not None and isinstance(result, float)
