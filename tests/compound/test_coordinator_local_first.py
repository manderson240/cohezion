"""Tests for LoopCoordinator local-first dispatch and sprint boundary behavior.

Verifies:
- LocalImprovementExecutor is used by default (use_local_inference=True)
- Cloud escalation triggers after cloud_escalation_threshold consecutive local failures
- Sprint boundaries flush SprintResult and call course_correct()
- local_tokens / cloud_tokens are tracked separately per sprint
- Category stats accumulate correctly for the sweeper

Patching strategy: run() imports LocalImprovementExecutor from .local_executor at call time,
so we patch `cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor`.
The in-function `from .local_executor import LocalImprovementExecutor` binds the patched class.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# Canonical patch target — where the class is defined (in-function import binds this at call time)
_LOCAL_EXEC_PATH = "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor"


def _make_task(
    task_id: str = "t1",
    category: str = "test_fix",
    priority: int = 1,
    verification: str = "uv run pytest -q",
):
    from cohezion.compound.autonomous_loop.coordinator import LoopTask

    return LoopTask(
        id=task_id,
        description=f"Fix task {task_id}",
        priority=priority,
        category=category,
        verification=verification,
        estimated_tokens=100,
    )


def _make_config(**overrides):
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig

    defaults = dict(
        use_local_inference=True,
        cloud_escalation_threshold=2,
        sprint_duration_seconds=0,  # flush immediately after every task
        checkpoint_interval_seconds=9999,
        max_tokens=1_000_000,
        max_wall_clock_hours=1.0,
        checkpoint_path="/tmp/test-coordinator-checkpoint.json",
        resume_from_checkpoint=False,  # prevent tests polluting each other via disk state
    )
    defaults.update(overrides)
    return LoopConfig(**defaults)


def _local_mock(success: bool = True, tokens: int = 50) -> MagicMock:
    """Build a mock LocalImprovementExecutor that optionally succeeds."""
    mock = MagicMock()
    mock._started = True
    mock._sweeper = MagicMock()
    mock._sweeper.course_correct.return_value = ""
    mock.execute_task.return_value = {
        "success": success,
        "summary": "done" if success else "failed",
        "tokens_used": tokens,
        "output": "",
        "returncode": 0 if success else 1,
    }
    return mock


def _cloud_mock(success: bool = True, tokens: int = 80) -> MagicMock:
    """Build a mock cloud ImprovementExecutor."""
    mock = MagicMock()
    mock._started = True
    mock.execute_task.return_value = {
        "success": success,
        "summary": "done" if success else "failed",
        "tokens_used": tokens,
        "output": "",
        "returncode": 0 if success else 1,
    }
    return mock


class TestLocalFirstDispatch:
    def test_local_executor_called_by_default(self) -> None:
        """With use_local_inference=True, local executor handles task dispatch."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        coord = LoopCoordinator(_make_config())
        coord._backlog = [_make_task()]
        local = _local_mock(success=True)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        local.execute_task.assert_called_once()

    def test_cloud_executor_not_called_on_first_success(self) -> None:
        """Cloud executor is never invoked when local succeeds first try."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        coord = LoopCoordinator(_make_config())
        coord._backlog = [_make_task()]
        local = _local_mock(success=True)
        cloud = _cloud_mock(success=True)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run(executor=cloud)

        cloud.execute_task.assert_not_called()

    def test_use_local_inference_false_skips_local_executor(self) -> None:
        """When use_local_inference=False, only the cloud executor runs."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(use_local_inference=False)
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task()]
        cloud = _cloud_mock(success=True)

        with patch(_LOCAL_EXEC_PATH) as local_cls:
            coord.run(executor=cloud)

        # LocalImprovementExecutor class should not be instantiated
        local_cls.assert_not_called()
        cloud.execute_task.assert_called_once()


class TestCloudEscalation:
    def test_escalates_after_threshold_local_failures(self) -> None:
        """After cloud_escalation_threshold consecutive local failures, cloud takes over."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=2)
        coord = LoopCoordinator(config)
        task = _make_task()
        coord._backlog = [task]

        local = _local_mock(success=False, tokens=10)
        cloud = _cloud_mock(success=True, tokens=20)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run(executor=cloud)

        # Local should be called 2 times (threshold), then cloud takes over
        assert local.execute_task.call_count == 2
        assert cloud.execute_task.call_count == 1

    def test_local_failure_counter_resets_on_cloud_success(self) -> None:
        """After cloud handles a task, local failure counter is cleared."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=1)
        coord = LoopCoordinator(config)
        # Two tasks: first fails locally once → cloud; second should start fresh on local
        task_a = _make_task("a", priority=1)
        task_b = _make_task("b", priority=2)
        coord._backlog = [task_a, task_b]

        local_responses = iter(
            [
                # task_a: 1 local failure
                {
                    "success": False,
                    "summary": "fail",
                    "tokens_used": 5,
                    "output": "",
                    "returncode": 1,
                },
                # task_b: local success (counter was reset)
                {
                    "success": True,
                    "summary": "done",
                    "tokens_used": 5,
                    "output": "",
                    "returncode": 0,
                },
            ]
        )

        local = MagicMock()
        local._started = True
        local._sweeper = MagicMock()
        local._sweeper.course_correct.return_value = ""
        local.execute_task.side_effect = lambda t, p: next(local_responses)

        cloud = _cloud_mock(success=True, tokens=20)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            report = coord.run(executor=cloud)

        assert cloud.execute_task.call_count == 1  # only task_a escalated
        assert report.tasks_completed == 2

    def test_local_failure_counter_resets_on_local_success(self) -> None:
        """If a task fails then succeeds locally on retry, counter resets."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        # Threshold 3: task must fail 3× before escalating
        config = _make_config(cloud_escalation_threshold=3)
        coord = LoopCoordinator(config)
        task = _make_task("a", priority=1)
        coord._backlog = [task]

        responses = iter(
            [
                {
                    "success": False,
                    "summary": "fail",
                    "tokens_used": 5,
                    "output": "",
                    "returncode": 1,
                },
                {
                    "success": False,
                    "summary": "fail",
                    "tokens_used": 5,
                    "output": "",
                    "returncode": 1,
                },
                # Third attempt: local succeeds
                {
                    "success": True,
                    "summary": "done",
                    "tokens_used": 5,
                    "output": "",
                    "returncode": 0,
                },
            ]
        )

        local = MagicMock()
        local._started = True
        local._sweeper = MagicMock()
        local._sweeper.course_correct.return_value = ""
        local.execute_task.side_effect = lambda t, p: next(responses)

        cloud = _cloud_mock(success=True)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            report = coord.run(executor=cloud)

        # Cloud should NOT be called; local succeeded on 3rd attempt (threshold=3)
        cloud.execute_task.assert_not_called()
        assert report.tasks_completed == 1


class TestSprintBoundaries:
    def test_sprint_number_increments_after_flush(self) -> None:
        """Sprint number increments when the sprint window elapses (sprint_duration_seconds=0)."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task("t1"), _make_task("t2")]

        local = _local_mock(success=True)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        # 2 tasks → 2 sprint flushes → sprint_number == 2
        assert coord._sprint_number == 2
        assert len(coord._sprint_results) == 2

    def test_sprint_result_local_tokens_populated(self) -> None:
        """SprintResult.local_tokens is non-zero after local execution."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task()]

        local = _local_mock(success=True, tokens=42)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        assert coord._sprint_results[0].local_tokens == 42
        assert coord._sprint_results[0].cloud_tokens == 0

    def test_sprint_result_tracks_local_vs_cloud_tokens(self) -> None:
        """When cloud handles a task, cloud_tokens is populated; local_tokens reflects the failure."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(
            sprint_duration_seconds=0,
            cloud_escalation_threshold=1,  # escalate after 1 local failure
        )
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task()]

        local = _local_mock(success=False, tokens=30)
        cloud = _cloud_mock(success=True, tokens=80)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run(executor=cloud)

        total_local = sum(s.local_tokens for s in coord._sprint_results)
        total_cloud = sum(s.cloud_tokens for s in coord._sprint_results)
        assert total_local == 30
        assert total_cloud == 80

    def test_course_correct_called_at_sprint_boundary(self) -> None:
        """Sweeper course_correct() is invoked once per sprint flush."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task("t1"), _make_task("t2")]

        local = _local_mock(success=True)
        sweeper = MagicMock()
        sweeper.course_correct.return_value = "Use conftest.py for shared fixtures."
        local._sweeper = sweeper

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        assert sweeper.course_correct.call_count == 2

    def test_course_correct_receives_category_stats_with_attempts_successes(self) -> None:
        """Category stats use 'attempts'/'successes' keys matching LoopTickSweeper.course_correct()."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task(category="lint_fix")]

        captured_stats: list[dict] = []

        local = _local_mock(success=True)
        sweeper = MagicMock()
        sweeper.course_correct.side_effect = lambda sr, cs: captured_stats.append(dict(cs)) or ""
        local._sweeper = sweeper

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        assert captured_stats
        stats = captured_stats[0]
        assert "lint_fix" in stats
        assert stats["lint_fix"]["attempts"] == 1
        assert stats["lint_fix"]["successes"] == 1

    def test_failed_task_increments_attempts_not_successes(self) -> None:
        """A failed task increments attempts but not successes in category stats."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(
            sprint_duration_seconds=0,
            cloud_escalation_threshold=99,  # never escalate in this test
        )
        coord = LoopCoordinator(config)
        coord._backlog = [_make_task(category="type_fix")]

        captured_stats: list[dict] = []

        local = _local_mock(success=False, tokens=10)
        sweeper = MagicMock()
        sweeper.course_correct.side_effect = lambda sr, cs: captured_stats.append(dict(cs)) or ""
        local._sweeper = sweeper

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            coord.run()

        stats = captured_stats[0]
        assert stats["type_fix"]["attempts"] == 1
        assert stats["type_fix"]["successes"] == 0


class TestReportAccumulation:
    def test_final_report_reflects_all_tasks(self) -> None:
        """LoopReport.tasks_completed counts all successful tasks."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        coord = LoopCoordinator(_make_config())
        coord._backlog = [_make_task("t1"), _make_task("t2"), _make_task("t3")]

        local = _local_mock(success=True)

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            report = coord.run()

        assert report.tasks_completed == 3
        assert report.tasks_failed == 0
        assert report.success_rate == 1.0

    def test_success_rate_mixed_results(self) -> None:
        """success_rate = completed / (completed + failed)."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        coord = LoopCoordinator(_make_config(cloud_escalation_threshold=99))
        coord._backlog = [_make_task("t1"), _make_task("t2")]

        results = iter([True, False])

        local = MagicMock()
        local._started = True
        local._sweeper = MagicMock()
        local._sweeper.course_correct.return_value = ""
        local.execute_task.side_effect = lambda t, p: {
            "success": next(results),
            "summary": "x",
            "tokens_used": 10,
            "output": "",
            "returncode": 0,
        }

        with patch(_LOCAL_EXEC_PATH, return_value=local):
            report = coord.run()

        assert report.tasks_completed == 1
        assert report.tasks_failed == 1
        assert report.success_rate == 0.5
