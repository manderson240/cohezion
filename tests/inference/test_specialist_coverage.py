"""Item 38: specialist verification-gap report (report-only).

`specialist_coverage_report(registry)` surfaces, for each of the 6 specialist Tasks
(EXTRACTION/VISION/FIM/FUNCTION_CALL/RERANK/OCR_DOC), the gap between REGISTERED
(additive, done items 4/19/21/23/28) and SERVING-VERIFIED (needs-experiment, 0/6 today).

Each test fails a plausible wrong impl:
  - treats an empty for_task() as a registered row (no gap) → test_missing_specialist_is_a_gap,
  - reads verified_working from the wrong place / ignores it → test_flipping_one_moves_it,
  - mutates the registry while reporting → test_report_is_read_only,
  - the all-6-registered milestone regressed → test_default_registry_registers_all_six.
"""

from __future__ import annotations

import copy

from cohezion.inference.registry import FleetRegistry, Task, get_registry
from cohezion.inference.specialist_coverage import (
    SPECIALIST_TASKS,
    specialist_coverage_report,
)


def _isolated_registry() -> FleetRegistry:
    # Deep copy so flipping verified_working never pollutes the module singleton.
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


def test_all_six_unverified_zero_in_verified_set() -> None:
    reg = _isolated_registry()
    for task in SPECIALIST_TASKS:
        for entry in reg.for_task(task):
            entry.verified_working = False
    report = specialist_coverage_report(reg)
    assert len(report.registered) == 6, "all 6 specialist slots should be registered"
    assert report.gaps == [], "no gaps when every specialist Task has a model"
    assert report.verified == [], "0 verified when every specialist is verified_working=False"
    assert len(report.unverified) == 6


def test_flipping_one_moves_it_to_verified_set() -> None:
    reg = _isolated_registry()
    for task in SPECIALIST_TASKS:
        for entry in reg.for_task(task):
            entry.verified_working = False
    # Flip exactly the RERANK specialist.
    rerank_id = reg.for_task(Task.RERANK)[0].model_id
    reg.mark_verified(rerank_id)

    report = specialist_coverage_report(reg)
    verified_tasks = {r.task for r in report.verified}
    assert verified_tasks == {str(Task.RERANK)}, "only the flipped specialist is verified"
    assert len(report.unverified) == 5


def test_missing_specialist_is_a_gap() -> None:
    reg = _isolated_registry()
    # Remove the OCR_DOC specialist entirely → that Task has no model.
    ocr_ids = [m.model_id for m in reg.for_task(Task.OCR_DOC)]
    for mid in ocr_ids:
        reg.models.pop(mid)

    report = specialist_coverage_report(reg)
    assert str(Task.OCR_DOC) in report.gaps
    gap_row = next(r for r in report.rows if r.task == str(Task.OCR_DOC))
    assert gap_row.model_id is None
    assert gap_row.verified_working is False
    # A gap is NOT counted as registered.
    assert all(r.model_id is not None for r in report.registered)


def test_report_is_read_only() -> None:
    reg = _isolated_registry()
    before_count = len(reg.models)
    before_verified = {mid: m.verified_working for mid, m in reg.models.items()}
    specialist_coverage_report(reg)
    specialist_coverage_report(reg)
    assert len(reg.models) == before_count, "report must not add/remove models"
    assert {mid: m.verified_working for mid, m in reg.models.items()} == before_verified


def test_default_registry_registers_all_six() -> None:
    # The live milestone: items 4/19/21/23/28 registered all 6 specialist slots.
    report = specialist_coverage_report(get_registry())
    assert report.gaps == [], f"specialist slots still empty: {report.gaps}"
    assert len(report.registered) == 6
