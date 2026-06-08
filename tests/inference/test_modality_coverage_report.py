"""Item 84: modality-coverage report (report-only, TDD red→green).

`modality_coverage_report(registry)` reports three-state coverage for each I/O modality:
  "covered"              — ≥1 verified ModelEntry for the modality's Task
  "registered_unverified"— ≥1 entry but none verified (binary impl collapses this to "covered")
  "gap"                  — no ModelEntry registered at all

Each test fails a plausible wrong impl:
  - collapses registered_unverified into "covered"         -> test_registered_unverified_is_distinct
  - treats any registered entry as "covered"               -> test_covered_requires_verified
  - non-empty registry for an absent task shows registered  -> test_empty_registry_all_gaps
  - all_gaps property misses a task                         -> test_gaps_all_five_when_empty_registry
"""

from __future__ import annotations

import copy

from cohezion.inference.registry import FleetRegistry, Task, get_registry
from cohezion.inference.specialist_coverage import (
    MODALITY_COVERED,
    MODALITY_GAP,
    MODALITY_REGISTERED_UNVERIFIED,
    ModalityCoverageReport,
    modality_coverage_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _isolated_registry() -> FleetRegistry:
    """Deep copy of the module singleton so mutations don't pollute other tests."""
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


def _empty_registry() -> FleetRegistry:
    return FleetRegistry(models={})


def _force_verified(reg: FleetRegistry, task: Task) -> None:
    """Set verified_working=True on the first registered candidate for task."""
    candidates = reg.for_task(task)
    if candidates:
        candidates[0].verified_working = True


def _force_all_unverified(reg: FleetRegistry, task: Task) -> None:
    """Set verified_working=False on ALL candidates for task."""
    for m in reg.for_task(task):
        m.verified_working = False


# ---------------------------------------------------------------------------
# Core three-state discrimination tests
# ---------------------------------------------------------------------------


class TestCovered:
    """A modality with ≥1 verified ModelEntry → 'covered'."""

    def test_covered_when_any_entry_verified(self) -> None:
        reg = _isolated_registry()
        _force_all_unverified(reg, Task.GENERAL)
        # Force at least one GENERAL entry verified → text should be "covered"
        _force_verified(reg, Task.GENERAL)
        report = modality_coverage_report(reg)
        text_row = next(r for r in report.rows if r.modality == "text")
        assert text_row.status == MODALITY_COVERED

    def test_covered_requires_verified(self) -> None:
        """DISCRIMINATOR: a registered-but-unverified entry is NOT 'covered'."""
        reg = _isolated_registry()
        _force_all_unverified(reg, Task.GENERAL)  # all text models → unverified
        report = modality_coverage_report(reg)
        text_row = next(r for r in report.rows if r.modality == "text")
        assert text_row.status != MODALITY_COVERED, (
            "registered-but-unverified models must NOT produce 'covered' status"
        )


class TestRegisteredUnverified:
    """MAIN DISCRIMINATOR: a modality with entries but none verified → registered_unverified."""

    def test_registered_unverified_is_distinct(self) -> None:
        """Registered-but-unverified is distinct from both 'covered' and 'gap'.

        A binary impl that collapses this into 'covered' or 'gap' fails this test.
        """
        reg = _isolated_registry()
        # Make ALL general-task models unverified to get "registered_unverified"
        _force_all_unverified(reg, Task.GENERAL)
        # Confirm at least one entry exists (otherwise it would be a gap)
        assert reg.for_task(Task.GENERAL), "registry must have ≥1 GENERAL model"
        report = modality_coverage_report(reg)
        text_row = next(r for r in report.rows if r.modality == "text")
        assert text_row.status == MODALITY_REGISTERED_UNVERIFIED, (
            f"registered-but-unverified must produce 'registered_unverified', not '{text_row.status}'"
        )

    def test_registered_unverified_not_in_gaps(self) -> None:
        """A registered-unverified modality is NOT in the gaps list."""
        reg = _isolated_registry()
        _force_all_unverified(reg, Task.GENERAL)
        report = modality_coverage_report(reg)
        assert "text" not in report.gaps


class TestGap:
    """A modality with no ModelEntry at all → 'gap'."""

    def test_image_out_gap_in_live_registry(self) -> None:
        """IMAGE_GEN has no registered model in the live registry (dep: item 83 registered none)."""
        reg = _isolated_registry()
        # If there are IMAGE_GEN entries, remove them to simulate a clean gap
        image_ids = [m.model_id for m in reg.for_task(Task.IMAGE_GEN)]
        for mid in image_ids:
            reg.models.pop(mid)
        report = modality_coverage_report(reg)
        image_row = next(r for r in report.rows if r.modality == "image_out")
        assert image_row.status == MODALITY_GAP
        assert image_row.model_ids == []

    def test_empty_registry_all_gaps(self) -> None:
        """An empty FleetRegistry produces 'gap' for ALL five modalities."""
        report = modality_coverage_report(_empty_registry())
        assert isinstance(report, ModalityCoverageReport)
        assert set(report.gaps) == {"text", "vision_in", "image_out", "audio_out", "video_out"}
        assert report.covered == []
        assert report.registered_unverified == []

    def test_gap_model_ids_empty(self) -> None:
        """A gap row has an empty model_ids list."""
        report = modality_coverage_report(_empty_registry())
        for row in report.rows:
            assert row.model_ids == [], f"{row.modality} gap row must have empty model_ids"


class TestGapsAllFiveWhenEmpty:
    """Structural test: all 5 modality names appear in output."""

    def test_gaps_all_five_when_empty_registry(self) -> None:
        """Empty registry must report exactly 5 rows, one per modality."""
        report = modality_coverage_report(_empty_registry())
        modality_names = {r.modality for r in report.rows}
        assert modality_names == {"text", "vision_in", "image_out", "audio_out", "video_out"}
        assert len(report.rows) == 5

    def test_five_rows_always_present(self) -> None:
        """Every call returns exactly 5 rows regardless of registry state."""
        report = modality_coverage_report(get_registry())
        assert len(report.rows) == 5


class TestEdgeCases:
    """Read-only and multi-entry checks."""

    def test_report_is_read_only(self) -> None:
        """Calling the function twice does not mutate the registry."""
        reg = _isolated_registry()
        before_verified = {mid: m.verified_working for mid, m in reg.models.items()}
        modality_coverage_report(reg)
        modality_coverage_report(reg)
        after_verified = {mid: m.verified_working for mid, m in reg.models.items()}
        assert after_verified == before_verified

    def test_covered_checks_all_candidates_not_just_top(self) -> None:
        """If the TOP priority model is unverified but a secondary is verified → 'covered'."""
        reg = _isolated_registry()
        general_candidates = reg.for_task(Task.GENERAL)
        if len(general_candidates) < 2:
            return  # not enough models to run this test; skip
        # Force the top-priority model unverified, a secondary verified
        general_candidates[0].verified_working = False
        general_candidates[1].verified_working = True
        report = modality_coverage_report(reg)
        text_row = next(r for r in report.rows if r.modality == "text")
        assert text_row.status == MODALITY_COVERED, (
            "any verified candidate (not just top-priority) should yield 'covered'"
        )
