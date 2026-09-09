"""Kaggle High-ROI Autonomous Leaderboard Monitor.

Tracks:
1. ARC-AGI-3 ($850,000): manderson240/cohezion-arc-agi-3-autoharness-solver
2. ARC-AGI-2 ($700,000): manderson240/arc-agi-2-fork-subset16-20260903
Total Prize Pool Under Active Autonomous Execution: $1,550,000 USD.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time

from cohezion.core.event_bus import Event, EventBus
from cohezion.data_mesh.kanban_bridge import persist_item

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s",
)
logger = logging.getLogger("high_roi_monitor")

KERNELS = [
    {
        "name": "ARC-AGI-3 ($850k)",
        "ref": "manderson240/cohezion-arc-agi-3-autoharness-solver",
        "comp": "arc-prize-2026-arc-agi-3",
        "out_dir": "/tmp/arc3_kernel_output",
    },
    {
        "name": "ARC-AGI-2 ($700k)",
        "ref": "manderson240/arc-agi-2-fork-subset16-20260903",
        "comp": "arc-prize-2026-arc-agi-2",
        "out_dir": "/tmp/arc2_kernel_output",
    },
]

POLL_INTERVAL_SECONDS = 180


def get_status(ref: str) -> str:
    res = subprocess.run(
        ["uv", "run", "kaggle", "kernels", "status", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    out = res.stdout + res.stderr
    if "KernelWorkerStatus.COMPLETE" in out:
        return "COMPLETE"
    elif "KernelWorkerStatus.RUNNING" in out:
        return "RUNNING"
    elif "KernelWorkerStatus.QUEUED" in out:
        return "QUEUED"
    elif "KernelWorkerStatus.ERROR" in out:
        return "ERROR"
    return "UNKNOWN"


def main() -> None:
    logger.info("High-ROI Kaggle Autonomous Monitor initialized for $1.55M prize targets.")
    bus = EventBus()
    
    persist_item({
        "id": "kaggle-high-roi-dual-track",
        "title": "High-ROI Dual Track Monitor: ARC-AGI-3 ($850k) & ARC-AGI-2 ($700k)",
        "status": "in_progress",
        "priority": "critical",
        "source": "kaggle_high_roi_monitor",
        "category": "kaggle_competition",
        "description": "Continuous tracking of GPU inference and AutoHarness verification across the top two highest prize competitions on Kaggle.",
    })

    completed = set()

    while len(completed) < len(KERNELS):
        for k in KERNELS:
            ref = k["ref"]
            if ref in completed:
                continue
            status = get_status(ref)
            logger.info(f"[{k['name']}] {ref} -> {status}")
            
            if status == "COMPLETE":
                logger.info(f"[{k['name']}] Finished execution! Pulling output...")
                os.makedirs(k["out_dir"], exist_ok=True)
                subprocess.run(["uv", "run", "kaggle", "kernels", "output", ref, "-p", k["out_dir"]], check=False)
                sub_file = os.path.join(k["out_dir"], "submission.json")
                if os.path.exists(sub_file):
                    logger.info(f"[{k['name']}] Found valid submission file: {sub_file}")
                completed.add(ref)
            elif status == "ERROR":
                logger.error(f"[{k['name']}] Failed with ERROR.")
                completed.add(ref)
                
        time.sleep(POLL_INTERVAL_SECONDS)

    logger.info("All high-ROI targets evaluated and ingested.")


if __name__ == "__main__":
    main()
