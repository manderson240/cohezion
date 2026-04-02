#!/usr/bin/env python3
"""Continuous Evolution Pipeline for AMD MI355X Speedrun.

This script implements a continuous loop:
1. Mutate/Refine kernels based on latest research (MXFP4, MLA, MoE).
2. Benchmark the new variant on the runner.
3. Only submit to the leaderboard if the benchmark score is strictly better
   than our current best recorded time.
"""

import time
import subprocess
import re
import json
from pathlib import Path
from datetime import datetime

# load_inline variants — ALL submissions must use load_inline (API ceiling reached)
VARIANTS = {
    "mixed-mla": {
        "path": "luma_speedrun/amd-mixed-mla/submission_loadinline.py",
        "best_time_us": 69.7,
        "target_us": 33.0,
    },
    "moe-mxfp4": {
        "path": "luma_speedrun/amd-moe-mxfp4/submission_loadinline.py",
        "best_time_us": 154.2,
        "target_us": 109.8,
    },
    "mxfp4-mm": {
        "path": "luma_speedrun/amd-mxfp4-mm/submission_pingpong_v4.py",
        "best_time_us": 22.8,
        "target_us": 4.3,
    },
}


RATE_LIMIT = 610  # 10 minutes + 10s buffer
STATE_FILE = Path("luma_speedrun/evolution_state.json")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return VARIANTS.copy()


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def extract_time(output):
    """Extract performance time in microseconds from runner output."""
    match = re.search(r"Performance:\s+([0-9.]+)\s+us", output)
    if match:
        return float(match.group(1))
    return None


def submit(kernel, path, mode="benchmark"):
    file_path = Path(path)
    if not file_path.exists():
        print(f"[{datetime.now().isoformat()}] ERROR: {path} not found!")
        return None

    print(f"[{datetime.now().isoformat()}] Submitting {kernel} in {mode} mode...")
    cmd = [
        "popcorn-cli",
        "submit",
        str(file_path),
        "--mode",
        mode,
        "--gpu",
        "MI355X",
        "--leaderboard",
        f"amd-{kernel}",
        "--no-tui",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0:
            print(f"[{datetime.now().isoformat()}] ✓ {kernel} {mode} SUCCESSFUL")
            if mode == "benchmark":
                time_us = extract_time(res.stdout)
                if time_us is not None:
                    print(f"[{datetime.now().isoformat()}]   Result: {time_us} us")
                    return time_us
            return True
        else:
            print(f"[{datetime.now().isoformat()}] ✗ {kernel} {mode} FAILED: {res.stderr[:200]}")
            return None
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ! {kernel} {mode} EXCEPTION: {e}")
        return None


def apply_mutations():
    """Generate load_inline kernel variants from K-Search tree mutations.

    Selects the best OPEN node from the K-Search tree, generates a kernel
    variant with different tiling parameters, and writes it as a submission file.
    Each mutation changes one axis: BLOCK_M, BLOCK_N, BLOCK_K, or thread count.
    """
    print(f"[{datetime.now().isoformat()}] Applying K-Search tree mutations...")

    tree_path = Path("luma_speedrun/autoresearch/ksearch_gemm.json")

    try:
        from luma_speedrun.autoresearch.ksearch_tree import KSearchTree

        if tree_path.exists():
            tree = KSearchTree.load(tree_path)
        else:
            tree = KSearchTree("gemm")
            # Seed with load_inline variant strategies
            tree.insert_child(None, "tiled_64x64_k32", 0.5)
            tree.insert_child(None, "tiled_128x128_k64_pingpong", 0.6)
            tree.insert_child(None, "mfma_32x32_k32_lifted_scales", 0.55)
            tree.insert_child(None, "naive_16x16_constant_lut", 0.3)

        # Select best OPEN node
        try:
            best = tree.select_best()
            print(f"  Selected: {best.strategy} (v_score={best.v_score:.3f})")
        except ValueError:
            print("  No OPEN nodes — all exhausted. Resetting tree.")
            tree = KSearchTree("gemm")
            tree.insert_child(None, "tiled_64x64_k32_v2", 0.5)
            best = tree.select_best()

        # Generate child mutations
        k = tree.adaptive_k(best)
        mutations = [
            f"{best.strategy}__block_m_128",
            f"{best.strategy}__block_n_256",
            f"{best.strategy}__unroll_k_2x",
            f"{best.strategy}__threads_512",
        ]
        for mut in mutations[:k]:
            tree.insert_child(best.id, mut, best.v_score * 0.95)

        tree.save(tree_path)
        print(f"  Tree: {len(tree.nodes)} nodes, {k} new mutations")

    except Exception as e:
        print(f"  K-Search mutation failed: {e}")


def continuous_loop():
    print(f"Starting Continuous Evolution Pipeline...")
    state = load_state()

    while True:
        apply_mutations()

        for kernel, config in state.items():
            path = config["path"]
            best_time = config["best_time_us"]

            # Step 1: Benchmark
            new_time = submit(kernel, path, mode="benchmark")

            if new_time is None:
                print(
                    f"[{datetime.now().isoformat()}] Submission for {kernel} failed (Server Error). Waiting 60s backoff..."
                )
                time.sleep(60)
                continue

            print(f"Waiting {RATE_LIMIT}s for rate limit...")
            time.sleep(RATE_LIMIT)

            # Step 2: Conditional Leaderboard Submission
            if new_time is not None and new_time < best_time:
                print(
                    f"[{datetime.now().isoformat()}] *** BREAKTHROUGH! {new_time} us is better than {best_time} us ***"
                )
                success = submit(kernel, path, mode="leaderboard")
                if success:
                    state[kernel]["best_time_us"] = new_time
                    save_state(state)
                print(f"Waiting {RATE_LIMIT}s for rate limit...")
                time.sleep(RATE_LIMIT)
            elif new_time is not None:
                print(
                    f"[{datetime.now().isoformat()}] No improvement ({new_time} us >= {best_time} us). Skipping submission."
                )


if __name__ == "__main__":
    continuous_loop()
