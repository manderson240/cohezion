#!/usr/bin/env python3
"""
Cohezion Daemon Status Inspector
================================
Inspects active background daemons, systemd services, and shared daemon state files.
"""

from __future__ import annotations

import json
from pathlib import Path

STATE_DIR = Path.home() / ".cohezion" / "compound_state"
DAEMON_LOG = STATE_DIR / "compound_daemon.log"
TASKS_JSON = STATE_DIR / "compound_tasks.json"


def main():
    print("=== Cohezion Background Daemon Inspection ===")

    print(f"\n1. State Directory: {STATE_DIR}")
    if STATE_DIR.exists():
        print("   ✓ State directory exists")
    else:
        print("   • State directory not yet created")

    if TASKS_JSON.exists():
        try:
            tasks = json.loads(TASKS_JSON.read_text())
            print(f"   ✓ Daemon tasks file contains {len(tasks)} items")
            pending = [t for t in tasks if not t.get("done")]
            print(f"   • Pending tasks: {len(pending)}")
        except Exception as e:
            print("   ! Error reading tasks:", e)
    else:
        print("   • Tasks file absent")

    if DAEMON_LOG.exists():
        lines = DAEMON_LOG.read_text().splitlines()[-5:]
        print("\n2. Recent Daemon Log Output:")
        for line in lines:
            print(f"   | {line}")
    else:
        print("\n2. Daemon Log: (No recent log file on disk)")


if __name__ == "__main__":
    main()
