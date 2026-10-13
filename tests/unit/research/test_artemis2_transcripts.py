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


def _loop(rows):
    df = _df([(*r, "art002_2026-04-07_oe1_trn-csv_v01.csv") for r in rows])
    return df.with_columns(row=pl.int_range(pl.len()))


def test_loop_gaps_separates_cut_audio_from_kept_silence():
    df = _loop([
        ("10:00:00", "2026-04-07 10:00:00.000", "CAPCOM", "a"),
        ("10:40:00", "2026-04-07 10:40:00.000", "Koch", "40 min of kept silence"),
        ("10:41:00", "2026-04-07 10:47:00.000", "CAPCOM", "6 min removed from the recording"),
        ("10:41:10", "2026-04-07", "Hansen", "in the blind, no time"),
    ])  # fmt: skip
    g = tr.loop_gaps(df)
    assert [c["removed_min"] for c in g["cuts"]] == [6.0]
    assert [q["silence_kept_min"] for q in g["silences_kept"]] == [40.0]
    assert [r["text"] for r in g["undated_rows"]] == ["in the blind, no time"]


def test_speakers_in_window_counts_only_loop_rows_in_range():
    df = _loop([
        ("02:26:00", "2026-04-07 02:26:00.000", "CAPCOM", "in"),
        ("02:27:00", "2026-04-07 02:27:00.000", "CAPCOM ", "in, trailing space"),
        ("03:00:00", "2026-04-07 03:00:00.000", "Wiseman", "out of range"),
    ])  # fmt: skip
    assert tr.speakers_in_window(df, "2026-04-07 02:25:30", "2026-04-07 02:39:00") == {"CAPCOM": 2}
