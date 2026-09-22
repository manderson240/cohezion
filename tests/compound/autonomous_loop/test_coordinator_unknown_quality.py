"""PQ1 at the LoopCoordinator seam: an ABSENT quality is UNKNOWN, never 0.0.

Review 2026-09-22 (C4): results with no ``cascade_quality_score`` key -- ``act_error``,
``no_resident_model``, ``needs_oracle``, and the placeholder the coordinator itself fabricates
for a lost result -- fell through to ``elif not success: quality_score = 0.0`` and fed 0.0 plus
``success_rate 0.0`` into the DegradationDetector baseline. An instrument fault (git hook, router
down, no oracle) was scored as a model failure. No live inference: results are hand-built dicts.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)


def _task() -> LoopTask:
    return LoopTask("t1", "d", "bugfix", 1, "", 10)


def _record(result: dict) -> tuple[RunReport, MagicMock]:
    det = MagicMock()
    coord = LoopCoordinator(LoopConfig(), degradation_detector=det)
    report = RunReport()
    coord._record_result(result, _task(), False, 0, report, {}, {}, SprintResult())
    return report, det


@pytest.mark.parametrize("status", ["act_error", "no_resident_model", "needs_oracle"])
def test_absent_quality_is_unknown_not_zero(status):
    report, det = _record({"success": False, "status": status, "tokens_used": 0})
    assert report.results[-1]["quality_score"] is None
    sent = det.check_degradation.call_args.args[0]
    assert "quality_score" not in sent
    # the outcome says nothing about the model: no 0.0 success_rate stand-in either
    assert "success_rate" not in sent


def test_lost_result_placeholder_is_unknown(monkeypatch):
    """The coordinator's own fallback for a result the executor never returned."""
    det = MagicMock()
    local = MagicMock()
    local.execute_batch.return_value = []  # executor dropped the result
    import cohezion.compound.autonomous_loop.local_executor as le

    monkeypatch.setattr(le, "LocalImprovementExecutor", lambda *a, **k: local)
    coord = LoopCoordinator(
        LoopConfig(cloud_escalation_threshold=99, sprint_duration_seconds=1e9),
        degradation_detector=det,
    )
    monkeypatch.setattr(coord, "_consolidate_episodes", lambda _r: None)
    coord._backlog = [_task()]
    report = coord.run(executor=None)
    assert report.results[-1]["quality_score"] is None
    assert "success_rate" not in det.check_degradation.call_args.args[0]


def test_a_measured_failure_still_reports_its_measurement():
    """Discriminating pair: the fix must not blank a quality the producer DID measure."""
    report, det = _record(
        {"success": False, "status": "act_exhausted", "cascade_quality_score": 0.0}
    )
    assert report.results[-1]["quality_score"] == 0.0
    sent = det.check_degradation.call_args.args[0]
    assert sent["quality_score"] == 0.0 and sent["success_rate"] == 0.0
