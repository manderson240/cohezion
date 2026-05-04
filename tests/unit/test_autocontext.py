"""Tests for autocontext — context pressure monitor and experiment state compressor."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cohezion.research import autocontext


if TYPE_CHECKING:
    from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_entries(n: int, label: str = "exp_a", delta: float = 0.1) -> list[dict]:
    """Generate n fake autoresearch.jsonl entries."""
    entries = []
    base = datetime(2026, 5, 1, 0, 0, 0)
    for i in range(n):
        ts = (base + timedelta(minutes=i)).isoformat()
        entries.append(
            {
                "label": label,
                "cycle": i,
                "duration_s": 0.5,
                "keep": "keep" if i % 2 == 0 else "discard",
                "result": {"delta": delta},
                "ts": ts,
            }
        )
    return entries


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


# ── test 1: monitor returns correct shape ────────────────────────────────────


def test_monitor_returns_dict_with_pct():
    """monitor() returns a dict with all expected keys and correct types."""
    mock_result = MagicMock()
    mock_result.stdout = '{"percentage": 47.0, "status": "OK"}'

    with patch("subprocess.run", return_value=mock_result):
        ctx = autocontext.monitor()

    assert isinstance(ctx, dict), "monitor() must return a dict"
    assert "pct" in ctx
    assert "status" in ctx
    assert "safe" in ctx
    assert "warn" in ctx
    assert "critical" in ctx
    assert "monitor_ms" in ctx

    assert ctx["pct"] == pytest.approx(0.47, abs=0.001)
    assert ctx["status"] == "OK"
    assert ctx["safe"] is True
    assert ctx["warn"] is False
    assert ctx["critical"] is False
    assert isinstance(ctx["monitor_ms"], float)


def test_monitor_handles_subprocess_failure():
    """monitor() returns pct=0 and UNAVAILABLE when cz CLI is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError("cz not found")):
        ctx = autocontext.monitor()

    assert ctx["pct"] == 0.0
    assert ctx["status"] == "UNAVAILABLE"
    assert ctx["safe"] is True  # 0% is safe


# ── test 2: compress keeps recent entries verbatim ───────────────────────────


def test_compress_keeps_recent_entries(tmp_path: Path):
    """compress() keeps the last keep_recent entries unchanged."""
    jsonl = tmp_path / "session.jsonl"
    entries = _make_entries(300, label="exp_a")
    _write_jsonl(jsonl, entries)

    stats = autocontext.compress(jsonl, keep_recent=200)

    assert stats["kept"] == 200, f"Expected 200 kept, got {stats['kept']}"
    assert stats["compressed"] == 100

    result_entries = _read_jsonl(jsonl)
    # The last 200 original entries should appear at the end
    verbatim = [e for e in result_entries if not e.get("compressed")]
    assert len(verbatim) == 200, f"Expected 200 verbatim entries, got {len(verbatim)}"

    # Verify the verbatim entries match the last 200 originals
    for orig, kept in zip(entries[-200:], verbatim, strict=False):
        assert kept["cycle"] == orig["cycle"]
        assert kept["ts"] == orig["ts"]


# ── test 3: compress summarizes old entries ───────────────────────────────────


def test_compress_summarizes_old_entries(tmp_path: Path):
    """compress() collapses old entries into aggregate summary rows."""
    jsonl = tmp_path / "session.jsonl"

    # Mix two experiment labels
    entries_a = _make_entries(150, label="exp_a", delta=0.2)
    entries_b = _make_entries(150, label="exp_b", delta=0.5)
    # Interleave them (preserve time ordering for natural test)
    mixed: list[dict] = []
    for i in range(150):
        mixed.append(entries_a[i])
        mixed.append(entries_b[i])

    _write_jsonl(jsonl, mixed)  # 300 total entries

    stats = autocontext.compress(jsonl, keep_recent=100)

    assert stats["compressed"] == 200
    assert stats["summaries_emitted"] >= 1  # at least one summary per experiment label in old

    result_entries = _read_jsonl(jsonl)
    summaries = [e for e in result_entries if e.get("compressed") is True]

    assert len(summaries) >= 1, "Should have at least one summary row"

    # Summaries must have required aggregate fields
    for s in summaries:
        assert "experiment" in s
        assert "n" in s
        assert "keep_frac" in s
        assert "mean_delta" in s
        assert "max_delta" in s
        assert "first_ts" in s
        assert "last_ts" in s
        assert s["compressed"] is True
        assert s["n"] > 0


# ── test 4: budget thresholds ────────────────────────────────────────────────


def test_budget_thresholds():
    """budget() returns correct remaining_experiments at each tier boundary."""
    cases = [
        (0.0, 1000, True),  # < 50%
        (0.49, 1000, True),  # still below 50%
        (0.50, 200, True),  # at the 50% tier
        (0.60, 200, True),  # mid 50-80% tier
        (0.79, 200, True),  # top of 50-80%
        (0.80, 50, True),  # at the 80% tier
        (0.85, 50, True),  # mid 80-90%
        (0.89, 50, True),  # near top of 80-90%
        (0.90, 0, False),  # exactly 90% → 0
        (0.95, 0, False),  # > 90%
        (1.0, 0, False),  # full context
    ]

    for pct, expected_remaining, expected_safe in cases:
        ctx = {"pct": pct}
        result = autocontext.budget(ctx)
        assert result["remaining_experiments"] == expected_remaining, (
            f"pct={pct}: expected {expected_remaining}, got {result['remaining_experiments']}"
        )
        assert result["safe_to_continue"] == expected_safe, (
            f"pct={pct}: expected safe_to_continue={expected_safe}"
        )
        assert result["pct"] == pct


# ── test 5: archive moves old entries ────────────────────────────────────────


def test_archive_moves_old_entries(tmp_path: Path):
    """archive() moves entries older than max_age_hours to .archive file."""
    jsonl = tmp_path / "session.jsonl"
    archive_path = tmp_path / "session.jsonl.archive"

    now = datetime.now()
    old_ts = (now - timedelta(hours=3)).isoformat()  # 3h ago → should archive
    recent_ts = (now - timedelta(minutes=30)).isoformat()  # 30min ago → keep

    entries = [
        {"label": "exp_a", "cycle": 0, "keep": "keep", "result": {}, "ts": old_ts},
        {"label": "exp_a", "cycle": 1, "keep": "keep", "result": {}, "ts": old_ts},
        {"label": "exp_b", "cycle": 2, "keep": "discard", "result": {}, "ts": recent_ts},
        {"label": "exp_b", "cycle": 3, "keep": "keep", "result": {}, "ts": recent_ts},
    ]
    _write_jsonl(jsonl, entries)

    archived_count = autocontext.archive(jsonl, max_age_hours=2.0)

    assert archived_count == 2, f"Expected 2 archived, got {archived_count}"
    assert archive_path.exists(), ".archive file should have been created"

    archived = _read_jsonl(archive_path)
    assert len(archived) == 2

    remaining = _read_jsonl(jsonl)
    assert len(remaining) == 2
    assert all(e["ts"] == recent_ts for e in remaining)


def test_archive_nonexistent_file(tmp_path: Path):
    """archive() returns 0 when the JSONL file does not exist."""
    result = autocontext.archive(tmp_path / "missing.jsonl")
    assert result == 0


def test_compress_noop_when_below_threshold(tmp_path: Path):
    """compress() is a no-op when the file has fewer entries than keep_recent."""
    jsonl = tmp_path / "small.jsonl"
    entries = _make_entries(50, label="exp_a")
    _write_jsonl(jsonl, entries)

    stats = autocontext.compress(jsonl, keep_recent=200)

    assert stats["kept"] == 50
    assert stats["compressed"] == 0
    assert stats["summaries_emitted"] == 0
