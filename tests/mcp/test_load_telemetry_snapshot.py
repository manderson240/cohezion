"""Item 908: load_telemetry_snapshot(path) -- read persisted telemetry back.

PRIMARY DISC.: round-trip: persist then load returns original summary;
missing file raises FileNotFoundError (kills silent-{} impl);
malformed JSON raises ValueError (kills swallow-errors impl);
does NOT mutate _TELEMETRY (pure I/O boundary).
"""

from __future__ import annotations

import json
import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    record_tool_call,
    persist_telemetry_snapshot,
    load_telemetry_snapshot,
)


def _reset():
    _TELEMETRY.clear()


# ── primary discriminator ─────────────────────────────────────────────────────


def test_round_trip_primary_discriminator(tmp_path) -> None:
    """FALSIFIABLE: persist then load returns original summary dict.
    Kills impl that returns wrong structure or ignores the file content."""
    _reset()
    record_tool_call("rt_tool", 10.0, True)
    record_tool_call("rt_tool", 20.0, False)
    out = tmp_path / "round_trip.json"
    persist_telemetry_snapshot(out)
    loaded = load_telemetry_snapshot(out)
    assert "rt_tool" in loaded
    entry = loaded["rt_tool"]
    assert entry["call_count"] == 2
    assert abs(entry["error_rate"] - 0.5) < 0.01
    assert "p50_ms" in entry
    assert "p95_ms" in entry


def test_missing_file_raises_file_not_found(tmp_path) -> None:
    """Missing file must raise FileNotFoundError, not return {}."""
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        load_telemetry_snapshot(missing)


def test_malformed_json_raises_value_error(tmp_path) -> None:
    """Malformed JSON must raise ValueError (not return {} or raise JSONDecodeError directly)."""
    bad = tmp_path / "bad.json"
    bad.write_text("this is not JSON", encoding="utf-8")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        load_telemetry_snapshot(bad)


def test_load_does_not_mutate_telemetry_store(tmp_path) -> None:
    """load_telemetry_snapshot must NOT write into _TELEMETRY.
    Kills impl that calls record_tool_call or merges into the global store."""
    _reset()
    record_tool_call("orig_tool", 5.0, True)
    out = tmp_path / "iso.json"
    persist_telemetry_snapshot(out)
    _reset()  # clear global store
    load_telemetry_snapshot(out)
    # _TELEMETRY must still be empty after load
    assert _TELEMETRY == {}


def test_empty_json_file_returns_empty_dict(tmp_path) -> None:
    """A file containing {} loads as an empty dict, not raises."""
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    result = load_telemetry_snapshot(empty)
    assert result == {}


def test_accepts_str_path(tmp_path) -> None:
    """Must accept str path in addition to Path."""
    _reset()
    record_tool_call("str_tool", 15.0, True)
    out = tmp_path / "str.json"
    persist_telemetry_snapshot(out)
    result = load_telemetry_snapshot(str(out))
    assert "str_tool" in result


def test_returned_dict_is_new_object(tmp_path) -> None:
    """Returned dict must be independent — mutating it does not affect _TELEMETRY."""
    _reset()
    record_tool_call("new_obj_tool", 25.0, True)
    out = tmp_path / "newobj.json"
    persist_telemetry_snapshot(out)
    loaded = load_telemetry_snapshot(out)
    loaded["injected_key"] = "value"
    assert "injected_key" not in _TELEMETRY


def test_multiple_tools_round_trip(tmp_path) -> None:
    """All tools survive the round-trip."""
    _reset()
    record_tool_call("tool_x", 10.0, True)
    record_tool_call("tool_y", 20.0, True)
    record_tool_call("tool_y", 30.0, False)
    out = tmp_path / "multi_rt.json"
    persist_telemetry_snapshot(out)
    loaded = load_telemetry_snapshot(out)
    assert set(loaded.keys()) == {"tool_x", "tool_y"}
    assert loaded["tool_y"]["call_count"] == 2
