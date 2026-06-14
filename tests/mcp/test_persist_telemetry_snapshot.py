"""Item 907: persist_telemetry_snapshot(path) -- atomic JSON telemetry persistence.

PRIMARY DISC.: after recording calls, file at path has correct JSON structure
{tool: {call_count, error_rate, p50_ms, p95_ms}}; empty store writes {};
atomic write (no partial file); distinct from in-memory-only summary.
"""

from __future__ import annotations

import json
from pathlib import Path

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    record_tool_call,
    persist_telemetry_snapshot,
)


def _reset():
    _TELEMETRY.clear()


# ── primary discriminator ─────────────────────────────────────────────────────


def test_file_created_with_correct_structure_primary_discriminator(tmp_path) -> None:
    """FALSIFIABLE: after recording calls, file exists with {tool: {call_count,...}}.
    Kills impl that writes the wrong format or doesn't write at all."""
    _reset()
    record_tool_call("snap_tool", 50.0, True)
    record_tool_call("snap_tool", 80.0, False)
    out = tmp_path / "telemetry.json"
    persist_telemetry_snapshot(out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert "snap_tool" in data
    entry = data["snap_tool"]
    assert entry["call_count"] == 2
    assert abs(entry["error_rate"] - 0.5) < 0.01
    assert "p50_ms" in entry
    assert "p95_ms" in entry


def test_empty_store_writes_empty_json_object(tmp_path) -> None:
    """Empty store must write {} not [] or missing file."""
    _reset()
    out = tmp_path / "empty.json"
    persist_telemetry_snapshot(out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data == {}


def test_written_json_is_valid(tmp_path) -> None:
    """Output file must parse as valid JSON (not just text)."""
    _reset()
    record_tool_call("valid_json_tool", 10.0, True)
    out = tmp_path / "valid.json"
    persist_telemetry_snapshot(out)
    # Must not raise
    data = json.loads(out.read_text())
    assert isinstance(data, dict)


def test_atomic_write_no_partial_file(tmp_path) -> None:
    """Write must be atomic: the destination file appears only after write completes.
    Verified indirectly: no .tmp file lingers after persist_telemetry_snapshot."""
    _reset()
    record_tool_call("atomic_tool", 20.0, True)
    out = tmp_path / "atomic.json"
    persist_telemetry_snapshot(out)
    # No temp file should linger
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"Temp file leaked: {tmp_files}"
    assert out.exists()


def test_accepts_str_path(tmp_path) -> None:
    """Must accept str path in addition to Path (no AttributeError on str)."""
    _reset()
    record_tool_call("str_path_tool", 30.0, True)
    out_str = str(tmp_path / "str_path.json")
    persist_telemetry_snapshot(out_str)
    assert Path(out_str).exists()


def test_multiple_tools_all_written(tmp_path) -> None:
    """All recorded tools appear in the file."""
    _reset()
    record_tool_call("tool_a", 10.0, True)
    record_tool_call("tool_b", 20.0, False)
    record_tool_call("tool_b", 30.0, False)
    out = tmp_path / "multi.json"
    persist_telemetry_snapshot(out)
    data = json.loads(out.read_text())
    assert "tool_a" in data
    assert "tool_b" in data
    assert data["tool_b"]["call_count"] == 2
    assert abs(data["tool_b"]["error_rate"] - 1.0) < 0.01


def test_overwrites_existing_file(tmp_path) -> None:
    """Second call overwrites previous content — not appends."""
    _reset()
    record_tool_call("over_tool", 10.0, True)
    out = tmp_path / "overwrite.json"
    persist_telemetry_snapshot(out)
    _reset()
    persist_telemetry_snapshot(out)
    data = json.loads(out.read_text())
    assert data == {}  # store was reset; second write wins


def test_call_count_values_are_integers(tmp_path) -> None:
    """call_count must be int, not float, in the JSON."""
    _reset()
    record_tool_call("int_tool", 15.0, True)
    out = tmp_path / "ints.json"
    persist_telemetry_snapshot(out)
    data = json.loads(out.read_text())
    assert isinstance(data["int_tool"]["call_count"], int)
