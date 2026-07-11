"""V-model tests for the compound-task feeder (work item f803d5ae1202).

Structural-before-behavioral. Everything is injected — the work-queue fetch is a fake
returning literal items and the tasks/lock files live under ``tmp_path``; no HTTP, no
inference, no live services, no writes outside ``tmp_path``.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from cohezion.compound.compound_feeder import feed_compound_tasks


def _item(item_id: str, *, type_="improvement", relevance="APPLY", title="Add cache warmer"):
    return {
        "id": item_id,
        "type": type_,
        "relevance": relevance,
        "title": title,
        "description": "wire it into the executor",
        "priority": 1,
    }


def _run(items, tmp_path: Path, limit=5):
    tasks_file = tmp_path / "compound_tasks.json"
    lock_file = tmp_path / "compound_tasks.lock"
    return (
        feed_compound_tasks(
            limit=limit,
            fetch=lambda: list(items),
            tasks_file=tasks_file,
            lock_file=lock_file,
        ),
        tasks_file,
    )


def _read(tasks_file: Path) -> list[dict]:
    return json.loads(tasks_file.read_text())


# ── T-structural ──────────────────────────────────────────────────────────────
def test_structural_signature_and_flock():
    """Signature carries the injection points AND the read-modify-write is under flock."""
    params = inspect.signature(feed_compound_tasks).parameters
    assert {"limit", "fetch", "tasks_file", "lock_file"} <= set(params)

    src = inspect.getsource(feed_compound_tasks)
    # flock is called literally inside the target function (not a helper) so this
    # structural check verifies the real lock, and the same lock path is used.
    assert "fcntl.flock" in src
    assert "lock_path" in src and "LOCK_EX" in src


# ── T1: actioned improvement APPLY item becomes a pending task ─────────────────
def test_t1_apply_improvement_becomes_pending_task(tmp_path):
    result, tasks_file = _run([_item("aaa111")], tmp_path)

    assert result["fed"] == 1
    tasks = _read(tasks_file)
    assert len(tasks) == 1
    task = tasks[0]
    assert task["done"] is False
    assert task["source_item_id"] == "aaa111"
    assert task["prompt"].startswith("compound loop:")
    assert isinstance(task["id"], int)


# ── T2: idempotent — running twice adds it once ───────────────────────────────
def test_t2_idempotent_across_runs(tmp_path):
    items = [_item("dup999")]
    tasks_file = tmp_path / "compound_tasks.json"
    lock_file = tmp_path / "compound_tasks.lock"

    first = feed_compound_tasks(
        limit=5, fetch=lambda: list(items), tasks_file=tasks_file, lock_file=lock_file
    )
    second = feed_compound_tasks(
        limit=5, fetch=lambda: list(items), tasks_file=tasks_file, lock_file=lock_file
    )

    assert first["fed"] == 1
    assert second["fed"] == 0 and second["skipped"] == 1
    tasks = _read(tasks_file)
    assert [t["source_item_id"] for t in tasks] == ["dup999"]


# ── T3: item already present as done:True is NOT re-added ──────────────────────
def test_t3_already_done_not_refed(tmp_path):
    tasks_file = tmp_path / "compound_tasks.json"
    lock_file = tmp_path / "compound_tasks.lock"
    tasks_file.write_text(
        json.dumps(
            [{"id": 7, "prompt": "old", "priority": 1, "done": True, "source_item_id": "done42"}],
            indent=2,
        )
    )

    result = feed_compound_tasks(
        limit=5,
        fetch=lambda: [_item("done42")],
        tasks_file=tasks_file,
        lock_file=lock_file,
    )

    assert result["fed"] == 0 and result["skipped"] == 1
    tasks = _read(tasks_file)
    assert len(tasks) == 1 and tasks[0]["done"] is True


# ── T4: the daemon's pre-existing tasks are preserved ─────────────────────────
def test_t4_preserves_existing_daemon_tasks(tmp_path):
    tasks_file = tmp_path / "compound_tasks.json"
    lock_file = tmp_path / "compound_tasks.lock"
    seeds = [
        {"id": 1, "prompt": "seed a", "priority": 1, "done": True},
        {"id": 2, "prompt": "seed b", "priority": 2, "done": False},
    ]
    tasks_file.write_text(json.dumps(seeds, indent=2))

    result = feed_compound_tasks(
        limit=5,
        fetch=lambda: [_item("new55")],
        tasks_file=tasks_file,
        lock_file=lock_file,
    )

    assert result["fed"] == 1
    tasks = _read(tasks_file)
    assert len(tasks) == 3
    # originals untouched, order preserved, new one appended with a fresh id
    assert tasks[0] == seeds[0] and tasks[1] == seeds[1]
    assert tasks[2]["source_item_id"] == "new55"
    assert tasks[2]["id"] == 3  # max(1,2)+1


# ── T5: non-improvement / non-APPLY / non-actioned items are ignored ──────────
def test_t5_ignores_non_improvement_non_apply(tmp_path):
    items = [
        _item("keep1"),  # eligible
        _item("skip_research", type_="research"),  # wrong type
        _item("skip_reject", relevance="REJECT"),  # wrong relevance
        {"id": "", "type": "improvement", "relevance": "APPLY", "title": "no id"},  # missing id
    ]
    result, tasks_file = _run(items, tmp_path)

    assert result["candidates"] == 1
    assert result["fed"] == 1
    tasks = _read(tasks_file)
    assert [t["source_item_id"] for t in tasks] == ["keep1"]


# ── extra: dedup-before-limit does not starve when head is all dupes ───────────
def test_limit_counts_only_new_adds(tmp_path):
    tasks_file = tmp_path / "compound_tasks.json"
    lock_file = tmp_path / "compound_tasks.lock"
    # pre-seed two already-fed items, then offer them again plus two fresh ones
    tasks_file.write_text(
        json.dumps(
            [
                {"id": 1, "prompt": "x", "priority": 2, "done": False, "source_item_id": "old1"},
                {"id": 2, "prompt": "y", "priority": 2, "done": True, "source_item_id": "old2"},
            ],
            indent=2,
        )
    )
    items = [_item("old1"), _item("old2"), _item("fresh1"), _item("fresh2")]

    result = feed_compound_tasks(
        limit=1, fetch=lambda: items, tasks_file=tasks_file, lock_file=lock_file
    )

    # limit=1 new add: the two dupes are skipped (not counted), exactly one fresh added
    assert result["fed"] == 1 and result["skipped"] == 2
    tasks = _read(tasks_file)
    assert [t["source_item_id"] for t in tasks] == ["old1", "old2", "fresh1"]
