#!/usr/bin/env python3
"""
intelligent_optimizer.py - Only submit if improvement expected

Rules:
1. Track baseline performance
2. Generate/test variants locally first
3. Only submit to leaderboard if variant < baseline * 0.95
4. Log all results for learning
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

# Configuration
WORKTREE = Path("/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint")
LOG_DIR = Path("/tmp/intelligent_optimizer")
LOG_DIR.mkdir(exist_ok=True)

# Baseline tracking file
BASELINE_FILE = LOG_DIR / "baselines.json"
RESULTS_FILE = LOG_DIR / "results.jsonl"

# Kernel configurations
KERNELS = {
    "mla": {
        "dir": "amd-mixed-mla",
        "leaderboard": "amd-mixed-mla",
        "baseline_us": 69.7,  # From code comments
        "rank1_us": 26.0,
        "variants": ["submission.py", "submission_safe.py", "submission_final.py"],
    },
    "moe": {
        "dir": "amd-moe-mxfp4",
        "leaderboard": "amd-moe-mxfp4",
        "baseline_us": 93.4,  # Our best so far
        "rank1_us": 70.47,
        "variants": [
            "submission.py",
            "submission_v2.py",
            "submission_safe.py",
            "submission_final.py",
        ],
    },
    "gemm": {
        "dir": "amd-mxfp4-mm",
        "leaderboard": "amd-mxfp4-mm",
        "baseline_us": 13.0,  # Estimated
        "rank1_us": 4.327,
        "variants": [
            "submission.py",
            "submission_8wave_pingpong.py",
            "submission_safe.py",
            "submission_final.py",
        ],
    },
}


def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(LOG_DIR / "optimizer.log", "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def run_command(cmd: list, timeout: int = 300) -> Tuple[str, int]:
    """Run command and return output + exit code."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]", -1
    except Exception as e:
        return f"[ERROR: {e}]", -1


def check_baseline(kernel: str) -> float:
    """Get current baseline for kernel."""
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE) as f:
            baselines = json.load(f)
            return baselines.get(kernel, KERNELS[kernel]["baseline_us"])
    return KERNELS[kernel]["baseline_us"]


def update_baseline(kernel: str, new_time: float):
    """Update baseline if improved."""
    baselines = {}
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE) as f:
            baselines = json.load(f)

    old = baselines.get(kernel, float("inf"))
    if new_time < old:
        baselines[kernel] = new_time
        with open(BASELINE_FILE, "w") as f:
            json.dump(baselines, f, indent=2)
        log(f"✅ New baseline for {kernel}: {new_time:.2f}µs (was {old:.2f}µs)")
        return True
    return False


def test_variant(kernel: str, variant: str, mode: str = "benchmark") -> Optional[float]:
    """Test variant and return timing if available."""
    config = KERNELS[kernel]
    kernel_dir = WORKTREE / "luma_speedrun" / config["dir"]

    log(f"Testing {kernel}/{variant} in {mode} mode...")

    cmd = [
        "popcorn-cli",
        "submit",
        variant,
        "--mode",
        mode,
        "--gpu",
        "MI355X",
        "--leaderboard",
        config["leaderboard"],
        "--no-tui",
    ]

    output, code = run_command(cmd, timeout=300)

    # Log result
    with open(RESULTS_FILE, "a") as f:
        result = {
            "timestamp": datetime.now().isoformat(),
            "kernel": kernel,
            "variant": variant,
            "mode": mode,
            "exit_code": code,
            "output": output[-1000:],  # Last 1000 chars
        }
        f.write(json.dumps(result) + "\n")

    # Try to extract timing from output
    # Look for patterns like "X.XXµs" or similar
    timing = None
    for line in output.split("\n"):
        if "µs" in line or "us" in line.lower():
            # Extract number
            import re

            match = re.search(r"(\d+\.?\d*)\s*[µu]s", line)
            if match:
                timing = float(match.group(1))
                break

    if timing:
        log(f"  Timing: {timing:.2f}µs")
    else:
        log(f"  No timing extracted (exit: {code})")

    return timing


def submit_to_leaderboard(kernel: str, variant: str) -> bool:
    """Submit variant to official leaderboard."""
    config = KERNELS[kernel]
    kernel_dir = WORKTREE / "luma_speedrun" / config["dir"]

    log(f"🚀 SUBMITTING {kernel}/{variant} TO LEADERBOARD")

    cmd = [
        "popcorn-cli",
        "submit",
        variant,
        "--mode",
        "leaderboard",
        "--gpu",
        "MI355X",
        "--leaderboard",
        config["leaderboard"],
        "--no-tui",
        "--output",
        str(LOG_DIR / f"{kernel}_{variant}_result.json"),
    ]

    output, code = run_command(cmd, timeout=600)

    # Check for submission ID
    import re

    match = re.search(r"Submission #(\d+)", output)
    if match:
        sub_id = match.group(1)
        log(f"  Submission ID: {sub_id}")

        # Wait for processing
        log(f"  Waiting for leaderboard run to complete...")
        import time

        time.sleep(180)  # 3 minutes

        # Check result
        check_cmd = ["popcorn-cli", "submissions", "show", sub_id]
        check_output, _ = run_command(check_cmd, timeout=30)

        if "leaderboard on" in check_output:
            log(f"  ✅ Leaderboard run confirmed!")
            return True

    log(f"  ⚠️ Submission may still be processing")
    return False


def optimize_kernel(kernel: str):
    """Optimize single kernel intelligently."""
    config = KERNELS[kernel]
    baseline = check_baseline(kernel)

    log(f"\n{'=' * 50}")
    log(f"Optimizing {kernel.upper()}")
    log(f"Baseline: {baseline:.2f}µs")
    log(f"Rank 1: {config['rank1_us']:.2f}µs")
    log(f"Gap: {baseline / config['rank1_us']:.2f}x")
    log(f"{'=' * 50}\n")

    # Strategy: Test each variant, submit best to leaderboard
    best_variant = None
    best_time = float("inf")

    for variant in config["variants"]:
        variant_path = WORKTREE / "luma_speedrun" / config["dir"] / variant
        if not variant_path.exists():
            log(f"Skipping {variant} (not found)")
            continue

        # Test in benchmark mode first
        timing = test_variant(kernel, variant, mode="benchmark")

        if timing and timing < best_time:
            best_time = timing
            best_variant = variant
            log(f"  New best variant: {variant} ({timing:.2f}µs)")

    # Decision: Submit to leaderboard?
    if best_variant and best_time < baseline * 0.95:  # 5% improvement threshold
        log(f"\n✅ Improvement detected: {baseline:.2f} → {best_time:.2f}µs")
        log(f"Submitting {best_variant} to leaderboard...")

        if submit_to_leaderboard(kernel, best_variant):
            update_baseline(kernel, best_time)
            return True
    else:
        if best_variant:
            log(f"\n❌ No improvement: best={best_time:.2f}µs, baseline={baseline:.2f}µs")
        else:
            log(f"\n❌ No working variant found")

    return False


def main():
    """Main optimization loop."""
    log("=" * 50)
    log("INTELLIGENT OPTIMIZER STARTED")
    log("Principle: Only submit improvements")
    log("=" * 50)

    # Round-robin through kernels
    iteration = 0
    while True:
        iteration += 1
        log(f"\n{'=' * 50}")
        log(f"ITERATION {iteration}")
        log(f"{'=' * 50}")

        improved = False
        for kernel in ["moe", "mla", "gemm"]:  # MoE first (closest to goal)
            if optimize_kernel(kernel):
                improved = True

        if not improved:
            log("\n⚠️ No improvements this round")
            log("Generating new variants or waiting...")
            # Could call variant generator here

        # Wait before next iteration
        log("\nSleeping 30 minutes...")
        import time

        time.sleep(1800)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nShutdown requested")
        sys.exit(0)
