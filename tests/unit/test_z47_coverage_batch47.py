"""Coverage batch Z47: constitutional_enforcer, adversarial_grounding, long_horizon_task, zvol_swap."""

from __future__ import annotations


import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: security/constitutional_enforcer.py
# ---------------------------------------------------------------------------


class TestConstitutionalEnforcer:
    def _make_enforcer(self):
        from cohezion.security.constitutional_enforcer import ConstitutionalEnforcer

        return ConstitutionalEnforcer()

    def test_safe_text_has_no_violations(self):
        enforcer = self._make_enforcer()
        assert enforcer.is_safe("run pytest tests/ -q") is True

    def test_rm_rf_root_is_destructive(self):
        enforcer = self._make_enforcer()
        violations = enforcer.check("rm -rf /")
        assert len(violations) > 0

    def test_rm_rf_subdir_is_allowed(self):
        enforcer = self._make_enforcer()
        assert enforcer.is_safe("rm -rf /tmp/test_dir") is True

    def test_mkfs_is_destructive(self):
        enforcer = self._make_enforcer()
        violations = enforcer.check("mkfs.ext4 /dev/sda")
        assert len(violations) > 0

    def test_dd_raw_disk_write_is_destructive(self):
        enforcer = self._make_enforcer()
        violations = enforcer.check("dd if=/dev/zero of=/dev/sda")
        assert len(violations) > 0

    def test_fork_bomb_is_destructive(self):
        enforcer = self._make_enforcer()
        violations = enforcer.check(":() { :|:& }; :")
        assert len(violations) > 0

    def test_violation_type_is_set(self):
        from cohezion.security.constitutional_enforcer import ViolationType

        enforcer = self._make_enforcer()
        violations = enforcer.check("rm -rf /")
        assert violations[0].violation_type == ViolationType.DESTRUCTIVE_COMMAND

    def test_enforce_raises_on_violation(self):
        enforcer = self._make_enforcer()
        with pytest.raises(ValueError, match="Constitutional violation"):
            enforcer.enforce("rm -rf /")

    def test_enforce_passes_on_safe_text(self):
        enforcer = self._make_enforcer()
        enforcer.enforce("print('hello world')")  # should not raise

    def test_secret_exposure_pattern(self):
        enforcer = self._make_enforcer()
        violations = enforcer.check("print(os.environ['AWS_SECRET_ACCESS_KEY'])")
        assert len(violations) > 0

    def test_violation_dataclass(self):
        from cohezion.security.constitutional_enforcer import Violation, ViolationType

        v = Violation(
            violation_type=ViolationType.DESTRUCTIVE_COMMAND,
            pattern_matched="rm -rf /",
            input_text="rm -rf /",
            description="Destructive command detected",
        )
        assert v.violation_type == ViolationType.DESTRUCTIVE_COMMAND


# ---------------------------------------------------------------------------
# Module 2: universe/adversarial_grounding.py
# ---------------------------------------------------------------------------


class TestAdversarialGrounding:
    def _make_grounding(self):
        from cohezion.universe.adversarial_grounding import AdversarialGrounding

        return AdversarialGrounding()

    def test_perturbation_result_dataclass(self):
        from cohezion.universe.adversarial_grounding import PerturbationResult

        result = PerturbationResult(
            coherence_before=0.8,
            coherence_after=0.5,
            perturbation_magnitude=0.1,
            suspicious=False,
        )
        assert result.suspicious is False

    def test_inject_perturbation_not_suspicious(self):
        grounding = self._make_grounding()
        # Large delta → not suspicious (manifold responded normally)
        result = grounding.inject_perturbation(coherence_before=0.8, coherence_after=0.5)
        assert result.suspicious is False

    def test_inject_perturbation_suspicious(self):
        grounding = self._make_grounding()
        # Tiny delta → suspicious (manifold resisted perturbation)
        result = grounding.inject_perturbation(coherence_before=0.500, coherence_after=0.501)
        assert result.suspicious is True

    def test_alerts_accumulate(self):
        grounding = self._make_grounding()
        grounding.inject_perturbation(0.5, 0.501)  # suspicious
        grounding.inject_perturbation(0.5, 0.502)  # suspicious
        assert len(grounding.alerts) == 2

    def test_should_resync_false_insufficient_alerts(self):
        grounding = self._make_grounding()
        grounding.inject_perturbation(0.5, 0.501)
        grounding.inject_perturbation(0.5, 0.502)
        assert grounding.should_resync(consecutive_alerts=3) is False

    def test_should_resync_true(self):
        grounding = self._make_grounding()
        for i in range(3):
            grounding.inject_perturbation(0.5, 0.5 + 0.001 * i)
        assert grounding.should_resync(consecutive_alerts=3) is True

    def test_generate_perturbation_vector(self):
        grounding = self._make_grounding()
        rng = np.random.default_rng(42)
        vec = grounding.generate_perturbation_vector(rng)
        assert vec.shape == (12,)
        # Magnitude should match the configured value
        assert abs(np.linalg.norm(vec) - grounding._magnitude) < 1e-5

    def test_history_accumulates(self):
        grounding = self._make_grounding()
        grounding.inject_perturbation(0.8, 0.6)
        grounding.inject_perturbation(0.6, 0.4)
        assert len(grounding.history) == 2

    def test_hallucination_alert_dataclass(self):
        from cohezion.universe.adversarial_grounding import HallucinationAlert

        alert = HallucinationAlert(
            alert_type="coherence_bubble",
            coherence=0.5,
            perturbation_delta=0.001,
            description="Suspicious stability",
        )
        assert alert.alert_type == "coherence_bubble"


# ---------------------------------------------------------------------------
# Module 3: compound/long_horizon_task.py
# ---------------------------------------------------------------------------


class TestLongHorizonTask:
    def _make_task(self, task_id="t1"):
        from cohezion.compound.long_horizon_task import LongHorizonTask

        return LongHorizonTask(task_id=task_id, budget_sessions=3)

    def test_task_step_result_dataclass(self):
        from cohezion.compound.long_horizon_task import TaskStepResult

        r = TaskStepResult(success=True, handoff_triggered=False, checkpoint_saved=False)
        assert r.success is True

    def test_task_init(self):
        task = self._make_task()
        assert task.task_id == "t1"
        assert task.steps_completed == 0
        assert task.budget_sessions == 3

    def test_execute_step_success(self):
        task = self._make_task()
        result = task.execute_step()
        assert result.success is True
        assert task.steps_completed == 1

    def test_execute_step_triggers_handoff_when_context_high(self):
        from unittest.mock import patch

        task = self._make_task()
        with patch(
            "cohezion.compound.long_horizon_task.get_context_usage_percent", return_value=80.0
        ):
            result = task.execute_step()
        assert result.handoff_triggered is True
        assert result.checkpoint_saved is True

    def test_progress_percent(self):
        task = self._make_task()
        task.steps_completed = 2
        task.total_steps_estimated = 4
        assert task.progress_percent == pytest.approx(50.0)

    def test_progress_percent_zero_total(self):
        task = self._make_task()
        task.total_steps_estimated = 0
        assert task.progress_percent == pytest.approx(0.0)

    def test_save_checkpoint(self):
        task = self._make_task()
        task.steps_completed = 2
        checkpoint = task.save_checkpoint()
        assert checkpoint["task_id"] == "t1"
        assert checkpoint["steps_completed"] == 2

    def test_from_checkpoint(self):
        from cohezion.compound.long_horizon_task import LongHorizonTask

        checkpoint = {"task_id": "task_abc", "steps_completed": 3}
        task = LongHorizonTask.from_checkpoint(checkpoint)
        assert task.task_id == "task_abc"


# ---------------------------------------------------------------------------
# Module 4: core/zvol_swap.py
# ---------------------------------------------------------------------------


class TestZVOLSwapPipeline:
    def _make_pipeline(self, capacity=1024 * 1024):
        from cohezion.core.zvol_swap import ZVOLSwapPipeline

        return ZVOLSwapPipeline(zvol_capacity_bytes=capacity)

    def test_kv_cache_entry(self):
        from cohezion.core.zvol_swap import KVCacheEntry

        entry = KVCacheEntry(agent_id="agent1", context_bytes=1024, priority=0.3)
        assert entry.context_bytes == 1024

    def test_swap_event_to_dict(self):
        from cohezion.core.zvol_swap import SwapEvent, SwapEventType

        ev = SwapEvent(
            event_type=SwapEventType.PAGED_TO_ZVOL, detail="paged agent1", bytes_freed=512
        )
        d = ev.to_dict()
        assert d["event_type"] == "paged_to_zvol"

    def test_register_and_page(self):
        from cohezion.core.zvol_swap import KVCacheEntry, SwapEventType

        pipeline = self._make_pipeline()
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="a1", context_bytes=100, priority=0.1)
        )
        event = pipeline.page_to_zvol()
        assert event.event_type == SwapEventType.PAGED_TO_ZVOL
        assert "a1" in event.detail

    def test_page_raises_when_empty(self):
        pipeline = self._make_pipeline()
        with pytest.raises(RuntimeError):
            pipeline.page_to_zvol()

    def test_pages_lowest_priority_first(self):
        from cohezion.core.zvol_swap import KVCacheEntry

        pipeline = self._make_pipeline()
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="high", context_bytes=100, priority=0.9)
        )
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="low", context_bytes=100, priority=0.1)
        )
        event = pipeline.page_to_zvol()
        assert "low" in event.detail

    def test_zvol_full_triggers_apoptosis(self):
        from cohezion.core.zvol_swap import KVCacheEntry, SwapEventType

        pipeline = self._make_pipeline(capacity=50)  # tiny capacity
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="a1", context_bytes=100, priority=0.1)
        )
        event = pipeline.page_to_zvol()
        assert event.event_type == SwapEventType.ZVOL_FULL_APOPTOSIS
        assert "a1" in pipeline.terminated_agents

    def test_is_oom_safe(self):
        pipeline = self._make_pipeline()
        assert pipeline.is_oom_safe() is True

    def test_zvol_utilization(self):
        from cohezion.core.zvol_swap import KVCacheEntry

        pipeline = self._make_pipeline(capacity=1000)
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="a1", context_bytes=400, priority=0.1)
        )
        pipeline.page_to_zvol()
        assert pipeline.zvol_utilization() == pytest.approx(0.4)

    def test_events_list(self):
        from cohezion.core.zvol_swap import KVCacheEntry

        pipeline = self._make_pipeline()
        pipeline.register_agent_context(
            KVCacheEntry(agent_id="a1", context_bytes=100, priority=0.1)
        )
        pipeline.page_to_zvol()
        events = pipeline.events()
        assert len(events) == 1
        assert "event_type" in events[0]
