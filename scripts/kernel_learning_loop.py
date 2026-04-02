#!/usr/bin/env python3
"""Kernel Learning Loop — continuous benchmark-driven optimization.

Runs every 5 minutes:
  1. K-Search tree selects next mutation (kernel variant index)
  2. Generate load_inline kernel variant (select from available submissions)
  3. popcorn --mode test (correctness check, ~30s)
  4. If correct: popcorn --mode benchmark (performance, ~60s)
  5. Record result to SurrealDB kernel_run table
  6. Update K-Search tree node score
  7. If benchmark < current_best: FLAG for leaderboard submission

Every 60 minutes:
  8. Submit best-of-hour to leaderboard (--mode leaderboard)
  9. Compare leaderboard rank vs benchmark estimate

Budget: 12 benchmarks/hour x 3 kernels = 36 data points/hour
Over 5 days: 4,320 benchmark runs (vs ~50 total currently)

Usage:
    .venv/bin/python scripts/kernel_learning_loop.py --kernel gemm
    .venv/bin/python scripts/kernel_learning_loop.py --kernel all --interval 300
    .venv/bin/python scripts/kernel_learning_loop.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from base64 import b64encode
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("kernel-loop")

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "cohezion",
    "Authorization": "Basic " + b64encode(b"root:root").decode(),
}

KERNELS = {
    "gemm": {
        "dir": "luma_speedrun/amd-mxfp4-mm",
        "leaderboard": "amd-mxfp4-mm",
        "submissions": [
            "submission.py",
            "submission_loadinline.py",
            "submission_tritonblas.py",
        ],
    },
    "mla": {
        "dir": "luma_speedrun/amd-mixed-mla",
        "leaderboard": "amd-mixed-mla",
        "submissions": ["submission.py", "submission_loadinline.py"],
    },
    "moe": {
        "dir": "luma_speedrun/amd-moe-mxfp4",
        "leaderboard": "amd-moe-mxfp4",
        "submissions": ["submission.py", "submission_loadinline.py"],
    },
}


def surreal_query(sql: str) -> list:
    """Execute SurrealQL and return results."""
    try:
        req = urllib.request.Request(
            SURREAL_URL, data=sql.encode(), headers=SURREAL_HEADERS, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except Exception:
        return []


def persist_kernel_run(
    kernel: str,
    approach: str,
    time_us: float,
    status: str,
    submission_file: str = "",
    details: str = "",
) -> None:
    """Persist a kernel run to SurrealDB."""
    approach_safe = approach.replace("'", "")[:200]
    details_safe = details.replace("'", "")[:500]
    file_safe = submission_file.replace("'", "")[:100]
    sql = (
        f"CREATE kernel_run SET "
        f"kernel = '{kernel}', "
        f"approach = '{approach_safe}', "
        f"time_us = {time_us:.3f}, "
        f"status = '{status}', "
        f"submission_file = '{file_safe}', "
        f"details = '{details_safe}', "
        f"loop_iteration = true, "
        f"created = time::now();"
    )
    surreal_query(sql)


def get_best_time(kernel: str) -> float:
    """Get best successful time for a kernel from SurrealDB."""
    results = surreal_query(
        f"SELECT math::min(time_us) as best FROM kernel_run "
        f"WHERE kernel = '{kernel}' AND status = 'success' GROUP ALL;"
    )
    if results and results[0].get("status") == "OK" and results[0].get("result"):
        return results[0]["result"][0].get("best", 999999.0)
    return 999999.0


def run_popcorn(kernel_dir: str, mode: str, timeout_s: int = 120) -> dict:
    """Run popcorn CLI in a kernel directory. Returns dict with status and output."""
    try:
        result = subprocess.run(
            ["popcorn", "--mode", mode],
            cwd=kernel_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except FileNotFoundError:
        return {"returncode": -1, "stdout": "", "stderr": "popcorn not found", "success": False}
    except subprocess.TimeoutExpired:
        return {"returncode": -2, "stdout": "", "stderr": "timeout", "success": False}


def parse_benchmark_time(output: str) -> float:
    """Extract benchmark time in microseconds from popcorn output."""
    for line in output.split("\n"):
        lower = line.lower()
        if "time" in lower and ("us" in lower or "µs" in lower):
            # Try to find numeric value before "us" or "µs"
            for word in line.split():
                try:
                    val = float(word.replace("us", "").replace("µs", "").rstrip(","))
                    if 0.1 < val < 100000:  # Sanity check
                        return val
                except ValueError:
                    continue
        # Also check for "median" or "mean" patterns
        if "median" in lower or "mean" in lower:
            for word in line.split():
                try:
                    val = float(word)
                    if 0.1 < val < 100000:
                        return val
                except ValueError:
                    continue
    return -1.0


def select_submission(kernel: str, iteration: int) -> str:
    """Simple round-robin submission selector. K-Search tree integration pending."""
    info = KERNELS[kernel]
    submissions = info["submissions"]
    base_dir = Path(info["dir"])

    # Round-robin through available submissions
    idx = iteration % len(submissions)
    selected = submissions[idx]

    # Verify file exists
    if (base_dir / selected).exists():
        return selected

    # Fallback to first available
    for s in submissions:
        if (base_dir / s).exists():
            return s

    return "submission.py"


def run_one_cycle(
    kernel: str,
    iteration: int,
    dry_run: bool = False,
    submit_best: bool = False,
) -> dict:
    """Run one benchmark cycle for a kernel."""
    info = KERNELS[kernel]
    kernel_dir = info["dir"]

    # 1. Select submission variant
    submission = select_submission(kernel, iteration)
    logger.info("[%s] iter=%d submission=%s", kernel, iteration, submission)

    if dry_run:
        logger.info("[%s] DRY RUN — skipping popcorn", kernel)
        persist_kernel_run(kernel, f"dry_run_{submission}", 0, "dry_run", submission)
        return {"status": "dry_run", "submission": submission}

    # 2. Copy selected submission as submission.py if needed
    base_dir = Path(kernel_dir)
    if submission != "submission.py":
        import shutil

        src = base_dir / submission
        dst = base_dir / "submission.py"
        # Backup current
        if dst.exists():
            shutil.copy2(dst, base_dir / "submission_backup.py")
        shutil.copy2(src, dst)
        logger.info("[%s] Activated %s as submission.py", kernel, submission)

    # 3. Test correctness
    logger.info("[%s] Running correctness test...", kernel)
    test_result = run_popcorn(kernel_dir, "test", timeout_s=60)

    if not test_result["success"]:
        logger.warning("[%s] Correctness FAILED: %s", kernel, test_result["stderr"][:200])
        persist_kernel_run(
            kernel,
            f"test_fail_{submission}",
            0,
            "correctness_fail",
            submission,
            test_result["stderr"][:200],
        )
        return {"status": "correctness_fail", "submission": submission}

    # 4. Benchmark
    logger.info("[%s] Running benchmark...", kernel)
    bench_result = run_popcorn(kernel_dir, "benchmark", timeout_s=120)

    if not bench_result["success"]:
        logger.warning("[%s] Benchmark FAILED: %s", kernel, bench_result["stderr"][:200])
        persist_kernel_run(
            kernel,
            f"bench_fail_{submission}",
            0,
            "benchmark_fail",
            submission,
            bench_result["stderr"][:200],
        )
        return {"status": "benchmark_fail", "submission": submission}

    # 5. Parse time
    time_us = parse_benchmark_time(bench_result["stdout"])
    if time_us < 0:
        logger.warning("[%s] Could not parse benchmark time from output", kernel)
        persist_kernel_run(
            kernel,
            f"parse_fail_{submission}",
            0,
            "parse_fail",
            submission,
            bench_result["stdout"][:200],
        )
        return {"status": "parse_fail", "submission": submission}

    # 6. Persist to SurrealDB
    persist_kernel_run(kernel, submission, time_us, "success", submission, f"iter={iteration}")
    logger.info("[%s] Benchmark: %.1f us (submission=%s)", kernel, time_us, submission)

    # 7. Check if new best
    best = get_best_time(kernel)
    is_new_best = time_us < best

    if is_new_best:
        logger.info("[%s] NEW BEST: %.1f us (prev: %.1f us)", kernel, time_us, best)

    # 8. Submit if requested and improved
    if submit_best and is_new_best:
        logger.info("[%s] Submitting to leaderboard...", kernel)
        submit_result = run_popcorn(kernel_dir, "leaderboard", timeout_s=120)
        if submit_result["success"]:
            logger.info("[%s] Leaderboard submission successful!", kernel)
            persist_kernel_run(
                kernel, f"leaderboard_{submission}", time_us, "submitted", submission
            )
        else:
            logger.warning("[%s] Leaderboard submission failed", kernel)

    return {
        "status": "success",
        "time_us": time_us,
        "submission": submission,
        "is_new_best": is_new_best,
    }


def main():
    parser = argparse.ArgumentParser(description="Kernel Learning Loop")
    parser.add_argument(
        "--kernel",
        required=True,
        choices=["gemm", "mla", "moe", "all"],
        help="Which kernel to optimize",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between benchmark cycles (default: 300 = 5 min)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Max iterations (0 = infinite)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Record to SurrealDB without running popcorn",
    )
    parser.add_argument(
        "--submit-interval",
        type=int,
        default=12,
        help="Submit to leaderboard every N iterations (default: 12 = ~1 hour at 5min intervals)",
    )
    args = parser.parse_args()

    kernels = list(KERNELS.keys()) if args.kernel == "all" else [args.kernel]

    logger.info("Starting kernel learning loop")
    logger.info("  Kernels: %s", ", ".join(kernels))
    logger.info("  Interval: %ds", args.interval)
    logger.info("  Submit every %d iterations", args.submit_interval)
    logger.info("  Dry run: %s", args.dry_run)

    iteration = 0
    while True:
        iteration += 1
        if args.max_iterations and iteration > args.max_iterations:
            logger.info("Reached max iterations (%d). Stopping.", args.max_iterations)
            break

        submit_this_round = (iteration % args.submit_interval) == 0

        for kernel in kernels:
            try:
                result = run_one_cycle(
                    kernel,
                    iteration,
                    dry_run=args.dry_run,
                    submit_best=submit_this_round,
                )
                status = result.get("status", "unknown")
                time_us = result.get("time_us", 0)
                if status == "success":
                    emoji = "*" if result.get("is_new_best") else " "
                    logger.info(
                        "[%s] %s iter=%d  %.1f us  (%s)",
                        kernel,
                        emoji,
                        iteration,
                        time_us,
                        result["submission"],
                    )
                else:
                    logger.info("[%s]   iter=%d  status=%s", kernel, iteration, status)
            except Exception as e:
                logger.error("[%s] Exception in cycle: %s", kernel, e)
                persist_kernel_run(kernel, "exception", 0, "error", "", str(e)[:200])

        if args.interval > 0 and (not args.max_iterations or iteration < args.max_iterations):
            logger.info("Sleeping %ds until next cycle...", args.interval)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
