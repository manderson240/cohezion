"""Discriminating tests for the specialist-coverage delta (item 57, 2026-06-06).

`specialist_coverage_delta(before, after)` over two item-38 SpecialistCoverageReports tracks the
specialist verification campaign over time (CB11 diff_snapshots / item-39 loop_progress_delta family):
{newly_registered, newly_verified, regressed}.

Each test fails a plausible wrong impl:
  - reports a delta for an identical pair → test_identical_empty,
  - an unverified→verified flip leaks into newly_registered too → test_newly_verified_only,
  - misses a verified→unverified regression → test_regressed,
  - a gap→registered isn't newly_registered, or an unchanged task appears → test_newly_registered/unchanged.
"""

from __future__ import annotations

from cohezion.inference.specialist_coverage import (
    SpecialistCoverage,
    SpecialistCoverageReport,
    specialist_coverage_delta,
)


def _report(rows: dict[str, tuple[str | None, bool]]) -> SpecialistCoverageReport:
    # rows: task -> (model_id_or_None, verified_working)
    return SpecialistCoverageReport(
        rows=[
            SpecialistCoverage(task=t, model_id=mid, verified_working=v)
            for t, (mid, v) in rows.items()
        ]
    )


def test_identical_empty() -> None:
    rep = _report({"rerank": ("M", False), "fim": ("N", True)})
    d = specialist_coverage_delta(rep, rep)
    assert d.newly_registered == [] and d.newly_verified == [] and d.regressed == []


def test_newly_verified_only() -> None:
    before = _report({"rerank": ("M", False)})
    after = _report({"rerank": ("M", True)})  # same model, flipped to verified
    d = specialist_coverage_delta(before, after)
    assert d.newly_verified == ["rerank"]
    assert (
        d.newly_registered == [] and d.regressed == []
    )  # model_id unchanged → not newly_registered


def test_regressed() -> None:
    before = _report({"rerank": ("M", True)})
    after = _report({"rerank": ("M", False)})  # lost verification
    d = specialist_coverage_delta(before, after)
    assert d.regressed == ["rerank"]
    assert d.newly_verified == [] and d.newly_registered == []


def test_newly_registered() -> None:
    before = _report({"ocr_doc": (None, False)})  # gap
    after = _report({"ocr_doc": ("GLM-OCR", False)})  # gained a model (still unverified)
    d = specialist_coverage_delta(before, after)
    assert d.newly_registered == ["ocr_doc"]
    assert d.newly_verified == [] and d.regressed == []


def test_unchanged_task_in_no_list() -> None:
    before = _report({"rerank": ("M", False), "fim": ("N", True)})
    after = _report({"rerank": ("M", True), "fim": ("N", True)})  # only rerank changed
    d = specialist_coverage_delta(before, after)
    assert d.newly_verified == ["rerank"]
    assert "fim" not in d.newly_verified + d.newly_registered + d.regressed
