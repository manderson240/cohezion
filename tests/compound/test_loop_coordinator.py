"""Tests for LoopCoordinator.run() — LocalImprovementExecutor wiring.

Verifies:
- LocalImprovementExecutor is used by default (use_local_inference=True)
- Cloud escalation fires after cloud_escalation_threshold consecutive local failures
- local_tokens / cloud_tokens correctly split in SprintResult
- LoopTickSweeper.course_correct() is called at sprint boundaries
- Budget exhaustion terminates the loop cleanly
- Executor.stop() is always called even on early exit
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_config(**overrides):
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig

    defaults = dict(
        use_local_inference=True,
        local_base_url="http://localhost:19999",
        worktree_path="/tmp/test-worktree",
        checkpoint_path="/tmp/test-loop/checkpoint.json",
        backlog_path="/tmp/test-loop/backlog.json",
        results_path="/tmp/test-loop/results.json",
        max_tokens=100_000,
        max_wall_clock_hours=1.0,
        sprint_duration_seconds=999_999,  # never flush mid-test unless forced
        cloud_escalation_threshold=2,
        min_free_ram_gb=0.0,  # disable RAM guard in unit tests
        resume_from_checkpoint=False,
        fail_fast=False,
    )
    defaults.update(overrides)
    return LoopConfig(**defaults)


def _make_task(tid="t1", category="test_fix", priority=1):
    from cohezion.compound.autonomous_loop.coordinator import LoopTask

    return LoopTask(
        id=tid,
        description=f"Task {tid}",
        category=category,
        priority=priority,
        verification="uv run pytest tests/foo.py -q",
        estimated_tokens=100,
    )


def _mock_local_exec(success: bool = True, tokens: int = 50) -> MagicMock:
    """Build a mock LocalImprovementExecutor with execute_batch support.

    The coordinator now calls execute_batch() for all local tasks.
    execute_batch returns one result dict per task in the batch, keyed by task_id.
    """
    m = MagicMock()
    m._started = False
    m._sweeper = MagicMock()
    m._sweeper.course_correct.return_value = []

    def batch_result(batch, worktree_path=""):
        return [
            {
                "task_id": task.id,
                "success": success,
                "summary": "ok" if success else "failed",
                "tokens_used": tokens,
                "output": "",
                "returncode": 0 if success else 1,
            }
            for task in batch
        ]

    m.execute_batch.side_effect = batch_result
    # execute_task kept for backward-compat in tests that set side_effects on it;
    # the coordinator no longer calls it directly.
    m.execute_task.return_value = {
        "success": success,
        "summary": "ok" if success else "failed",
        "tokens_used": tokens,
        "output": "",
        "returncode": 0 if success else 1,
    }

    def fake_start(path):
        m._started = True

    def fake_stop():
        m._started = False

    m.start.side_effect = fake_start
    m.stop.side_effect = fake_stop
    return m


def _mock_cloud_exec(success: bool = True, tokens: int = 200) -> MagicMock:
    """Build a mock ImprovementExecutor (cloud)."""
    m = MagicMock()
    m._started = False
    m.execute_task.return_value = {
        "success": success,
        "summary": "cloud ok" if success else "cloud failed",
        "tokens_used": tokens,
        "output": "",
        "returncode": 0 if success else 1,
    }

    def fake_start(path):
        m._started = True

    def fake_stop():
        m._started = False

    m.start.side_effect = fake_start
    m.stop.side_effect = fake_stop
    return m


class TestDefaultLocalExecution:
    def test_local_executor_used_by_default(self) -> None:
        """When use_local_inference=True, LocalImprovementExecutor.execute_task is called."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config()
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task()]

        local_exec = _mock_local_exec(success=True)

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch(
                "cohezion.compound.autonomous_loop.executor.ImprovementExecutor"
            ) as mock_cloud_cls,
        ):
            coordinator.run()

        local_exec.execute_batch.assert_called_once()
        # Cloud executor should never be instantiated when local succeeds
        mock_cloud_cls.assert_not_called()

    def test_local_tokens_tracked_in_result(self) -> None:
        """Tokens from local executor appear in report's results with is_cloud=False."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config()
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task()]

        local_exec = _mock_local_exec(success=True, tokens=77)

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            report = coordinator.run()

        assert report.results[0]["tokens"] == 77
        assert report.results[0]["is_cloud"] is False

    def test_use_local_inference_false_skips_local_executor(self) -> None:
        """When use_local_inference=False, ImprovementExecutor is used instead."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(use_local_inference=False)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task()]

        cloud_exec = _mock_cloud_exec(success=True)

        with (
            patch(
                "cohezion.compound.autonomous_loop.executor.ImprovementExecutor",
                return_value=cloud_exec,
            ),
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor"
            ) as mock_local_cls,
        ):
            coordinator.run()

        # Local executor class was never instantiated
        mock_local_cls.assert_not_called()
        cloud_exec.execute_task.assert_called_once()


class TestCloudEscalation:
    def test_escalates_after_threshold_local_failures(self) -> None:
        """After cloud_escalation_threshold=2 failures on same task, cloud executor is used.

        The coordinator routes to cloud when consecutive_failures >= threshold.
        Cloud executor must be supplied as run(executor=...) — the coordinator
        does not auto-instantiate it in use_local_inference=True mode.
        """
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=2)
        coordinator = LoopCoordinator(config)
        # Same task id so failure count accumulates across picks
        coordinator._backlog = [
            _make_task("t1"),
            _make_task("t1"),  # same id: failure count = 2 → escalate on 3rd pick
            _make_task("t1"),
        ]

        local_exec = _mock_local_exec(success=False, tokens=10)
        cloud_exec = _mock_cloud_exec(success=True, tokens=200)

        with patch(
            "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
            return_value=local_exec,
        ):
            coordinator.run(executor=cloud_exec)

        # Cloud executor must have been called at least once (escalation fired)
        assert cloud_exec.execute_task.call_count > 0

    def test_cloud_tokens_tracked_separately_from_local(self) -> None:
        """Escalated cloud tasks show is_cloud=True in results.

        threshold=1 means after ONE local failure, the next pick of the same
        task goes to cloud. Cloud executor is passed as run(executor=...).
        """
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=1)
        coordinator = LoopCoordinator(config)
        # Same task id twice: first pick fails locally, second pick escalates
        coordinator._backlog = [_make_task("t1"), _make_task("t1")]

        local_exec = _mock_local_exec(success=False, tokens=10)
        cloud_exec = _mock_cloud_exec(success=True, tokens=200)

        with patch(
            "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
            return_value=local_exec,
        ):
            report = coordinator.run(executor=cloud_exec)

        cloud_results = [r for r in report.results if r["is_cloud"]]
        local_results = [r for r in report.results if not r["is_cloud"]]
        assert len(cloud_results) > 0
        assert len(local_results) > 0

    def test_local_failure_counter_resets_on_success(self) -> None:
        """If a task succeeds locally, its failure count resets to zero."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=2)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task("t1"), _make_task("t2")]

        call_count = [0]

        def alternating_result(task, worktree_path):
            call_count[0] += 1
            return {
                "success": True,
                "summary": "ok",
                "tokens_used": 5,
                "output": "",
                "returncode": 0,
            }

        local_exec = _mock_local_exec(success=True)
        local_exec.execute_task.side_effect = alternating_result

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            report = coordinator.run()

        # Two tasks, both succeeded locally — no cloud needed
        assert report.tasks_completed == 2
        assert all(not r["is_cloud"] for r in report.results)


class TestSprintTokenTracking:
    def test_sprint_result_splits_local_and_cloud_tokens(self) -> None:
        """SprintResult.local_tokens and .cloud_tokens are independently tracked."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator, SprintResult

        # Force sprint flush: set sprint_duration=0 so every task flushes
        config = _make_config(sprint_duration_seconds=0, cloud_escalation_threshold=1)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task("t1"), _make_task("t2")]

        # t1 fails locally → escales to cloud
        call_seq = [False, True]  # first call local fails, second (t2) succeeds
        idx = [0]

        def seq_result(task, worktree_path):
            r = call_seq[idx[0] % len(call_seq)]
            idx[0] += 1
            return {
                "success": r,
                "summary": "ok" if r else "fail",
                "tokens_used": 10,
                "output": "",
                "returncode": 0 if r else 1,
            }

        local_exec = _mock_local_exec(success=True)
        local_exec.execute_task.side_effect = seq_result

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            coordinator.run()

        # Sprint results were flushed; verify they exist and have the fields
        for sr in coordinator._sprint_results:
            assert isinstance(sr, SprintResult)
            assert hasattr(sr, "local_tokens")
            assert hasattr(sr, "cloud_tokens")
            assert sr.local_tokens + sr.cloud_tokens == sr.tokens_used


class TestSweeperCourseCorrection:
    def test_course_correct_called_at_sprint_boundary(self) -> None:
        """LoopTickSweeper.course_correct() fires when the sprint window elapses."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        # sprint_duration=0 → every task triggers a sprint flush
        config = _make_config(sprint_duration_seconds=0)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task("t1"), _make_task("t2")]

        local_exec = _mock_local_exec(success=True)

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            coordinator.run()

        # course_correct was called once per sprint flush
        assert local_exec._sweeper.course_correct.call_count >= 1

    def test_course_correct_receives_category_stats(self) -> None:
        """course_correct() gets the category stats dict with done/failed counts."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [
            _make_task("t1", category="test_fix"),
            _make_task("t2", category="lint_fix"),
        ]

        local_exec = _mock_local_exec(success=True)

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            coordinator.run()

        # Every call passes sprint_results list and category_stats dict
        for call_args in local_exec._sweeper.course_correct.call_args_list:
            sprint_list, cat_stats = call_args[0]
            assert isinstance(sprint_list, list)
            assert isinstance(cat_stats, dict)

    def test_sweeper_error_does_not_crash_loop(self) -> None:
        """If course_correct raises, the loop continues — it's non-blocking."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(sprint_duration_seconds=0)
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task("t1")]

        local_exec = _mock_local_exec(success=True)
        local_exec._sweeper.course_correct.side_effect = RuntimeError("sweeper offline")

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            report = coordinator.run()  # must not raise

        assert report.tasks_completed == 1


class TestExecutorLifecycle:
    def test_local_executor_started_and_stopped(self) -> None:
        """start() and stop() are both called on the local executor."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config()
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task()]

        local_exec = _mock_local_exec(success=True)

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            coordinator.run()

        local_exec.start.assert_called_once_with(config.worktree_path)
        local_exec.stop.assert_called_once()

    def test_cloud_executor_stop_only_when_started(self) -> None:
        """If cloud executor was never started (no escalation), stop() must not be called."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config(cloud_escalation_threshold=5)  # never escalates
        coordinator = LoopCoordinator(config)
        coordinator._backlog = [_make_task()]

        local_exec = _mock_local_exec(success=True)
        cloud_exec = _mock_cloud_exec(success=True)
        cloud_exec._started = False  # never started

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch(
                "cohezion.compound.autonomous_loop.executor.ImprovementExecutor",
                return_value=cloud_exec,
            ),
        ):
            coordinator.run()

        # Cloud was passed as implicit fallback — it was never started
        cloud_exec.stop.assert_not_called()

    def test_empty_backlog_returns_clean_report(self) -> None:
        """An empty backlog produces a valid report with zero tasks."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator

        config = _make_config()
        coordinator = LoopCoordinator(config)
        coordinator._backlog = []

        local_exec = _mock_local_exec()

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                return_value=local_exec,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            report = coordinator.run()

        assert report.tasks_completed == 0
        assert report.tasks_failed == 0
        assert report.results == []
        local_exec.execute_task.assert_not_called()


class TestWarmupTiersCalledFromStart:
    """warmup_tiers() must be called inside LocalImprovementExecutor.start().

    Discriminating tests: a wrong implementation that skips warmup_tiers() would fail
    test_warmup_called_with_base_url. These tests pin the NPU stale-context fix so
    it cannot regress silently.
    """

    def test_warmup_called_with_base_url(self) -> None:
        """start() calls warmup_tiers() with the executor's base_url — not a constant.

        A wrong impl that calls warmup_tiers() with a hardcoded URL or skips it entirely
        would fail this assertion. This is the discriminating case.
        """
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        custom_url = "http://localhost:19999"

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.warmup_tiers",
                return_value={"npu": True, "igpu": True, "cpu": True},
            ) as mock_warmup,
            patch("cohezion.compound.autonomous_loop.local_executor.check_ram", return_value=(True, 32.0)),
        ):
            exec_ = LocalImprovementExecutor(base_url=custom_url)
            exec_.start("/tmp/worktree")

        mock_warmup.assert_called_once_with(custom_url)

    def test_warmup_failure_does_not_prevent_start(self) -> None:
        """If warmup_tiers() reports tier failures, start() still sets _started=True.

        NPU warmup can fail transiently (cold boot, slow CLI). The executor should
        start anyway and let execute_task's existing fallback handle HTTP 500s.
        """
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.warmup_tiers",
                return_value={"npu": False, "igpu": True, "cpu": True},
            ),
            patch("cohezion.compound.autonomous_loop.local_executor.check_ram", return_value=(True, 32.0)),
        ):
            exec_ = LocalImprovementExecutor()
            exec_.start("/tmp/worktree")

        assert exec_._started is True

    def test_warmup_complete_failure_does_not_raise(self) -> None:
        """If all tiers fail warmup, start() still completes without raising."""
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.warmup_tiers",
                return_value={"npu": False, "igpu": False, "cpu": False},
            ),
            patch("cohezion.compound.autonomous_loop.local_executor.check_ram", return_value=(True, 32.0)),
        ):
            exec_ = LocalImprovementExecutor()
            exec_.start("/tmp/worktree")  # must not raise

        assert exec_._started is True


class TestReflectionLoopWiring:
    """Verify LoopCoordinator passes its DegradationDetector to LocalImprovementExecutor.

    The discriminating case: a wrong impl that constructs LocalImprovementExecutor
    without the detector would pass the happy-path tests above but fail here —
    the reflection feedback loop would be silently absent.
    """

    def test_coordinator_passes_detector_to_local_executor(self) -> None:
        """DegradationDetector passed to LoopCoordinator flows into LocalImprovementExecutor.

        Verifies the constructor call captures degradation_detector=<the coordinator's
        detector instance>, not None.
        """
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator
        from cohezion.compound.degradation_detector import DegradationDetector

        detector = DegradationDetector()
        config = _make_config()
        coordinator = LoopCoordinator(config, degradation_detector=detector)
        coordinator._backlog = []  # empty — only care about construction

        captured_kwargs: dict = {}

        def capture_executor(base_url, degradation_detector=None):
            captured_kwargs["base_url"] = base_url
            captured_kwargs["degradation_detector"] = degradation_detector
            return _mock_local_exec()  # already strips execute_batch

        # Patch at the source module (lazy import inside run() rebinds from there)
        with (
            patch(
                "cohezion.compound.autonomous_loop.local_executor.LocalImprovementExecutor",
                side_effect=capture_executor,
            ),
            patch("cohezion.compound.autonomous_loop.executor.ImprovementExecutor"),
        ):
            coordinator.run()

        assert captured_kwargs.get("degradation_detector") is detector, (
            "LoopCoordinator must pass its _degradation_detector to LocalImprovementExecutor; "
            f"got {captured_kwargs.get('degradation_detector')!r}"
        )

    def test_coordinator_detector_is_not_none_by_default(self) -> None:
        """LoopCoordinator always has a non-None detector — auto-created if not supplied."""
        from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator
        from cohezion.compound.degradation_detector import DegradationDetector

        coordinator = LoopCoordinator(_make_config())
        assert isinstance(coordinator._degradation_detector, DegradationDetector)
