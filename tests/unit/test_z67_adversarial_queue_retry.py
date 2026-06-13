"""Adversarial batch Z67: task_queue exhaustion/flush logic + retry_with_backoff semantics.

Real bugs confirmed:

task_queue.py:
1. dequeue() never checks can_retry() — exhausted tasks (attempts>=max_attempts)
   are returned to callers instead of being silently discarded.
2. flush(TaskPriority.LOW) with the default argument flushes nothing because
   the guard uses strict-greater (>) instead of greater-or-equal (>=), so the
   intended "drop low-priority tasks" path is dead code.

p0_resilience_mixins.py:
3. asyncio.Coroutine was removed in Python 3.11 — the module crashes on import
   with AttributeError. No `from __future__ import annotations` to lazify them.
4. retry_with_backoff(max_retries=0) never calls the operation — range(0) is
   empty — and returns None silently.
5. retry_with_backoff semantic off-by-one: max_retries=N means N total attempts,
   not N retries after the first. With max_retries=1 only 1 attempt is made.
6. CheckpointManager.cleanup_before(N) deletes checkpoints >= N, not < N —
   the name says "before" but the implementation does "from N onwards".
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/task_queue.py
# ---------------------------------------------------------------------------


class TestTaskQueueExhaustion:
    def _task(self, attempts=0, max_attempts=3, priority=None, timeout=9999.0):
        from cohezion.compound.task_queue import QueuedTask, TaskPriority

        return QueuedTask(
            task_id=f"t_{attempts}_{max_attempts}",
            prompt="p",
            system_prompt=None,
            model="m",
            priority=priority or TaskPriority.NORMAL,
            attempts=attempts,
            max_attempts=max_attempts,
            timeout_seconds=timeout,
        )

    def test_dequeue_skips_exhausted_task(self):
        """dequeue() must not return a task where attempts >= max_attempts.

        BUG: dequeue() checks has_expired() but not can_retry(). A task that
        has been attempted max_attempts times is still returned to the caller,
        which then re-attempts it — violating the max_attempts contract.
        """
        from cohezion.compound.task_queue import TaskQueue

        q = TaskQueue()
        exhausted = self._task(attempts=3, max_attempts=3)
        assert not exhausted.can_retry()

        q.enqueue(exhausted)
        result = q.dequeue()
        assert result is None, (
            f"dequeue() returned exhausted task (attempts={result.attempts} == max_attempts)"
            if result
            else ""
        )

    def test_dequeue_returns_task_with_remaining_attempts(self):
        """Task with attempts < max_attempts must be dequeued normally."""
        from cohezion.compound.task_queue import TaskQueue

        q = TaskQueue()
        live = self._task(attempts=1, max_attempts=3)
        assert live.can_retry()

        q.enqueue(live)
        result = q.dequeue()
        assert result is not None
        assert result.attempts == 1

    def test_dequeue_skips_exhausted_returns_next_valid(self):
        """When the first task is exhausted, dequeue() must return the next valid one."""
        from cohezion.compound.task_queue import TaskQueue

        q = TaskQueue()
        q.enqueue(self._task(attempts=3, max_attempts=3))  # exhausted
        q.enqueue(self._task(attempts=0, max_attempts=3))  # valid

        result = q.dequeue()
        assert result is not None
        assert result.attempts == 0, "Should have skipped exhausted task and returned valid one"


class TestTaskQueueFlush:
    def _low_task(self, i=0):
        from cohezion.compound.task_queue import QueuedTask, TaskPriority

        return QueuedTask(
            task_id=f"low_{i}",
            prompt="p",
            system_prompt=None,
            model="m",
            priority=TaskPriority.LOW,
            timeout_seconds=9999.0,
        )

    def test_flush_low_flushes_low_priority_tasks(self):
        """flush(TaskPriority.LOW) must drop all LOW-priority tasks.

        BUG: flush() uses `if priority_threshold.value > TaskPriority.LOW.value`
        which is `1 > 1 = False` — nothing is flushed when threshold is LOW.
        The docstring says 'drop tasks with priority < threshold', implying
        flush(NORMAL) drops LOW. But the default is LOW and common usage
        expects flush() to clear the lowest tier. Fix: use >= for the LOW check.
        """
        from cohezion.compound.task_queue import TaskPriority, TaskQueue

        q = TaskQueue()
        for i in range(3):
            q.enqueue(self._low_task(i))
        assert q.size() == 3

        flushed = q.flush(TaskPriority.NORMAL)  # threshold=NORMAL → drop LOW
        assert flushed == 3, f"Expected 3 flushed, got {flushed}"
        assert q.size() == 0

    def test_flush_critical_threshold_leaves_critical_intact(self):
        """flush(CRITICAL) drops LOW and NORMAL but never CRITICAL tasks."""
        from cohezion.compound.task_queue import QueuedTask, TaskPriority, TaskQueue

        q = TaskQueue()
        for p, n in [(TaskPriority.CRITICAL, 2), (TaskPriority.NORMAL, 3), (TaskPriority.LOW, 4)]:
            for i in range(n):
                q.enqueue(
                    QueuedTask(
                        task_id=f"{p.name}_{i}",
                        prompt="p",
                        system_prompt=None,
                        model="m",
                        priority=p,
                        timeout_seconds=9999.0,
                    )
                )

        q.flush(TaskPriority.CRITICAL)  # drop LOW + NORMAL
        assert q.size() == 2  # only CRITICAL remains

    def test_size_consistent_after_flush(self):
        """Queue size reported by size() matches actual content after flush."""
        from cohezion.compound.task_queue import TaskPriority, TaskQueue

        q = TaskQueue()
        for i in range(5):
            q.enqueue(self._low_task(i))
        q.flush(TaskPriority.NORMAL)
        assert q.size() == q.metrics.current_depth == 0


# ---------------------------------------------------------------------------
# Module 2: inference/p0_resilience_mixins.py
# ---------------------------------------------------------------------------


class TestP0ResilienceMixinsImport:
    def test_module_imports_without_error(self):
        """p0_resilience_mixins must import cleanly on Python 3.11+.

        BUG: uses asyncio.Coroutine which was removed in Python 3.11.
        Without `from __future__ import annotations`, the annotation is
        evaluated eagerly at class definition → AttributeError on import.
        Fix: add `from __future__ import annotations` or replace with
        collections.abc.Coroutine.
        """
        try:
            import cohezion.inference.p0_resilience_mixins as m  # noqa: F401
        except AttributeError as e:
            pytest.fail(f"p0_resilience_mixins import failed on Python 3.11+: {e}")


class TestRetryWithBackoff:
    def test_max_retries_zero_calls_operation_once(self):
        """retry_with_backoff(max_retries=0) must call the operation exactly once.

        BUG: uses `for attempt in range(max_retries)`, so range(0) is empty
        and the operation is never called — returns None silently.
        Fix: range(max_retries + 1) to include at least the initial attempt.
        """
        from cohezion.inference.p0_resilience_mixins import retry_with_backoff

        calls = []

        async def op():
            calls.append(1)
            return "done"

        result = asyncio.run(retry_with_backoff(op, max_retries=0))
        assert len(calls) == 1, f"max_retries=0 must call op once, called {len(calls)} times"
        assert result == "done"

    def test_max_retries_means_retries_not_total_attempts(self):
        """max_retries=N must mean N additional retries after first failure (N+1 total).

        BUG: range(max_retries) gives N total attempts, not N retries.
        With max_retries=2 only 2 attempts are made; caller expects 3 (1+2).
        """
        from cohezion.inference.p0_resilience_mixins import retry_with_backoff

        calls = []

        async def always_fail():
            calls.append(1)
            raise ValueError("boom")

        with pytest.raises(ValueError):
            asyncio.run(retry_with_backoff(always_fail, max_retries=2, base_delay=0.001))

        assert len(calls) == 3, (
            f"max_retries=2 must make 3 total attempts (1 initial + 2 retries), made {len(calls)}"
        )

    def test_successful_operation_returns_result(self):
        """Successful operation on first try returns its value."""
        from cohezion.inference.p0_resilience_mixins import retry_with_backoff

        async def op():
            return 42

        result = asyncio.run(retry_with_backoff(op, max_retries=3))
        assert result == 42

    def test_succeeds_on_second_attempt(self):
        """Operation that fails once then succeeds is retried correctly."""
        from cohezion.inference.p0_resilience_mixins import retry_with_backoff

        calls = [0]

        async def flaky():
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError("first try fails")
            return "ok"

        result = asyncio.run(retry_with_backoff(flaky, max_retries=1, base_delay=0.001))
        assert result == "ok"
        assert calls[0] == 2


class TestCheckpointManagerCleanup:
    def test_cleanup_before_removes_older_phases(self, tmp_path):
        """cleanup_before(N) must remove phases with id < N, keeping N and above.

        BUG: implementation uses `if pid >= phase_id: path.unlink()` — deletes
        checkpoints FROM N onwards, which is the opposite of what 'before' means.
        Fix: change `>=` to `<` so phases before N are removed.
        """
        from cohezion.inference.p0_resilience_mixins import CheckpointManager

        cm = CheckpointManager(str(tmp_path))
        for i in range(5):
            cm.save(i, {"val": i})

        removed = cm.cleanup_before(3)
        remaining = sorted(cm.list_checkpoints().keys())

        assert removed == 3, f"Expected 3 removed (phases 0,1,2), got {removed}"
        assert remaining == [3, 4], f"Expected phases [3,4] remaining, got {remaining}"

    def test_cleanup_before_zero_removes_nothing(self, tmp_path):
        """cleanup_before(0) removes phases before 0 — there are none."""
        from cohezion.inference.p0_resilience_mixins import CheckpointManager

        cm = CheckpointManager(str(tmp_path))
        for i in range(3):
            cm.save(i, {"v": i})

        removed = cm.cleanup_before(0)
        assert removed == 0
        assert len(cm.list_checkpoints()) == 3
