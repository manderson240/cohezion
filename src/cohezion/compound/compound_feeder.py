"""Compound-task feeder — connect the actioner→work-queue loop to the compound daemon.

Wiring note (work item f803d5ae1202): the compound daemon
(``~/cohezion-labs/compound_daemon.py``, systemd ``cohezion-compound.service``) runs the
full depth-4 ``make_executor`` cycle (CompoundExecutor→SkillRefiner→RetrospectionEngine)
on LOCAL inference — the real compounding — but starves on an empty queue. It reads
``~/.cohezion/compound_tasks.json`` and treats ``[t for t in tasks if not t.get("done")]``
as pending; once every seed task is ``done:True`` it idles "No pending tasks — sleeping".
Meanwhile the research daemon + actioner feed a SEPARATE store (work-queue API :8080) the
compound daemon cannot see. This module is the missing PRODUCER: it pulls actioned/approved
``improvement`` + ``relevance=APPLY`` work-queue items and appends them to the daemon's task
file as pending, idempotently and race-safely.

Wire-at-Creation: run this on a timer BEFORE the compound daemon's cycle. Suggested unit
(the lead/user installs — do NOT enable from here):

    # ~/.config/systemd/user/cohezion-compound-feeder.service
    [Unit]
    Description=Feed compound daemon from actioned work-queue items
    [Service]
    Type=oneshot
    ExecStart=%h/dev/cohezion/.venv/bin/python %h/dev/cohezion/scripts/compound_feeder.py --limit 5

    # ~/.config/systemd/user/cohezion-compound-feeder.timer
    [Unit]
    Description=Feed the compound daemon every 20 minutes
    [Timer]
    OnBootSec=2min
    OnUnitActiveSec=20min
    [Install]
    WantedBy=timers.target

Concurrency (the load-bearing V-model concern): the daemon also writes
``compound_tasks.json`` (``save_tasks``: atomic ``tmp`` write + ``os.replace``, whole-file
last-write-wins) WITHOUT any lock. The feeder takes an ``fcntl.flock`` on
``~/.cohezion/compound_tasks.lock`` around its read-modify-write, and writes with the
daemon's exact on-disk schema (``list[dict]``, ``json`` indent=2, atomic ``os.replace``).
This makes concurrent FEEDER runs (overlapping timer firings) safe. It does NOT by itself
make feeder↔daemon safe: ``os.replace`` prevents file *corruption*, not lost *updates*, and
the daemon does not take this lock. Full safety requires the daemon's ``load_tasks`` /
``save_tasks`` to flock the SAME lockfile — an out-of-repo follow-up flagged for the lead
who owns the daemon. The daemon idles ~30 min between cycles, so the practical collision
window is small, but that is a mitigation, not a guarantee.

Idempotent dedup: each fed task carries ``source_item_id`` = the work-queue item id. A task
is never added when its ``source_item_id`` already exists in ``compound_tasks.json`` in ANY
state (``done`` or pending), so re-runs and already-completed items never re-feed.
"""

from __future__ import annotations

import fcntl
import json
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


STATE_DIR = Path.home() / ".cohezion"
TASKS_FILE = STATE_DIR / "compound_tasks.json"
LOCK_FILE = STATE_DIR / "compound_tasks.lock"
DEFAULT_API_BASE = "http://localhost:8080"
FETCH_STATUSES = ("actioned", "approved")


def _default_fetch(base_url: str = DEFAULT_API_BASE, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Fetch APPLY ``improvement`` items in actioned/approved from the work-queue API.

    Filtering by status/type/relevance is done in the URL for efficiency; the pure
    function re-applies the type/relevance filter so injected fakes are also gated.
    """
    items: list[dict[str, Any]] = []
    for status in FETCH_STATUSES:
        url = f"{base_url.rstrip('/')}/api/work-queue?type=improvement&relevance=APPLY&status={status}"
        req = urllib.request.Request(url, method="GET")  # noqa: S310 — literal http(s) API base
        # S310: base_url is the fixed local work-queue API, scheme is http(s).
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            page = json.loads(resp.read())
        items.extend(page.get("items", []))
    return items


def _item_to_task(item: dict[str, Any], task_id: int) -> dict[str, Any]:
    """Map a work-queue item to the daemon's task schema (compound-cycle instruction)."""
    title = str(item.get("title", "")).strip()
    description = str(item.get("description", "")).strip()
    prompt = f"compound loop: {title}" if title else "compound loop: (untitled work-queue item)"
    if description:
        prompt = f"{prompt} — {description}"
    # work-queue priority is 0=low 1=normal 2=high; daemon sorts ascending (lower = sooner),
    # impact = 1/priority. Invert so high work-queue priority runs first.
    wq_priority = int(item.get("priority", 1) or 0)
    daemon_priority = max(1, 3 - wq_priority)
    return {
        "id": task_id,
        "prompt": prompt,
        "priority": daemon_priority,
        "done": False,
        "source_item_id": item.get("id"),
    }


def feed_compound_tasks(
    limit: int = 5,
    *,
    fetch: Callable[[], list[dict[str, Any]]] | None = None,
    tasks_file: Path | None = None,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    """Feed up to ``limit`` NEW work-queue items into the compound daemon's task file.

    Reads actioned/approved ``improvement`` + ``relevance=APPLY`` items, maps each to the
    daemon's ``{id, prompt, priority, done, source_item_id}`` schema, and appends them as
    pending — idempotently (keyed on ``source_item_id``) and under an ``fcntl.flock`` so
    overlapping feeder runs never drop each other's (or the daemon's existing) tasks.

    Injection points keep this pure for tests: ``fetch`` supplies work-queue items,
    ``tasks_file`` / ``lock_file`` redirect the on-disk queue. No live services touched
    when all three are provided.

    Returns ``{"fed", "skipped", "candidates", "task_ids"}``.
    """
    fetch = fetch or _default_fetch
    tasks_path = tasks_file or TASKS_FILE
    lock_path = lock_file or LOCK_FILE

    raw = fetch()
    candidates = [
        it
        for it in raw
        if it.get("type") == "improvement" and it.get("relevance") == "APPLY" and it.get("id")
    ]

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_fp:
        fcntl.flock(lock_fp, fcntl.LOCK_EX)
        try:
            tasks: list[dict[str, Any]] = (
                json.loads(tasks_path.read_text()) if tasks_path.exists() else []
            )
            existing_ids = {t.get("source_item_id") for t in tasks if t.get("source_item_id")}
            next_id = max((t["id"] for t in tasks if isinstance(t.get("id"), int)), default=0) + 1

            fed_ids: list[int] = []
            skipped = 0
            for item in candidates:
                if len(fed_ids) >= limit:
                    break
                if item["id"] in existing_ids:
                    skipped += 1
                    continue
                task = _item_to_task(item, next_id)
                tasks.append(task)
                existing_ids.add(item["id"])
                fed_ids.append(next_id)
                next_id += 1

            if fed_ids:
                tmp = tasks_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(tasks, indent=2))
                os.replace(tmp, tasks_path)
        finally:
            fcntl.flock(lock_fp, fcntl.LOCK_UN)

    return {
        "fed": len(fed_ids),
        "skipped": skipped,
        "candidates": len(candidates),
        "task_ids": fed_ids,
    }
