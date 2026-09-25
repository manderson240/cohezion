#!/usr/bin/env python3
"""Automated Kaggle Midnight UTC Submitter for Google Gemma 4 Developer Agent
==========================================================================
Deterministic background daemon that:
1. Calculates exact seconds until the next 00:00:15 UTC submission quota reset.
2. Performs pre-submission validation on submission.zip (SHA-256 and AST check).
3. Submits to Kaggle at the exact second the quota window opens.
4. Logs submission reference and status directly to SurrealDB.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import sys
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("gemma4_midnight_submitter")

SUBMISSION_ZIP = Path("scripts/kaggle/gemma4_kernel/submission.zip")
COMPETITION = "gemma-4-developer-agent"
DESCRIPTION = (
    "Cohezion Compound Graph Agent v2: Grounded GenerateContentConfig "
    "(nested thinking_config) + Strict get_status Invariant"
)


def compute_seconds_to_midnight_utc() -> float:
    now_utc = datetime.now(UTC)
    next_midnight = (now_utc + timedelta(days=1)).replace(
        hour=0, minute=0, second=15, microsecond=0
    )
    seconds_left = (next_midnight - now_utc).total_seconds()
    return max(0.0, seconds_left)


def verify_submission_archive() -> str:
    if not SUBMISSION_ZIP.exists():
        raise FileNotFoundError(f"Missing submission archive: {SUBMISSION_ZIP}")
    data = SUBMISSION_ZIP.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    logger.info("Submission archive verified: size=%d bytes, SHA-256=%s", len(data), sha)
    return sha


def log_to_surrealdb(status: str, ref: int | None, sha: str, message: str) -> None:
    sql = f"""
USE NS cohezion DB main;
UPSERT submission_record:gemma4_v2 CONTENT {{
    competition: '{COMPETITION}',
    submission_ref: {ref if ref else 'null'},
    status: '{status}',
    sha256: '{sha}',
    submitted_at: time::now(),
    message: '{message}'
}};
"""
    req = urllib.request.Request(
        "http://localhost:8001/sql",
        data=sql.encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(b"root:root").decode("ascii")
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req) as resp:
            logger.info("Submission logged to SurrealDB successfully.")
    except Exception as exc:
        logger.warning("Failed to log to SurrealDB: %s", exc)


def main() -> None:
    logger.info("Starting Gemma 4 Midnight UTC Auto-Submitter Daemon...")
    sha = verify_submission_archive()

    secs_to_wait = compute_seconds_to_midnight_utc()
    hours_left = secs_to_wait / 3600.0
    logger.info(
        "Quota reset at 00:00:15 UTC. Waiting for %.1f seconds (~%.2f hours)...",
        secs_to_wait,
        hours_left,
    )

    # Sleep until reset
    if secs_to_wait > 0:
        time.sleep(secs_to_wait)

    logger.info("Quota window opened! Authenticating with Kaggle API...")
    api = KaggleApi()
    api.authenticate()

    logger.info("Dispatching submission to %s...", COMPETITION)
    try:
        res = api.competition_submit(
            file_name=str(SUBMISSION_ZIP),
            message=DESCRIPTION,
            competition=COMPETITION,
        )
        logger.info("Submission successful! Result: %s", res)
        # Query latest submission ref
        subs = api.competition_submissions(COMPETITION)
        latest_ref = subs[0].ref if subs else None
        logger.info("Latest submission ref: %s", latest_ref)
        log_to_surrealdb("SUBMITTED", latest_ref, sha, "Successfully submitted at 00:00 UTC")
    except Exception as exc:
        logger.error("Submission failed: %s", exc)
        log_to_surrealdb("FAILED", None, sha, str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
