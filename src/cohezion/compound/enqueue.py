"""Bridge the compound-self-improve hook to the compound daemon's task queue.

THE GAP THIS CLOSES (found 2026-07-18): `~/.claude/hooks/compound-self-improve.sh` fires
on every file edit and had logged **96 TRIGGERED events with 0 completions**. The daemon
woke every 30 minutes, read `~/.cohezion/compound_tasks.json`, found "No pending tasks",
and slept. Both components worked; nothing connected them. The hook wrote a log line; the
daemon read a queue; no code bridged the two.

This is the wire-at-creation failure in its purest form -- a producer with no consumer
looks exactly like a quiet, healthy system.

DESIGN:
  * stdlib only, no cohezion imports. This is called from a shell hook that must survive a
    half-broken venv, and an import error here would silently re-open the same gap.
  * Advisory-locked (fcntl) read-modify-write. The hook can fire concurrently with the
    daemon's own save_tasks(); an unlocked RMW loses tasks, which would look identical to
    "the bridge doesn't work".
  * Deduplicated by prompt within DEDUP_WINDOW_HOURS. 96 triggers over one session were
    mostly repeat edits to the same file; enqueuing each one would drown the queue in
    near-identical work and starve everything else.
  * Bounded queue. A runaway edit loop must not grow the file without limit.
  * Fail-SILENT by design: a hook that breaks the user's edit flow is worse than a missed
    task. Every failure path returns False rather than raising.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path


STATE_DIR = Path.home() / ".cohezion"
TASKS_FILE = STATE_DIR / "compound_tasks.json"
LOCK_FILE = STATE_DIR / "compound_tasks.lock"

DEDUP_WINDOW_HOURS = 6.0
MAX_PENDING = 40  # backstop: a runaway edit loop must not grow the queue unboundedly


def _now() -> float:
    return time.time()


def enqueue(prompt: str, priority: int = 5, source: str = "hook") -> bool:
    """Append a task if it is not a recent duplicate. Returns True if it was added.

    Matches the daemon's schema exactly: {id, prompt, priority, done}. Extra keys
    (created_at, source) are additive -- the daemon ignores what it does not read, and
    they make the queue auditable after the fact.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return False

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOCK_FILE.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                tasks: list[dict] = []
                if TASKS_FILE.exists():
                    try:
                        loaded = json.loads(TASKS_FILE.read_text())
                        if isinstance(loaded, list):
                            tasks = loaded
                    except (json.JSONDecodeError, OSError):
                        return False  # never clobber a queue we cannot parse

                cutoff = _now() - DEDUP_WINDOW_HOURS * 3600
                for t in tasks:
                    if t.get("prompt") != prompt:
                        continue
                    # A still-pending duplicate is always a duplicate. A completed one only
                    # counts inside the window, so recurring work can legitimately requeue.
                    if not t.get("done"):
                        return False
                    if float(t.get("created_at") or 0) >= cutoff:
                        return False

                if sum(1 for t in tasks if not t.get("done")) >= MAX_PENDING:
                    return False

                tasks.append(
                    {
                        "id": max((int(t.get("id", 0)) for t in tasks), default=0) + 1,
                        "prompt": prompt,
                        "priority": priority,
                        "done": False,
                        "created_at": _now(),
                        "source": source,
                    }
                )
                tmp = TASKS_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(tasks, indent=2))
                os.replace(tmp, TASKS_FILE)  # atomic: a crash mid-write cannot truncate
                return True
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except (OSError, ValueError):
        return False


def pending_count() -> int:
    """Pending tasks, or -1 if the queue is unreadable (distinguishable from empty)."""
    try:
        loaded = json.loads(TASKS_FILE.read_text())
        return sum(1 for t in loaded if not t.get("done")) if isinstance(loaded, list) else -1
    except (OSError, json.JSONDecodeError):
        return -1


def main() -> int:
    """CLI for the shell hook:  python3 -m cohezion.compound.enqueue "<prompt>" [priority]"""
    import sys

    if len(sys.argv) < 2:
        print(f"pending={pending_count()}")
        return 0
    prio = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    added = enqueue(sys.argv[1], prio, source="hook")
    print("ENQUEUED" if added else "SKIPPED(duplicate-or-full)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
