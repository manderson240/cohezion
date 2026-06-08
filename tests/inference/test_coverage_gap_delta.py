"""Discriminating tests for coverage_gap_delta (backlog item 94, 2026-06-08).

`coverage_gap_delta(before, after)` over two item-62 `coverage_gaps` sets tracks gap closure:
`filled` = gaps in before but NOT after (a $0 specialist got registered — progress); `opened` =
gaps new in after (a Task with queries but no specialist — regression). Report-only, pure over
injected `set[str]`.

Each test fails a plausible wrong impl:
  - an impl that reports every current gap (or the union) → test_gap_in_both_in_neither,
  - an impl that swaps the filled/opened directions → test_directions,
  - an impl that miscompares identical sets → test_identical_both_empty.
"""

from __future__ import annotations

from cohezion.inference.local_coverage import CoverageGapDelta, coverage_gap_delta


def test_directions() -> None:
    # 'ocr' gap was closed; 'vision' is a new gap.
    out = coverage_gap_delta({"ocr", "rerank"}, {"rerank", "vision"})
    assert out.filled == ["ocr"]  # in before, gone in after → a specialist landed
    assert out.opened == ["vision"]  # new in after → a fresh gap


def test_gap_in_both_in_neither() -> None:
    # DISCRIMINATING: a gap present in BOTH snapshots is unchanged — in NEITHER list. An impl that
    # reports every current gap (or the union) would wrongly include it.
    out = coverage_gap_delta({"rerank"}, {"rerank"})
    assert out.filled == [] and out.opened == []


def test_identical_both_empty() -> None:
    snap = {"ocr", "vision", "rerank"}
    out = coverage_gap_delta(snap, snap)
    assert out.filled == [] and out.opened == []


def test_all_filled() -> None:
    # every gap closed → all filled, none opened.
    out = coverage_gap_delta({"ocr", "vision"}, set())
    assert out.filled == ["ocr", "vision"]
    assert out.opened == []


def test_all_opened_from_empty() -> None:
    # gaps appearing from a clean slate → all opened.
    out = coverage_gap_delta(set(), {"vision", "ocr"})
    assert out.opened == ["ocr", "vision"]  # sorted
    assert out.filled == []


def test_returns_dataclass_and_sorted() -> None:
    out = coverage_gap_delta({"z", "a"}, {"a", "m", "b"})
    assert isinstance(out, CoverageGapDelta)
    assert out.filled == ["z"]  # only 'z' left (a stayed)
    assert out.opened == ["b", "m"]  # sorted, deterministic
