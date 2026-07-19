"""Discriminating tests for the hook->daemon enqueue bridge.

The gap being closed: 96 TRIGGERED hook events, 0 tasks enqueued, daemon idle. Every test
below is written so a plausible-but-wrong implementation FAILS it.
"""

from __future__ import annotations

import json

import pytest

from cohezion.compound import enqueue as eq


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Never touch the real ~/.cohezion queue from a test."""
    monkeypatch.setattr(eq, "STATE_DIR", tmp_path)
    monkeypatch.setattr(eq, "TASKS_FILE", tmp_path / "compound_tasks.json")
    monkeypatch.setattr(eq, "LOCK_FILE", tmp_path / "compound_tasks.lock")


def _tasks():
    return json.loads(eq.TASKS_FILE.read_text())


class TestEnqueue:
    def test_task_lands_in_the_daemon_schema(self):
        """The daemon reads {id, prompt, priority, done}. A task missing any of those is
        invisible to it — which would reproduce the exact bug being fixed."""
        assert eq.enqueue("audit the thing") is True
        (t,) = _tasks()
        assert {"id", "prompt", "priority", "done"} <= set(t)
        assert t["prompt"] == "audit the thing"
        assert t["done"] is False

    def test_empty_prompt_rejected(self):
        assert eq.enqueue("   ") is False
        assert not eq.TASKS_FILE.exists()

    def test_ids_increment_and_do_not_collide(self):
        for i in range(3):
            eq.enqueue(f"task {i}")
        ids = [t["id"] for t in _tasks()]
        assert len(set(ids)) == 3, f"duplicate ids: {ids}"


class TestDeduplication:
    def test_pending_duplicate_is_skipped(self):
        """Discriminating: the hook fired 96x on repeat edits to the same files. An impl
        that appends unconditionally floods the queue and starves everything else."""
        assert eq.enqueue("same work") is True
        assert eq.enqueue("same work") is False
        assert len(_tasks()) == 1

    def test_completed_task_outside_window_can_requeue(self):
        """Mirror case: recurring work must be able to come back. An impl that dedups on
        prompt alone, forever, silently stops enqueuing legitimate repeat work."""
        eq.enqueue("recurring audit")
        tasks = _tasks()
        tasks[0]["done"] = True
        tasks[0]["created_at"] = eq._now() - (eq.DEDUP_WINDOW_HOURS + 1) * 3600
        eq.TASKS_FILE.write_text(json.dumps(tasks))
        assert eq.enqueue("recurring audit") is True
        assert len(_tasks()) == 2

    def test_completed_task_inside_window_is_still_skipped(self):
        eq.enqueue("recent work")
        tasks = _tasks()
        tasks[0]["done"] = True  # created_at is now -> inside the window
        eq.TASKS_FILE.write_text(json.dumps(tasks))
        assert eq.enqueue("recent work") is False


class TestSafety:
    def test_queue_is_bounded(self):
        """A runaway edit loop must not grow the file without limit."""
        for i in range(eq.MAX_PENDING + 5):
            eq.enqueue(f"task {i}")
        assert len(_tasks()) == eq.MAX_PENDING

    def test_unparseable_queue_is_never_clobbered(self):
        """Discriminating: an impl that starts fresh on a parse error DESTROYS the real
        queue. Refusing to write is the only safe behaviour."""
        eq.TASKS_FILE.write_text("{ this is not json")
        assert eq.enqueue("new task") is False
        assert eq.TASKS_FILE.read_text() == "{ this is not json"

    def test_existing_tasks_are_preserved(self):
        eq.TASKS_FILE.write_text(
            json.dumps([{"id": 7, "prompt": "pre-existing", "priority": 1, "done": False}])
        )
        eq.enqueue("added later")
        prompts = [t["prompt"] for t in _tasks()]
        assert "pre-existing" in prompts and "added later" in prompts

    def test_never_raises_on_broken_state_dir(self, monkeypatch):
        """Fail-silent: a hook that breaks the user's edit flow is worse than a lost task."""
        monkeypatch.setattr(eq, "STATE_DIR", eq.STATE_DIR / "nope" / "\0bad")
        assert eq.enqueue("anything") is False


class TestPendingCount:
    def test_distinguishes_empty_from_unreadable(self):
        """Discriminating: returning 0 for an unreadable queue is the same fail-open that
        made the original bug invisible — 'no tasks' and 'cannot read tasks' must differ."""
        assert eq.pending_count() == -1  # file absent
        eq.enqueue("a")
        assert eq.pending_count() == 1
        eq.TASKS_FILE.write_text("not json")
        assert eq.pending_count() == -1
