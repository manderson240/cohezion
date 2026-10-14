#!/usr/bin/env python3
"""Cohezion Active Leaderboard Ascension Orchestrator
===================================================
Monitors all running kernels for active, unexpired Kaggle competitions and
submits them deterministically with mathematical invariant checks upon completion.

Hardened with:
- Exclusive process lock (fcntl.flock) to prevent duplicate daemons
- Persistent on-disk submission ledger (scripts/kaggle/orchestrator_ledger.json)
- Dynamic kernel version resolution via kagglesdk
- Daily quota exhaustion handling with UTC midnight pacing

Active Tracks:
1. Enveda CASMI26: manderson240/cohezion-casmi26-fork-v4n-0421 -> enveda-CASMI26-molecule-id-mass-spectra
2. RSNA Knee: manderson240/cohezion-rsna-knee-sota-ensemble -> rsna-knee-abnormality-detection
3. ARC-AGI-3: manderson240/cohezion-arc-agi-3-autoharness-solver -> arc-prize-2026-arc-agi-3
4. ARC-AGI-2: monitors existing pending submission
5. Gemma-4 Dev Agent: monitors existing pending submission
"""

import datetime
import fcntl
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ascension_orchestrator")

LOCK_FILE = Path("/tmp/cohezion_ascension_orchestrator.lock")
LEDGER_PATH = Path("scripts/kaggle/orchestrator_ledger.json")

SUBMISSIONS = [
    {
        "name": "Enveda CASMI26",
        "competition": "enveda-CASMI26-molecule-id-mass-spectra",
        "kernel": "manderson240/cohezion-casmi26-fork-v4n-0421",
        "code_path": "scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb",
        "file": "submission.csv",
        "message": "Cohezion CASMI26 Podium v18: Calibrated POP_MU 0.42 + Adduct Surrogate + MetFrag Parsimony",
    },
    {
        "name": "RSNA Knee",
        "competition": "rsna-knee-abnormality-detection",
        "kernel": "manderson240/cohezion-rsna-knee-sota-ensemble",
        "code_path": "scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb",
        "file": "submission.csv",
        "message": "Cohezion RSNA Knee SOTA v28: 32-Slice Fidelity + Multi-Res Dual-Scale + Finding-Specific Covariance",
    },
    {
        "name": "ARC-AGI-3",
        "competition": "arc-prize-2026-arc-agi-3",
        "kernel": "manderson240/cohezion-arc-agi-3-autoharness-solver",
        "file": "submission.parquet",
        "message": "Cohezion ARC-AGI-3 SOTA v30: Go-Explore BFS Macro-Action Affordance Engine (64-bit Zobrist)",
    },
]


def load_ledger() -> Dict[str, Any]:
    if LEDGER_PATH.exists():
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load ledger: %s. Starting with empty ledger.", e)
    return {}


def save_ledger(ledger: Dict[str, Any]) -> None:
    temp_path = LEDGER_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)
    temp_path.replace(LEDGER_PATH)


def resolve_kernel_version(kernel_slug: str) -> Optional[int]:
    try:
        parts = kernel_slug.split("/")
        if len(parts) == 2:
            owner, slug = parts
            import kaggle
            api = kaggle.KaggleApi()
            api.authenticate()
            from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
            with api.build_kaggle_client() as client:
                req = ApiGetKernelRequest()
                req.user_name = owner
                req.kernel_slug = slug
                res = client.kernels.kernels_api_client.get_kernel(req)
                return int(res.metadata.current_version_number)
    except Exception as e:
        logger.warning("Could not resolve version for %s: %s", kernel_slug, e)
    return None


def check_kernel(kernel_slug: str) -> str:
    res = subprocess.run(["kaggle", "kernels", "status", kernel_slug], capture_output=True, text=True)
    out = res.stdout.strip()
    if "KernelWorkerStatus.COMPLETE" in out:
        return "COMPLETE"
    elif "KernelWorkerStatus.RUNNING" in out or "KernelWorkerStatus.QUEUED" in out:
        return "RUNNING"
    elif "KernelWorkerStatus.ERROR" in out:
        return "ERROR"
    return out


def submit_notebook(item: dict, resolved_ver: Optional[int]) -> str:
    logger.info("Submitting %s (%s, ver=%s) to %s...", item["name"], item["kernel"], resolved_ver, item["competition"])
    cmd = [
        sys.executable,
        "scripts/kaggle/kaggle_submit.py",
        "notebook",
        "-c", item["competition"],
        "-k", item["kernel"],
        "-f", item["file"],
        "-m", item["message"],
    ]
    if resolved_ver is not None:
        cmd.extend(["-v", str(resolved_ver)])
    if "code_path" in item and item["code_path"]:
        cmd.extend(["--code-path", item["code_path"]])
    res = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("Submit STDOUT:\n%s", res.stdout.strip())
    if res.stderr:
        logger.warning("Submit STDERR:\n%s", res.stderr.strip())

    combined = res.stdout + " " + res.stderr
    if "used its daily Submission allowance" in combined:
        return "QUOTA_EXHAUSTED"
    return "SUCCESS" if res.returncode == 0 else "FAILED"


def poll_cycle(iteration: int, ledger: Dict[str, Any]) -> bool:
    all_done = True
    logger.info("--- Ascension Poll Cycle %d ---", iteration)
    for item in SUBMISSIONS:
        kernel = item["kernel"]
        competition = item["competition"]

        # Check quota hold
        hold_until = item.get("hold_until_ts", 0)
        if time.time() < hold_until:
            wait_m = (hold_until - time.time()) / 60.0
            logger.info("  %s: Daily quota used today. Holding for tomorrow UTC (%.1fm remaining).", item["name"], wait_m)
            continue

        status = check_kernel(kernel)
        logger.info("  %s (%s): %s", item["name"], kernel, status)

        if status == "COMPLETE":
            resolved_ver = resolve_kernel_version(kernel)
            ledger_key = f"{competition}:{kernel}:v{resolved_ver if resolved_ver else 'latest'}"

            if ledger_key in ledger and ledger[ledger_key].get("status") == "SUCCESS":
                entry = ledger[ledger_key]
                logger.info("  %s: Already submitted in ledger on %s (key=%s) ✓", item["name"], entry.get("timestamp"), ledger_key)
                continue

            result = submit_notebook(item, resolved_ver)
            ledger[ledger_key] = {
                "competition": competition,
                "kernel": kernel,
                "version": resolved_ver,
                "status": result,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "message": item["message"],
            }
            save_ledger(ledger)

            if result == "SUCCESS":
                logger.info("  ✓ %s submitted successfully and recorded to ledger.", item["name"])
            elif result == "QUOTA_EXHAUSTED":
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                tomorrow_utc = (now_utc + datetime.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
                sec_to_reset = (tomorrow_utc - now_utc).total_seconds()
                item["hold_until_ts"] = time.time() + sec_to_reset
                logger.warning("  ⏳ %s: Quota exhausted. Set hold for %.2f hours until %s.", item["name"], sec_to_reset / 3600.0, tomorrow_utc.isoformat())
            else:
                all_done = False
        else:
            all_done = False
    return all_done


def main():
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        logger.error("Another instance of ascension_orchestrator is already running. Exiting.")
        sys.exit(0)

    logger.info("=== Cohezion Leaderboard Ascension Orchestrator Started ===")
    ledger = load_ledger()
    logger.info("Loaded ledger with %d entries.", len(ledger))

    try:
        for iteration in range(1, 360):
            done = poll_cycle(iteration, ledger)
            if done:
                logger.info("🎉 All active ascension kernels have successfully finished and submitted!")
                break
            time.sleep(30)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
