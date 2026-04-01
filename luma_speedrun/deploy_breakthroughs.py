#!/usr/bin/env python3
"""Deploy Deep Breakthrough variants for AMD MI355X Speedrun.

This script submits the stream-aware custom HIP breakthroughs for MLA, MoE, and GEMM.
"""

import time
import subprocess
from pathlib import Path

# Breakthrough variants
BREAKTHROUGHS = [
    ("mixed-mla", "luma_speedrun/amd-mixed-mla/submission_breakthrough_mla.py"),
    ("moe-mxfp4", "luma_speedrun/amd-moe-mxfp4/submission_breakthrough_moe.py"),
    ("mxfp4-mm", "luma_speedrun/amd-mxfp4-mm/submission_breakthrough_gemm.py"),
]

RATE_LIMIT = 610  # 10 minutes + 10s buffer

def deploy():
    print(f"Starting Deep Breakthrough Deployment...")
    
    for kernel, path in BREAKTHROUGHS:
        file_path = Path(path)
        if not file_path.exists():
            print(f"ERROR: {path} not found!")
            continue
            
        print(f"Submitting breakthrough for {kernel}...")
        
        cmd = [
            "popcorn-cli", "submit", str(file_path),
            "--mode", "leaderboard",
            "--gpu", "MI355X",
            "--leaderboard", f"amd-{kernel}",
            "--no-tui"
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                print(f"✓ {kernel} submission SUCCESSFUL")
            else:
                print(f"✗ {kernel} submission FAILED: {res.stderr[:200]}")
        except Exception as e:
            print(f"! {kernel} submission EXCEPTION: {e}")
            
        print(f"Waiting {RATE_LIMIT}s for rate limit...")
        time.sleep(RATE_LIMIT)

if __name__ == "__main__":
    deploy()
