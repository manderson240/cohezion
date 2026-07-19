"""Durable, inspectable goal state — `cat` answers "what am I working toward?".

WHY (2026-07-18): a session-scoped Stop-hook goal ("no more OOM") worked well — it blocked
completion and returned evidence-based feedback each turn. But that state lived only inside
the hook. Nothing on disk answered "what is the current goal, and is it converging?", so
the goal could not survive a restart, could not be inspected mid-run, and left no record of
WHY it was eventually satisfied.

Companion to `enqueue.py`, which closes the hook->daemon gap. Together: the hook enqueues
work, the daemon does it, and the goal records what the work is FOR.

Deliberately NOT a new hook. Tonight's audit found ~30 hooks already registered and the
real defects were all UNWIRED INTERFACES between working components, not missing triggers.
Adding a mechanism where an interface is missing is how the 96-triggers-0-completions gap
was created in the first place.

stdlib only, atomic writes, fail-silent — same constraints as enqueue.py, for the same
reason: this is called from hook context.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


STATE_DIR = Path.home() / ".cohezion"
GOAL_FILE = STATE_DIR / "goal_state.json"
MAX_OBSERVATIONS = 100  # bounded: a long-running goal must not grow the file without limit


def _now() -> float:
    return time.time()


def set_goal(condition: str, *, source: str = "user") -> bool:
    """Start tracking a goal. Replaces any active goal, archiving it first."""
    condition = (condition or "").strip()
    if not condition:
        return False
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = _read()
        archive = state.get("archive", [])
        if state.get("condition") and state.get("condition") != condition:
            archive.append(
                {
                    "condition": state["condition"],
                    "started_at": state.get("started_at"),
                    "ended_at": _now(),
                    "satisfied": state.get("satisfied", False),
                    "observations": len(state.get("observations", [])),
                }
            )
        return _write(
            {
                "condition": condition,
                "source": source,
                "started_at": _now(),
                "satisfied": False,
                "observations": [],
                "archive": archive[-20:],
            }
        )
    except (OSError, ValueError):
        return False


def observe(note: str, *, satisfied: bool | None = None) -> bool:
    """Record evidence about the active goal.

    `satisfied` is TRI-STATE on purpose. None means "evidence recorded, verdict unchanged" —
    which is the honest state for most observations. Collapsing that to False would make
    "we checked and it is not met" indistinguishable from "we have not checked", the same
    fail-open ambiguity that hid three separate defects tonight.
    """
    note = (note or "").strip()
    if not note:
        return False
    try:
        state = _read()
        if not state.get("condition"):
            return False
        obs = state.get("observations", [])
        obs.append({"at": _now(), "note": note[:500], "satisfied": satisfied})
        state["observations"] = obs[-MAX_OBSERVATIONS:]
        if satisfied is not None:
            state["satisfied"] = satisfied
            if satisfied:
                state["satisfied_at"] = _now()
        return _write(state)
    except (OSError, ValueError):
        return False


def status() -> dict:
    """Current goal state. Always returns a dict; `condition` is "" when none is active."""
    s = _read()
    obs = s.get("observations", [])
    started = s.get("started_at")
    return {
        "condition": s.get("condition", ""),
        "satisfied": s.get("satisfied", False),
        "observations": len(obs),
        "age_hours": round((_now() - started) / 3600, 2) if started else 0.0,
        "last_note": obs[-1]["note"] if obs else "",
        "archived": len(s.get("archive", [])),
    }


def _read() -> dict:
    try:
        loaded = json.loads(GOAL_FILE.read_text())
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(state: dict) -> bool:
    tmp = GOAL_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(tmp, GOAL_FILE)  # atomic: a crash mid-write cannot truncate the goal
    return True


def main() -> int:
    """CLI:  python3 -m cohezion.compound.goal_state [set <cond> | observe <note> | status]"""
    import sys

    args = sys.argv[1:]
    if not args or args[0] == "status":
        s = status()
        if not s["condition"]:
            print("no active goal")
            return 0
        mark = "SATISFIED" if s["satisfied"] else "open"
        print(f"[{mark}] {s['condition']}")
        print(f"  {s['observations']} observations over {s['age_hours']}h")
        if s["last_note"]:
            print(f"  last: {s['last_note'][:120]}")
        return 0
    if args[0] == "set" and len(args) > 1:
        print("ok" if set_goal(" ".join(args[1:])) else "failed")
        return 0
    if args[0] == "observe" and len(args) > 1:
        print("ok" if observe(" ".join(args[1:])) else "failed (no active goal?)")
        return 0
    print("usage: set <condition> | observe <note> | status")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
