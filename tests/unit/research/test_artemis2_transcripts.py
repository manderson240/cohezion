"""Offline tests for research/artemis2/transcripts.py (synthetic transcript rows)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl


_PATH = Path(__file__).resolve().parents[3] / "research" / "artemis2" / "transcripts.py"
_spec = importlib.util.spec_from_file_location("transcripts", _PATH)
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)


def _df(rows):
    return pl.DataFrame(rows, schema=["audio_time", "utc", "speaker", "text", "file"], orient="row")


def test_event_requires_verbatim_quote_at_that_time(monkeypatch):
    df = _df([
        ("00:00:01", "2026-04-07 00:51:57.628", "Hansen", "We saw an impact flash.", "a.csv"),
        ("00:00:02", "2026-04-07 00:52:10.000", "Hansen", "We saw an impact flash!", "b.csv"),
    ])  # fmt: skip
    monkeypatch.setattr(tr, "EVENTS", [
        ("2026-04-07 00:51:57", "We saw an impact flash.", "flash", "ok"),
        ("2026-04-07 00:52:10", "We saw an impact flash.", "flash", "wrong punctuation"),
        ("2026-04-07 00:59:00", "We saw an impact flash.", "flash", "wrong time"),
    ])  # fmt: skip
    found, missing = tr.verify_events(df)
    assert [e["label"] for e in found] == ["ok"]
    assert len(missing) == 2


def test_quality_counts_backwards_and_unparseable_timestamps():
    df = _df([
        ("0", "2026-04-07 00:00:10.000", "Wiseman ", "[[Inaudible]] hello", "a.csv"),
        ("1", "2026-04-07 00:00:05.000", "", "back in time", "a.csv"),
        ("2", "2026-04-06", "Koch", "date only", "a.csv"),
        ("0", "2026-04-07 00:00:01.000", "Koch", "other file starts earlier: not backwards", "b.csv"),
    ])  # fmt: skip
    q = tr.quality(df)
    assert q["timestamps_going_backwards"] == 1
    assert q["unparseable_utc"] == ["2026-04-06"]
    assert q["blank_speaker_rows"] == 1
    assert q["inaudible_markers"] == 1
    assert q["speakers_with_trailing_space"] == {"Wiseman ": 1}
