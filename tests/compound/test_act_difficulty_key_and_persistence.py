"""ACT outcomes must land where a predict_tier caller can read them, and survive a restart.

Review 2026-09-22 (C10): LoopCoordinator recorded ACT outcomes under the fixed skill
"act_loop", which no predict_tier caller queries, and DifficultyEstimator history was not part
of SkillRefiner's durable spine (to_dict/save_state), so every record died at process exit.
Now a LoopTask may name its ``skill``; outcomes are keyed (skill, category), which is exactly
the (skill_name, operation_type) CompoundExecutor.execute_task hands predict_tier. No inference.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)
from cohezion.compound.difficulty_estimator import DifficultyEstimator
from cohezion.compound.skill_refiner import SkillRefiner


def _green(tier: str = "npu") -> dict:
    return {"success": True, "status": "committed", "cascade_quality_score": 1.0,
            "tier_used": tier, "elapsed_ms": 1000}


def _record_many(est: DifficultyEstimator, task: LoopTask, n: int = 4) -> None:
    coord = LoopCoordinator(LoopConfig(), degradation_detector=MagicMock(),
                            difficulty_estimator=est)
    for _ in range(n):
        coord._record_result(_green(), task, False, 0, RunReport(), {}, {}, SprintResult())


def test_act_outcome_is_readable_under_the_tasks_own_skill():
    est = DifficultyEstimator()
    task = LoopTask("t", "d", "bugfix", 1, "", 10, skill="research-actioner")
    assert est.predict_tier("research-actioner", "bugfix") == "unknown"
    _record_many(est, task)
    assert est.predict_tier("research-actioner", "bugfix") == "npu"


def test_difficulty_history_survives_save_and_restore(tmp_path):
    a = SkillRefiner()
    a._difficulty_estimator.record("sk", "op", "igpu", 0, 0.9, latency_s=1.0)
    a._difficulty_estimator.record("sk", "op", "igpu", 0, 0.8, latency_s=1.0)
    assert a._difficulty_estimator.predict_tier("sk", "op") == "igpu"
    path = tmp_path / "sr.json"
    a.save_state(path)

    b = SkillRefiner()
    assert b.restore_state(path)
    assert b._difficulty_estimator.predict_tier("sk", "op") == "igpu"
    c = SkillRefiner.from_dict(a.to_dict())
    assert c._difficulty_estimator.predict_tier("sk", "op") == "igpu"


def test_restore_keeps_the_window_bound():
    """A hand-edited or foreign state file with >10 rows must not unbound the window."""
    row = {"tier_used": "cpu", "escalation_count": 0, "quality_score": 0.9, "latency_s": 0.0}
    b = SkillRefiner.from_dict({"difficulty_history": {"sk::op": [row] * 30}})
    assert len(b._difficulty_estimator._history[("sk", "op")]) == 10
    b._difficulty_estimator.record("sk", "op", "cpu", 0, 0.9)
    assert len(b._difficulty_estimator._history[("sk", "op")]) == 10
