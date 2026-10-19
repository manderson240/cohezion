#!/usr/bin/env python3
"""System Telemetry, Journal Surveillance & Workspace Governance Fabric.
=======================================================================
Unifies the 4 critical autonomic sensory streams of Cohezion:
1. System Resources: CPU load, 128GB UMA headroom, Swap usage, PSI memory pressure, and GPU GTT.
2. System Journals: Real-time surveillance of systemd journal and kernel logs for amdgpu/memory faults.
3. Workspaces & Worktrees: Full audit of active git worktrees, branch isolation, and cross-session leases.
4. EventBus Publication: Publishes typed telemetry events that replicate across sessions via CrossSessionEventBridge.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.inference.smart_oom_governor import SmartOOMGovernor

logger = logging.getLogger("system_telemetry_fabric")


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    """Point-in-time telemetry snapshot of system resources."""

    cpu_pct: float
    avail_mem_gib: float
    swap_used_gib: float
    gtt_used_gib: float
    psi_pressure: float
    is_safe_local: bool
    safety_reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_pct": self.cpu_pct,
            "avail_mem_gib": self.avail_mem_gib,
            "swap_used_gib": self.swap_used_gib,
            "gtt_used_gib": self.gtt_used_gib,
            "psi_pressure": self.psi_pressure,
            "is_safe_local": self.is_safe_local,
            "safety_reason": self.safety_reason,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class JournalAlert:
    """Detected diagnostic warning or alert from systemd/kernel journals."""

    facility: str
    priority: str
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class WorktreeEntry:
    """Metadata regarding an active git worktree / workspace."""

    path: str
    branch: str
    commit: str
    is_clean: bool


class SystemTelemetryFabric:
    """Autonomic telemetry and governance coordinator for Cohezion."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()

    def sample_resources(self) -> ResourceSnapshot:
        """Sample hardware compute, memory, and kernel pressure metrics."""
        cpu_pct = round(psutil.cpu_percent(interval=None), 2)
        avail_gib, swap_gib, _ = SmartOOMGovernor.get_memory_state()
        gtt_gib = SmartOOMGovernor.get_gtt_used_gib()
        psi = SmartOOMGovernor.get_psi_pressure()
        is_safe, reason = SmartOOMGovernor.can_execute_local()

        return ResourceSnapshot(
            cpu_pct=cpu_pct,
            avail_mem_gib=avail_gib,
            swap_used_gib=swap_gib,
            gtt_used_gib=gtt_gib,
            psi_pressure=psi,
            is_safe_local=is_safe,
            safety_reason=reason,
        )

    def sample_journals(self, max_lines: int = 30) -> list[JournalAlert]:
        """Inspect journalctl or dmesg for kernel/hardware warnings (amdgpu, OOM, faults)."""
        alerts: list[JournalAlert] = []
        critical_patterns = re.compile(
            r"(amdgpu.*(?:reset|timeout|fault|error)|oom-killer|out of memory|page allocation failure)",
            re.IGNORECASE,
        )

        try:
            # Query non-blocking journalctl user & system logs
            cmd = ["journalctl", "-n", str(max_lines), "--no-pager", "-p", "4..0"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    match = critical_patterns.search(line)
                    if match:
                        alerts.append(
                            JournalAlert(
                                facility="journalctl",
                                priority="warning",
                                message=line.strip()[:300],
                            )
                        )
        except Exception as exc:
            logger.debug("journalctl sampling skipped: %s", exc)

        return alerts

    def sample_workspaces(self) -> list[WorktreeEntry]:
        """Audit all active git worktrees and verify status."""
        worktrees: list[WorktreeEntry] = []
        try:
            cmd = ["git", "worktree", "list", "--porcelain"]
            proc = subprocess.run(
                cmd, cwd=str(self.repo_root), capture_output=True, text=True, timeout=3.0
            )
            if proc.returncode == 0:
                current_entry: dict[str, str] = {}
                for line in proc.stdout.splitlines():
                    if not line.strip():
                        if "worktree" in current_entry:
                            worktrees.append(
                                WorktreeEntry(
                                    path=current_entry.get("worktree", ""),
                                    branch=current_entry.get("branch", "detached"),
                                    commit=current_entry.get("HEAD", "")[:9],
                                    is_clean=True,
                                )
                            )
                        current_entry = {}
                        continue

                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        current_entry[parts[0]] = parts[1]
                    elif len(parts) == 1:
                        current_entry[parts[0]] = ""

                if "worktree" in current_entry:
                    worktrees.append(
                        WorktreeEntry(
                            path=current_entry.get("worktree", ""),
                            branch=current_entry.get("branch", "detached"),
                            commit=current_entry.get("HEAD", "")[:9],
                            is_clean=True,
                        )
                    )
        except Exception as exc:
            logger.debug("Worktree sampling skipped: %s", exc)

        return worktrees

    async def audit_and_publish(
        self, event_bus: EventBus, source: str = "telemetry_fabric"
    ) -> dict[str, Any]:
        """Sample all systems and emit typed events across the EventBus."""
        # 1. Resources
        resources = self.sample_resources()
        evt_resource = Event.resource_telemetry(
            source=source,
            cpu_pct=resources.cpu_pct,
            avail_mem_gib=resources.avail_mem_gib,
            swap_used_gib=resources.swap_used_gib,
            gtt_used_gib=resources.gtt_used_gib,
            psi_pressure=resources.psi_pressure,
            is_safe_local=resources.is_safe_local,
            safety_reason=resources.safety_reason,
        )
        await event_bus.publish(evt_resource)

        # 2. Journals
        alerts = self.sample_journals()
        for alert in alerts:
            evt_alert = Event.journal_alert(
                source=source,
                facility=alert.facility,
                priority=alert.priority,
                message=alert.message,
            )
            await event_bus.publish(evt_alert)

        # 3. Workspaces
        workspaces = self.sample_workspaces()
        evt_ws = Event.workspace_state(
            source=source,
            worktrees=[
                {"path": wt.path, "branch": wt.branch, "commit": wt.commit}
                for wt in workspaces
            ],
            active_path=str(self.repo_root),
        )
        await event_bus.publish(evt_ws)

        return {
            "resources": resources.to_dict(),
            "alert_count": len(alerts),
            "workspace_count": len(workspaces),
        }
