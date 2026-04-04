#!/usr/bin/env python3
"""Intelligent optimizer - Only submit improvements."""

import subprocess
import json
from pathlib import Path
from datetime import datetime

LOG = Path("/tmp/intelligent_optimizer.log")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

# Baselines from our knowledge
BASELINES = {
    "mla": 69.7,
    "moe": 93.4,
    "gemm": 13.0
}

def test_kernel(kernel, variant):
    """Test variant, return timing if available."""
    log(f"Testing {kernel}/{variant}...")
    
    worktree = "/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
    dirs = {"mla": "amd-mixed-mla", "moe": "amd-moe-mxfp4", "gemm": "amd-mxfp4-mm"}
    lbs = {"mla": "amd-mixed-mla", "moe": "amd-moe-mxfp4", "gemm": "amd-mxfp4-mm"}
    
    cmd = [
        "timeout", "300",
        "popcorn-cli", "submit", variant,
        "--mode", "benchmark",
        "--gpu", "MI355X",
        "--leaderboard", lbs[kernel],
        "--no-tui"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=f"{worktree}/luma_speedrun/{dirs[kernel]}")
        output = result.stdout + result.stderr
        
        # Look for timing in output
        import re
        match = re.search(r'(\d+\.?\d*)\s*us', output.lower())
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        log(f"  Error: {e}")
        return None

def submit_leaderboard(kernel, variant):
    """Submit to official leaderboard."""
    log(f"🚀 SUBMITTING {kernel}/{variant}!")
    
    worktree = "/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
    dirs = {"mla": "amd-mixed-mla", "moe": "amd-moe-mxfp4", "gemm": "amd-mxfp4-mm"}
    lbs = {"mla": "amd-mixed-mla", "moe": "amd-moe-mxfp4", "gemm": "amd-mxfp4-mm"}
    
    cmd = [
        "timeout", "600",
        "popcorn-cli", "submit", variant,
        "--mode", "leaderboard",
        "--gpu", "MI355X",
        "--leaderboard", lbs[kernel],
        "--no-tui"
    ]
    
    try:
        subprocess.run(cmd, timeout=600, cwd=f"{worktree}/luma_speedrun/{dirs[kernel]}")
        log(f"  Submitted!")
        return True
    except:
        return False

def main():
    log("="*50)
    log("INTELLIGENT OPTIMIZER - Improvement-Based Only")
    log("="*50)
    
    while True:
        log("\n--- New Optimization Round ---")
        
        # Check each kernel
        for kernel in ["moe", "mla", "gemm"]:
            baseline = BASELINES[kernel]
            log(f"\n{kernel.upper()}: Baseline {baseline}µs")
            
            # Test current best
            timing = test_kernel(kernel, "submission.py")
            
            if timing and timing < baseline * 0.95:  # 5% improvement
                log(f"  ✅ IMPROVEMENT: {baseline} → {timing}µs")
                if submit_leaderboard(kernel, "submission.py"):
                    BASELINES[kernel] = timing
            else:
                if timing:
                    log(f"  No improvement: {timing}µs vs {baseline}µs")
                else:
                    log(f"  Could not extract timing")
        
        log("\nSleeping 30 minutes...")
        import time
        time.sleep(1800)

if __name__ == "__main__":
    main()
