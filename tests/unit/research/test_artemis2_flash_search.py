"""Offline tests for research/artemis2/flash_search_video.py (synthetic frames, no video)."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


_PATH = Path(__file__).resolve().parents[3] / "research" / "artemis2" / "flash_search_video.py"
_spec = importlib.util.spec_from_file_location("flash_search_video", _PATH)
fsv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fsv)

N, HP, WP = 60, 90, 160  # pooled frame size used by the detector


def _blank():
    rng = np.random.default_rng(1)
    frames = rng.integers(0, 4, size=(N, HP, WP)).astype(np.uint8)  # dark sky + compression noise
    frames[:, 20, 30] = 200  # a steady star
    return frames


def test_short_flash_is_detected_at_its_frame_and_place():
    frames = _blank()
    frames[30:33, 50, 70] = 120  # 3-frame (50 ms) point flash
    found, busy = fsv.transients(frames, offset=1000, thr=20)
    assert busy == []
    assert {(c["frame"], c["x"], c["y"]) for c in found} >= {(1030, 140, 100)}
    assert all(c["x"] == 140 and c["y"] == 100 for c in found)


def test_steady_star_and_noise_give_no_candidates():
    found, busy = fsv.transients(_blank(), offset=0, thr=20)
    assert found == []
    assert busy == []


def test_long_brightening_is_not_a_transient():
    frames = _blank()
    frames[10:55, 50, 70] = 120  # lasts ~0.75 s: Earthshine/slow change, not an impact flash
    found, _ = fsv.transients(frames, offset=0, thr=20)
    assert found == []


def test_global_change_is_logged_as_busy_not_as_flashes():
    frames = _blank()
    rng = np.random.default_rng(2)
    ys, xs = rng.integers(5, HP - 5, 40), rng.integers(5, WP - 5, 40)
    frames[30, ys, xs] = 150  # 40 scattered points in one frame: scene change / glitch
    found, busy = fsv.transients(frames, offset=0, thr=20)
    assert busy == [30]
    assert [c for c in found if c["frame"] == 30] == []


def test_cross_match_requires_both_channels():
    a = [{"frame": 100, "x": 200, "y": 300}, {"frame": 500, "x": 10, "y": 10}]
    b = [{"frame": 101, "x": 202, "y": 299}, {"frame": 900, "x": 10, "y": 10}]
    m = fsv.cross_match(a, b)
    assert len(m) == 1
    assert m[0]["ch1"]["frame"] == 100


def test_frame_time_round_trip():
    t = datetime(2026, 4, 7, 0, 45, tzinfo=UTC)
    assert abs((fsv.utc_at(fsv.frame_at(t)) - t).total_seconds()) < 1 / fsv.FPS


def test_triage_separates_rise_from_dark_and_flicker_of_existing_source():
    matched = [
        {"ch1": {"peak": 30, "excess": 26}},  # reference 4 DN: rose from dark
        {"ch1": {"peak": 140, "excess": 30}},  # reference 110 DN: a star flickering
    ]
    counts = fsv.triage(matched)
    assert counts == {"from_dark": 1, "existing_source_brightening": 1}
    assert [m["kind"] for m in matched] == ["from_dark", "existing_source_brightening"]
