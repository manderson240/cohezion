#!/usr/bin/env python3
"""G1 Submission Queue Manager for Team Gamma.

Manages popcorn-cli submission queue with:
- 3 concurrent submission limit
- Off-peak scheduling (06:00-12:00 UTC)
- Test → Benchmark → Leaderboard pipeline
- Result tracking and retry logic
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SubmissionQueueManager:
    """Manages popcorn-cli submission queue."""

    QUEUE_LIMIT = 3
    OFF_PEAK_START = 6  # 06:00 UTC
    OFF_PEAK_END = 12  # 12:00 UTC
    PEAK_START = 14  # 14:00 UTC
    PEAK_END = 20  # 20:00 UTC

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.queue_file = workspace / "queue" / "submission_queue.json"
        self.schedule_file = workspace / "queue" / "schedule.json"
        self.results_dir = workspace / "results"
        self.logs_dir = workspace / "logs"

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status."""
        queue_data = json.loads(self.queue_file.read_text())
        active_count = len(queue_data.get("active", []))
        pending_count = len(queue_data.get("queue", []))
        completed_count = len(queue_data.get("completed", []))
        failed_count = len(queue_data.get("failed", []))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_limit": self.QUEUE_LIMIT,
            "active_submissions": active_count,
            "pending_submissions": pending_count,
            "completed_submissions": completed_count,
            "failed_submissions": failed_count,
            "available_slots": max(0, self.QUEUE_LIMIT - active_count),
            "status": "healthy" if active_count <= self.QUEUE_LIMIT else "overloaded",
        }

    def is_off_peak(self) -> bool:
        """Check if current time is in off-peak window."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        return self.OFF_PEAK_START <= hour < self.OFF_PEAK_END

    def is_peak(self) -> bool:
        """Check if current time is in peak hours."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        return self.PEAK_START <= hour < self.PEAK_END

    def get_next_window(self) -> str:
        """Get next optimal submission window."""
        now = datetime.now(timezone.utc)
        hour = now.hour

        if self.OFF_PEAK_START <= hour < self.OFF_PEAK_END:
            return "NOW (off-peak active)"
        elif hour < self.OFF_PEAK_START:
            return f"{self.OFF_PEAK_START:02d}:00 UTC today"
        else:
            return f"{self.OFF_PEAK_START:02d}:00 UTC tomorrow"

    def check_active_processes(self) -> list[dict[str, str]]:
        """Check running popcorn-cli processes."""
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True,
            )
            processes = []
            for line in result.stdout.split("\n"):
                if "popcorn-cli" in line and "grep" not in line:
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append(
                            {
                                "pid": parts[1],
                                "cpu": parts[2],
                                "mem": parts[3],
                                "time": parts[9],
                                "command": " ".join(parts[10:]),
                            }
                        )
            return processes
        except subprocess.CalledProcessError:
            return []

    def generate_dashboard(self) -> str:
        """Generate queue status dashboard."""
        status = self.get_queue_status()
        active_procs = self.check_active_processes()

        dashboard = f"""
╔══════════════════════════════════════════════════════════════════╗
║           G1 SUBMISSION QUEUE DASHBOARD - Team Gamma             ║
╠══════════════════════════════════════════════════════════════════╣
║ Timestamp: {status["timestamp"][:19]:<50} ║
╠══════════════════════════════════════════════════════════════════╣
║ QUEUE STATUS                                                     ║
║ ─────────────                                                    ║
║   Queue Limit:        {status["queue_limit"]:<3} submissions                          ║
║   Active:             {status["active_submissions"]:<3} submissions                          ║
║   Pending:            {status["pending_submissions"]:<3} submissions                          ║
║   Completed:          {status["completed_submissions"]:<3} submissions                          ║
║   Failed:             {status["failed_submissions"]:<3} submissions                          ║
║   Available Slots:    {status["available_slots"]:<3}                              ║
║   Status:             {status["status"]:<20}                    ║
╠══════════════════════════════════════════════════════════════════╣
║ TIME WINDOW                                                      ║
║ ───────────                                                      ║
║   Off-peak:           06:00-12:00 UTC (OPTIMAL)                  ║
║   Peak hours:         14:00-20:00 UTC (AVOID)                    ║
║   Current:            {datetime.now(timezone.utc).strftime("%H:%M UTC"):<20}                    ║
║   Off-peak now?       {"YES - OPTIMAL" if self.is_off_peak() else "NO":<20}                    ║
║   Next window:        {self.get_next_window():<20}                    ║
╠══════════════════════════════════════════════════════════════════╣
║ ACTIVE PROCESSES ({len(active_procs)})                                               ║
║ ──────────────────                                               ║
"""
        if active_procs:
            for proc in active_procs[:5]:
                dashboard += f"║   PID {proc['pid']:<8} CPU {proc['cpu']:<6} MEM {proc['mem']:<6} {proc['time']:<8} ║\n"
        else:
            dashboard += "║   No active popcorn-cli processes                                ║\n"

        dashboard += "╚══════════════════════════════════════════════════════════════════╝"
        return dashboard

    def submit_job(
        self,
        leaderboard: str,
        mode: str,
        kernel_dir: Path,
        priority: int = 5,
    ) -> dict[str, Any]:
        """Queue a new submission job."""
        job = {
            "id": f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "leaderboard": leaderboard,
            "mode": mode,
            "kernel_dir": str(kernel_dir),
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "submitted_at": None,
            "completed_at": None,
            "result": None,
        }

        queue_data = json.loads(self.queue_file.read_text())
        queue_data["queue"].append(job)
        queue_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.queue_file.write_text(json.dumps(queue_data, indent=2))

        return job

    def process_queue(self) -> list[dict[str, Any]]:
        """Process pending submissions if slots available."""
        processed = []
        queue_data = json.loads(self.queue_file.read_text())
        active_count = len(queue_data.get("active", []))

        available_slots = self.QUEUE_LIMIT - active_count
        if available_slots <= 0:
            return processed

        # Sort by priority (lower = higher priority)
        pending = sorted(
            queue_data.get("queue", []),
            key=lambda x: x.get("priority", 5),
        )

        for job in pending[:available_slots]:
            job["status"] = "active"
            job["submitted_at"] = datetime.now(timezone.utc).isoformat()
            queue_data["active"].append(job)
            queue_data["queue"].remove(job)
            processed.append(job)

        queue_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.queue_file.write_text(json.dumps(queue_data, indent=2))

        return processed


def main() -> None:
    """Main entry point."""
    workspace = Path(
        "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/opencode_infinity/teams/gamma/agents/g1"
    )
    manager = SubmissionQueueManager(workspace)

    print(manager.generate_dashboard())

    # Save dashboard to file
    dashboard_file = workspace / "logs" / "dashboard.txt"
    dashboard_file.write_text(manager.generate_dashboard())
    print(f"\nDashboard saved to: {dashboard_file}")


if __name__ == "__main__":
    main()
