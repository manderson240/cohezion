#!/usr/bin/env python3
"""Persistent dev work tracker — crash-safe JSONL append-only store.

Cross-session work items survive crashes, context resets, and branch switches.
Store lives at ~/.cohezion/work-items.jsonl (append-only, one JSON object per line).

Usage:
    python scripts/work_tracker.py add "Title" [--tags tag1,tag2] [--branch BRANCH]
    python scripts/work_tracker.py list [--status open|done|blocked]
    python scripts/work_tracker.py done WK-NNN [--note "optional note"]
    python scripts/work_tracker.py block WK-NNN --reason "why"
    python scripts/work_tracker.py context  # SessionStart hook output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STORE = Path.home() / ".cohezion" / "work-items.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _load() -> list[dict]:
    if not STORE.exists():
        return []
    items: dict[str, dict] = {}
    for line in STORE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            wid = obj.get("id")
            if wid:
                items[wid] = obj  # later entries override — JSONL log compaction
        except json.JSONDecodeError:
            continue
    return list(items.values())


def _append(obj: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    with STORE.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def _next_id(items: list[dict]) -> str:
    existing = {int(i["id"].split("-")[1]) for i in items if i.get("id", "").startswith("WK-")}
    n = max(existing, default=0) + 1
    return f"WK-{n:03d}"


def cmd_add(args: argparse.Namespace) -> None:
    items = _load()
    wid = _next_id(items)
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    branch = args.branch or _git_branch()
    obj = {
        "id": wid,
        "title": args.title,
        "status": "open",
        "tags": tags,
        "branch": branch,
        "created": _now(),
        "updated": _now(),
    }
    _append(obj)
    print(f"Created {wid}: {args.title}")


def cmd_list(args: argparse.Namespace) -> None:
    items = _load()
    status_filter = args.status
    branch_filter = args.branch
    shown = 0
    for item in items:
        if status_filter and item.get("status") != status_filter:
            continue
        if branch_filter and item.get("branch") != branch_filter:
            continue
        status = item.get("status", "?")
        mark = {"open": "[ ]", "done": "[x]", "blocked": "[!]"}.get(status, "[?]")
        tags = ",".join(item.get("tags", []))
        tag_str = f" [{tags}]" if tags else ""
        branch = item.get("branch", "")
        branch_str = f" ({branch})" if branch else ""
        print(f"{mark} {item['id']}: {item['title']}{tag_str}{branch_str}")
        if item.get("note"):
            print(f"    note: {item['note']}")
        shown += 1
    if shown == 0:
        print("(no items)")


def cmd_done(args: argparse.Namespace) -> None:
    items = _load()
    found = next((i for i in items if i["id"] == args.id), None)
    if not found:
        print(f"Error: {args.id} not found", file=sys.stderr)
        sys.exit(1)
    updated = {**found, "status": "done", "updated": _now()}
    if args.note:
        updated["note"] = args.note
    _append(updated)
    print(f"Marked {args.id} done: {found['title']}")


def cmd_block(args: argparse.Namespace) -> None:
    items = _load()
    found = next((i for i in items if i["id"] == args.id), None)
    if not found:
        print(f"Error: {args.id} not found", file=sys.stderr)
        sys.exit(1)
    updated = {**found, "status": "blocked", "updated": _now(), "reason": args.reason}
    _append(updated)
    print(f"Blocked {args.id}: {found['title']}")


def cmd_context(args: argparse.Namespace) -> None:
    """Emit a lean context block for SessionStart injection."""
    items = _load()
    open_items = [i for i in items if i.get("status") == "open"]
    blocked = [i for i in items if i.get("status") == "blocked"]
    if not open_items and not blocked:
        return
    print("## Active Work Items (cross-session tracker)")
    branch = _git_branch()
    for item in open_items:
        branch_str = f" [{item.get('branch', '?')}]" if item.get("branch") != branch else ""
        print(f"  [ ] {item['id']}: {item['title']}{branch_str}")
    for item in blocked:
        print(f"  [!] {item['id']}: {item['title']} — BLOCKED: {item.get('reason', '?')}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cohezion dev work tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add a work item")
    p_add.add_argument("title")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--branch", default="")

    p_list = sub.add_parser("list", help="List work items")
    p_list.add_argument("--status", choices=["open", "done", "blocked"])
    p_list.add_argument("--branch")

    p_done = sub.add_parser("done", help="Mark item done")
    p_done.add_argument("id")
    p_done.add_argument("--note", default="")

    p_block = sub.add_parser("block", help="Mark item blocked")
    p_block.add_argument("id")
    p_block.add_argument("--reason", required=True)

    sub.add_parser("context", help="Emit SessionStart context block")

    args = parser.parse_args()
    {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "block": cmd_block,
        "context": cmd_context,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
