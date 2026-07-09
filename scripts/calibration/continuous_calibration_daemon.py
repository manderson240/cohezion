#!/usr/bin/env python3
"""Continuous Calibration Daemon (ID-3).

Runs an automated self-improving loop for 2 real hours, executing cache
and routing sweeps, running tests to verify safety, and logging metrics
to both SurrealDB and the Obsidian Vault.
"""

import asyncio
import logging
import os
import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path

# Ensure src/ is in the python path
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

# Allow local insecure SurrealDB credentials for development
os.environ["COHEZION_ALLOW_INSECURE_SURREAL"] = "1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(root_dir / "logs" / "continuous_calibration.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

RUNS_LOG_PATH = root_dir / "data" / "calibration" / "continuous_runs.jsonl"
RUNS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

VAULT_ROOT = Path("/home/mike-anderson/vaults/cohezion-vault")


async def run_subprocess(cmd: list[str]) -> tuple[int, str, str]:
    """Runs a shell command and returns returncode, stdout, stderr."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(root_dir),
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


def log_to_obsidian_vault(
    iteration: int, timestamp: str, cache_threshold: float, routing_params: dict, status: str
) -> None:
    """Logs the calibration run to the Obsidian Vault."""
    try:
        vault_file = VAULT_ROOT / "experiments" / "2026-06-02-continuous-parameter-calibration.md"
        vault_file.parent.mkdir(parents=True, exist_ok=True)

        if not vault_file.exists():
            initial_content = """---
title: Continuous Parameter Calibration and Self-Tuning
project: cohezion
date: 2026-06-02
tags: [calibration, semantic-cache, task-classifier, self-improving, routing]
status: in_progress
---

# Continuous Parameter Calibration and Self-Tuning

## Hypothesis
Continuous, automated parameter sweeps of the Semantic Cache threshold and Task Classifier routing length gates will adaptively optimize token efficiency and routing precision as session logs accumulate, without breaking system invariants.

## Experiment Design
- **Semantic Cache Sweep:** Sweeps cosine similarity thresholds `[0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]`, targeting <5% false positive semantic collisions.
- **Routing Sweep:** Evaluates length override thresholds on status questions, what-is definitional queries, and fallback parameters, minimizing false negatives and false positives.
- **Safety Checks:** Runs `pytest` unit test suite to guarantee 100% regression safety before applying config.

## Calibration Runs So Far

| Cycle | Timestamp (UTC) | Cache Thres | Status Len | WhatIs Len | HowDoes Len | Short Len | Med Len | Status |
|---|---|---|---|---|---|---|---|---|
"""
            vault_file.write_text(initial_content)

        row = (
            f"| #{iteration} | {timestamp} | {cache_threshold:.2f} | "
            f"{routing_params.get('status_question_max_len')} | {routing_params.get('short_what_is_max_len')} | "
            f"{routing_params.get('how_does_max_len')} | {routing_params.get('fallback_short_max_len')} | "
            f"{routing_params.get('fallback_medium_max_len')} | {status} |\n"
        )

        with open(vault_file, "a") as f:
            f.write(row)
        logger.info(f"Successfully logged Cycle #{iteration} to Obsidian Vault.")
    except Exception as e:
        logger.error(f"Failed to write to Obsidian Vault: {e}")


async def log_to_surrealdb(
    iteration: int, timestamp: str, cache_threshold: float, routing_params: dict, status: str
) -> None:
    """Logs the calibration run to SurrealDB."""
    try:
        from cohezion.core.persistence.surreal_client import SurrealClient

        db = SurrealClient()
        connected = await db.connect()
        if connected:
            record = {
                "id": f"calibration_runs:{iteration}",
                "iteration": iteration,
                "timestamp": timestamp,
                "cache_threshold": cache_threshold,
                "routing_params": routing_params,
                "status": status,
            }
            await db.create("calibration_runs", record)
            logger.info("Successfully persisted calibration run to SurrealDB.")
            await db.close()
        else:
            logger.warning("Could not connect to SurrealDB. Skipping database persistence.")
    except Exception as e:
        logger.error(f"Failed to write to SurrealDB: {e}")


async def execute_calibration_cycle(iteration: int) -> None:
    """Executes one cycle of calibration, verification, and testing."""
    logger.info(f"=== Starting Calibration Cycle #{iteration} ===")

    # 1. Run Semantic Cache Sweep
    logger.info("Executing Semantic Cache Parameter Sweep...")
    code_cache, out_cache, err_cache = await run_subprocess(
        [
            ".venv/bin/python",
            "scripts/calibration/run_cache_calibration.py",
        ]
    )
    if code_cache != 0:
        logger.error(f"Cache calibration sweep failed (code {code_cache}): {err_cache}")
        return
    logger.info("Cache sweep complete.")

    # 2. Run Routing Sweep
    logger.info("Executing Task Classifier Routing Sweep...")
    code_route, out_route, err_route = await run_subprocess(
        [
            ".venv/bin/python",
            "scripts/calibration/run_routing_calibration.py",
        ]
    )
    if code_route != 0:
        logger.error(f"Routing calibration sweep failed (code {code_route}): {err_route}")
        return
    logger.info("Routing sweep complete.")

    # 3. Run Verify Calibration
    logger.info("Verifying calibrated parameters load correctly...")
    code_verify, out_verify, err_verify = await run_subprocess(
        [
            ".venv/bin/python",
            "scripts/calibration/verify_calibration.py",
        ]
    )
    if code_verify != 0:
        logger.error(f"Verification script failed (code {code_verify}): {err_verify}")
        return
    logger.info("Verification check passed.")

    # 4. Run Pytest Fast Tests
    logger.info("Running fast unit test suite to guarantee safety...")
    code_test, out_test, err_test = await run_subprocess(
        [
            "make",
            "test-fast",
        ]
    )
    if code_test != 0:
        logger.error(f"Test suite check failed (code {code_test}): {err_test}")
        return
    logger.info("All unit tests passed successfully.")

    # 5. Extract results for logging
    config_path = root_dir / "config" / "calibration_profiles.json"
    with open(config_path) as f:
        profiles = json.load(f)

    cache_threshold = (
        profiles.get("semantic_cache", {}).get("parameters", {}).get("similarity_threshold")
    )
    routing_params = profiles.get("task_classifier", {}).get("parameters", {})
    timestamp = datetime.now(timezone.utc).isoformat()

    log_entry = {
        "timestamp": timestamp,
        "iteration": iteration,
        "cache_threshold": cache_threshold,
        "routing_params": routing_params,
        "status": "HEALTHY",
    }

    # Filesystem JSONL logging
    with open(RUNS_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Obsidian Vault logging
    log_to_obsidian_vault(iteration, timestamp, cache_threshold, routing_params, "HEALTHY")

    # SurrealDB logging
    await log_to_surrealdb(iteration, timestamp, cache_threshold, routing_params, "HEALTHY")

    logger.info(f"Cycle #{iteration} succeeded.")


async def main():
    logger.info("Initializing Continuous Calibration Loop (2 Hour Budget)")

    # 2 Hours = 7200 seconds. Run 8 iterations, one every 15 minutes (900 seconds)
    total_duration = 7200
    interval = 900
    start_time = time.time()
    iteration = 1

    # Ensure logs folder exists
    (root_dir / "logs").mkdir(exist_ok=True)

    while (time.time() - start_time) < total_duration:
        cycle_start = time.time()
        try:
            await execute_calibration_cycle(iteration)
        except Exception as e:
            logger.exception(f"Unexpected exception during cycle #{iteration}: {e}")

        elapsed = time.time() - cycle_start
        sleep_time = max(0.0, interval - elapsed)

        remaining = total_duration - (time.time() - start_time)
        if remaining <= 0:
            break

        logger.info(
            f"Cycle #{iteration} complete. Sleeping for {sleep_time:.1f}s. "
            f"Remaining budget: {remaining:.1f}s"
        )
        iteration += 1
        await asyncio.sleep(sleep_time)

    logger.info("Continuous Calibration Loop complete. 2 Hour budget spent.")


if __name__ == "__main__":
    asyncio.run(main())
