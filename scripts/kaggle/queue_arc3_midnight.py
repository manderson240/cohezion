#!/usr/bin/env python3
"""Midnight UTC ARC-AGI-3 Submitter & Watcher.

Waits until 00:00:05 UTC, then automatically dispatches the verified
ARC-AGI-3 Kernel v10 submission via the official submission engine.
"""
import datetime
import subprocess
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

def get_seconds_until_midnight_utc():
    now = datetime.datetime.now(datetime.timezone.utc)
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    return int((midnight - now).total_seconds())

def main():
    wait_sec = get_seconds_until_midnight_utc()
    logging.info("Midnight ARC-3 Submitter initialized. Waiting %d seconds until 00:00:05 UTC...", wait_sec)
    
    # Sleep in chunks to allow graceful signals and progress logging
    while True:
        wait_sec = get_seconds_until_midnight_utc()
        if wait_sec <= 0:
            break
        sleep_dur = min(wait_sec, 300)
        time.sleep(sleep_dur)
        if wait_sec > 300:
            now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            logging.info("Current UTC: %s | Remaining wait: %d seconds (%0.1f hours)", now_utc, wait_sec, wait_sec/3600.0)

    logging.info("Midnight UTC reached! Triggering ARC-AGI-3 kernel submission...")
    
    cmd = [
        ".venv/bin/python3", "scripts/kaggle/kaggle_submit.py", "notebook",
        "-c", "arc-prize-2026-arc-agi-3",
        "-k", "manderson240/cohezion-arc-agi-3-autoharness-solver",
        "-f", "submission.parquet",
        "-m", "Cohezion ARC-AGI-3 SOTA v31: Monadic Markov Engine + 64-bit Zobrist Anti-Cycle (Daily Quota Reset)",
        "-w"
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    logging.info("Submission return code: %d", res.returncode)
    logging.info("Stdout: %s", res.stdout)
    if res.stderr:
        logging.warning("Stderr: %s", res.stderr)

if __name__ == "__main__":
    main()
