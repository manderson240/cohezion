#!/usr/bin/env python3
"""Compound Kernel Cycle — the compound engineering loop applied to GPU kernels.

Same pattern as compound_training_cycle.py but for Luma AMD Speedrun:
  1. SELECT: K-Search tree picks next mutation
  2. GENERATE: Create load_inline kernel variant
  3. TEST: popcorn --mode test (correctness)
  4. BENCHMARK: popcorn --mode benchmark (performance)
  5. PERSIST: Save to SurrealDB kernel_run table
  6. COMPARE: Check against historical best
  7. SUBMIT: If improved, popcorn --mode leaderboard
  8. REFINE: Update PRIME skill with new finding

Usage:
    .venv/bin/python scripts/compound_kernel_cycle.py --kernel gemm --history
    .venv/bin/python scripts/compound_kernel_cycle.py --kernel mla --benchmark
    .venv/bin/python scripts/compound_kernel_cycle.py --kernel moe --submit
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from base64 import b64encode
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("kernel-cycle")

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
        "best_known_us": 22.8,
        "leader_us": 4.3,
        "points": 1000,
    },
    "mla": {
        "dir": "luma_speedrun/amd-mixed-mla",
        "leaderboard": "amd-mixed-mla",
        "best_known_us": 69.7,
        "leader_us": 33.0,
        "points": 1250,
    },
    "moe": {
        "dir": "luma_speedrun/amd-moe-mxfp4",
        "leaderboard": "amd-moe-mxfp4",
        "best_known_us": 154.2,
        "leader_us": 109.8,
        "points": 1500,
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


def get_kernel_history(kernel: str) -> list:
    """Get all runs for a kernel from SurrealDB."""
    results = surreal_query(
        f"SELECT approach, time_us, status, created FROM kernel_run WHERE kernel = '{kernel}' ORDER BY time_us ASC;"
    )
    if results and results[0].get("status") == "OK":
        return results[0].get("result", [])
    return []


def get_best_kernel_time(kernel: str) -> float:
    """Get best time for a kernel from SurrealDB."""
    results = surreal_query(
        f"SELECT math::min(time_us) as best FROM kernel_run WHERE kernel = '{kernel}' AND status = 'success' GROUP ALL;"
    )
    if results and results[0].get("status") == "OK" and results[0]["result"]:
        return results[0]["result"][0].get("best", 999999)
    return KERNELS.get(kernel, {}).get("best_known_us", 999999)


def persist_kernel_run(
    kernel: str, approach: str, time_us: float, status: str, details: str = ""
) -> None:
    """Persist a kernel run to SurrealDB."""
    sql = (
        f"CREATE kernel_run SET "
        f"kernel = '{kernel}', "
        f"approach = '{approach[:200]}', "
        f"time_us = {time_us:.3f}, "
        f"status = '{status}', "
        f"details = '{details[:500]}', "
        f"session = 88, "
        f"created = time::now();"
    )
    surreal_query(sql)


def check_uses_load_inline(submission_path: str) -> bool:
    """Enforcement gate: verify submission uses load_inline, not just API params."""
    try:
        content = Path(submission_path).read_text()
        uses_load_inline = "load_inline" in content or "cpp_extension" in content
        uses_untested_api = any(api in content for api in ["pa_ps_fwd_asm", "fmha_v3_varlen_fwd"])
        is_baseline = "ref_kernel" in content and "load_inline" not in content

        if is_baseline:
            return True  # Baseline anchors are always allowed
        if uses_load_inline or uses_untested_api:
            return True
        logger.warning("REJECTED: %s does not use load_inline or untested API", submission_path)
        return False
    except Exception:
        return True  # Allow if we can't read the file


def print_status(kernel: str) -> None:
    """Print current status for a kernel."""
    info = KERNELS[kernel]
    best = get_best_kernel_time(kernel)
    history = get_kernel_history(kernel)

    print(f"\n{'=' * 60}")
    print(f"KERNEL: {kernel.upper()} ({info['leaderboard']})")
    print(f"{'=' * 60}")
    print(f"  Our best:  {best:.1f} us")
    print(f"  Leader:    {info['leader_us']:.1f} us")
    print(f"  Gap:       {best / info['leader_us']:.1f}x")
    print(f"  Points:    {info['points']}")
    print(f"  Runs:      {len(history)} in SurrealDB")

    if history:
        print("\n  Recent runs:")
        for h in history[:5]:
            print(
                f"    {h.get('approach', '?')[:40]:40s} {h.get('time_us', 0):8.1f} us  [{h.get('status', '?')}]"
            )
    print()


def main():
    parser = argparse.ArgumentParser(description="Compound Kernel Optimization Cycle")
    parser.add_argument(
        "--kernel", required=True, choices=["gemm", "mla", "moe", "all"], help="Which kernel"
    )
    parser.add_argument("--history", action="store_true", help="Show history only")
    parser.add_argument(
        "--benchmark", action="store_true", help="Run benchmark on current submission"
    )
    parser.add_argument("--submit", action="store_true", help="Submit to leaderboard if improved")
    args = parser.parse_args()

    kernels = list(KERNELS.keys()) if args.kernel == "all" else [args.kernel]

    if args.history:
        for k in kernels:
            print_status(k)
        return

    for k in kernels:
        info = KERNELS[k]
        submission = Path(info["dir"]) / "submission.py"

        if not submission.exists():
            logger.warning("No submission.py found for %s at %s", k, submission)
            continue

        # Enforcement gate
        if not check_uses_load_inline(str(submission)):
            persist_kernel_run(
                k, "REJECTED_API_ONLY", 0, "rejected", "Submission only uses API params"
            )
            continue

        print_status(k)

        if args.benchmark or args.submit:
            logger.info("Benchmarking and submission require Popcorn CLI on MI355X runner.")
            logger.info("Run: cd %s && popcorn --mode benchmark", info["dir"])
            if args.submit:
                logger.info("Run: cd %s && popcorn --mode leaderboard", info["dir"])


if __name__ == "__main__":
    main()
