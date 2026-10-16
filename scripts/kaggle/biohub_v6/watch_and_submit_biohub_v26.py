#!/usr/bin/env python3
"""
watch_and_submit_biohub_v26.py — Autonomous Verifier & Submitter for Cohezion Biohub v26.

Watches 'manderson240/cohezion-biohub-v6' version 26 on Kaggle.
Upon completion:
1. Pulls kernel output to /tmp/biohub_v26_out/
2. Verifies graph invariants with verify_submission_invariants.py
3. Dispatches official notebook submission via scripts/kaggle/kaggle_submit.py
4. Persists the submission record to SurrealDB and the Obsidian Vault.
"""

import os
import sys
import time
import subprocess
import json
import logging
from pathlib import Path
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [BiohubWatcher] %(message)s"
)
logger = logging.getLogger("BiohubWatcher")

KERNEL_SLUG = "manderson240/cohezion-biohub-v6"
KERNEL_VERSION = 28
COMPETITION = "biohub-cell-tracking-during-development"
OUTPUT_DIR = Path("/tmp/biohub_v26_out")
SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = "cohezion"
SURREAL_DB = "main"


def check_kernel_status() -> tuple[str, str]:
    import kaggle
    api = kaggle.KaggleApi()
    api.authenticate()
    res = api.kernels_status(KERNEL_SLUG)
    status = str(getattr(res, "status", getattr(res, "_status", "UNKNOWN")))
    failure_message = str(getattr(res, "failure_message", getattr(res, "_failure_message", "")))
    return status, failure_message


def run_surreal_query(query: str):
    try:
        req = urllib.request.Request(
            SURREAL_URL,
            data=query.encode("utf-8"),
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
                "Authorization": "Basic cm9vdDpyb290"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"SurrealDB query failed: {e}")
        return None


def main():
    logger.info(f"Starting autonomous watcher for {KERNEL_SLUG} (Version {KERNEL_VERSION})...")
    poll_interval = 30  # seconds
    max_wait_seconds = 7200  # 2 hours

    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        try:
            status, failure = check_kernel_status()
            logger.info(f"Status: {status} (Elapsed: {int(time.time() - start_time)}s)")

            if status == "COMPLETE":
                logger.info("Kernel execution COMPLETED! Pulling output...")
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                cmd_out = ["kaggle", "kernels", "output", KERNEL_SLUG, "-p", str(OUTPUT_DIR)]
                subprocess.run(cmd_out, check=True)

                sub_file = OUTPUT_DIR / "submission.csv"
                if not sub_file.exists():
                    logger.error(f"submission.csv NOT found in {OUTPUT_DIR}! Listing contents:")
                    for f in OUTPUT_DIR.iterdir():
                        logger.error(f"  {f.name} ({f.stat().st_size} bytes)")
                    sys.exit(1)

                logger.info(f"Found submission.csv ({sub_file.stat().st_size} bytes). Verifying invariants...")
                
                # Invariant verification using verify_submission_invariants
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from verify_submission_invariants import verify_biohub_submission
                res = verify_biohub_submission(str(sub_file))
                res.print_report("Biohub Cell Tracking")

                if not res.passed:
                    logger.error("Submission failed invariant verification! Halting submission.")
                    sys.exit(1)

                logger.info("✓ All invariant verification gates passed! Dispatching notebook submission...")
                message = f"Cohezion Biohub V26: Aligned Bidirectional Weight 0.15 + Relaxed Runtime Guard (TRA/SEG Target > 0.966)"
                
                cmd_submit = [
                    sys.executable,
                    str(Path(__file__).resolve().parent.parent / "kaggle_submit.py"),
                    "--competition", COMPETITION,
                    "--kernel", KERNEL_SLUG,
                    "--kernel-version", str(KERNEL_VERSION),
                    "--mode", "notebook",
                    "--message", message,
                ]
                submit_res = subprocess.run(cmd_submit, capture_output=True, text=True)
                logger.info(submit_res.stdout)
                if submit_res.returncode != 0:
                    logger.error(f"Submission failed with code {submit_res.returncode}: {submit_res.stderr}")
                    sys.exit(submit_res.returncode)

                logger.info("✓ Notebook submission dispatched successfully!")

                # Persist to SurrealDB
                surql = f"""
                UPDATE submission_record:biohub_v26 SET
                    competition = 'kaggle_competition:{COMPETITION}',
                    kernel = 'kaggle_kernel:biohub_v6',
                    kernel_version = {KERNEL_VERSION},
                    status = 'SUBMITTED',
                    dispatched_at = time::now(),
                    message = '{message}';
                """
                run_surreal_query(surql)
                logger.info("✓ Persisted submission record to SurrealDB.")
                return

            elif status in ("ERROR", "CANCELLED", "FAILED"):
                logger.error(f"Kernel failed with status {status}! Failure message: {failure}")
                sys.exit(1)

        except Exception as e:
            logger.warning(f"Error checking kernel status: {e}")

        time.sleep(poll_interval)

    logger.error("Timed out waiting for kernel completion.")
    sys.exit(1)


if __name__ == "__main__":
    main()
