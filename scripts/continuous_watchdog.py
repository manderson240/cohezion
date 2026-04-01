#!/usr/bin/env python3
"""Token-efficient watchdog for 8.5hr autonomous operation until 7 AM EST."""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

TARGET = datetime(2026, 4, 1, 7, 0)  # 7 AM EST April 1
PID_FILE = Path("/tmp/autonomous_watchdog.pid")
STATE_FILE = Path("_bmad/_config/traceability/watchdog_state.json")


def now():
    return datetime.now()


def remaining():
    return (TARGET - now()).total_seconds()


def save_state(cycles, errors):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"cycles": cycles, "errors": errors, "last": now().isoformat()})
    )


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"cycles": 0, "errors": 0}


async def monitor():
    state = load_state()
    while remaining() > 0:
        # Check if main process alive
        proc = await asyncio.create_subprocess_exec(
            "pgrep",
            "-f",
            "autonomous_session_orchestrator_v3_continuous",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if not stdout.strip():
            # Restart
            subprocess.Popen(
                [sys.executable, "scripts/autonomous_session_orchestrator_v3_continuous.py"],
                stdout=open("autonomous_continuous.log", "a"),
                stderr=subprocess.STDOUT,
            )
            print(f"[{now().strftime('%H:%M')}] Restarted main process")

        # Git push every 30 min
        if now().minute % 30 == 0:
            subprocess.run(["git", "push", "origin", "main"], capture_output=True)

        # Save state
        save_state(state["cycles"], state["errors"])

        # Sleep 60s
        await asyncio.sleep(60)

    # Graceful shutdown at 6:55
    subprocess.run(["pkill", "-f", "autonomous_session_orchestrator_v3_continuous"])
    print(f"[{now().strftime('%H:%M')}] Target reached. Shutdown complete.")


if __name__ == "__main__":
    print(f"Watchdog active. Target: 7 AM EST ({remaining() / 3600:.1f} hours remaining)")
    asyncio.run(monitor())
