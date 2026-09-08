#!/usr/bin/env python3
"""Checks and synchronizes messages across the Claude Code agent inboxes and SurrealDB."""

import os
import json
import glob
from pathlib import Path


def inspect_inboxes():
    harness_path = Path.home() / ".munder-difflin" / "harness" / "hive" / "agents"
    print("=" * 80)
    print("📬 INSPECTING CLAUDE CODE & HIVE AGENT INBOXES")
    print("=" * 80)

    if not harness_path.exists():
        print(f"No harness directory at {harness_path}")
        return

    agent_dirs = [d for d in harness_path.iterdir() if d.is_dir()]
    for agent in agent_dirs:
        inbox_files = list((agent / "inbox").glob("*.json"))
        outbox_files = list((agent / "outbox").glob("*.json"))
        print(
            f"• Agent: [{agent.name}] — {len(inbox_files)} inbox msgs | {len(outbox_files)} outbox msgs"
        )
        for f in inbox_files:
            try:
                data = json.loads(f.read_text())
                print(
                    f'   📥 [FROM: {data.get("from")} -> {data.get("to")}] Subject: "{data.get("subject")}"'
                )
                print(f"      Body: {data.get('body')[:140]}...")
            except Exception as e:
                print(f"   Notice reading {f.name}: {e}")


if __name__ == "__main__":
    inspect_inboxes()
