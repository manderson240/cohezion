#!/usr/bin/env python3
"""
BREAKTHROUGH ORCHESTRATOR - Can't Stop Won't Stop
Aggressive multi-kernel submission with auto-retry and improvement tracking
"""

import subprocess
import json
import time
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun")
RESULTS_FILE = Path("/home/mike-anderson/dev/cohezion/luma_speedrun/breakthrough_results.jsonl")
EMAIL = "manderson240@gmail.com"

# Current verified baselines
CURRENT_BEST = {
    "gemm": 22.0,
    "moe": 93.7,  # From today's benchmark (32-expert, bs=16)
    "mla": 69.7
}

KERNEL_CONFIG = {
    "gemm": {
        "path": BASE_DIR / "amd-mxfp4-mm/submission.py",
        "leaderboard": "amd-mxfp4-mm",
        "target": 4.327
    },
    "moe": {
        "path": BASE_DIR / "amd-moe-mxfp4/submission.py",
        "leaderboard": "amd-moe-mxfp4",
        "target": 107.793
    },
    "mla": {
        "path": BASE_DIR / "amd-mixed-mla/submission.py",
        "leaderboard": "amd-mixed-mla",
        "target": 32.972
    }
}

def log_result(kernel, mode, timing=None, status="unknown"):
    """Log submission result."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "kernel": kernel,
        "mode": mode,
        "timing_us": timing,
        "status": status,
        "current_best": CURRENT_BEST.get(kernel)
    }
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  📝 Logged: {kernel} = {timing}µs ({status})")

def submit_kernel(kernel, submit_mode="benchmark"):
    """Submit kernel and return timing."""
    config = KERNEL_CONFIG[kernel]
    cmd = [
        "popcorn-cli", "submit", str(config["path"]),
        "--mode", submit_mode,
        "--gpu", "MI355X",
        "--leaderboard", config["leaderboard"],
        "--no-tui"
    ]
    
    print(f"\n[{(datetime.now().strftime('%H:%M:%S'))}] Submitting {kernel.upper()} ({submit_mode})...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        
        # Extract timing
        import re
        timing = None
        for pattern in [r'⏱\s+([\d.]+)', r'([\d.]+)\s*µs', r'geomean[:\s]+([\d.]+)']:
            match = re.search(pattern, output)
            if match:
                timing = float(match.group(1))
                break
        
        if result.returncode == 0:
            log_result(kernel, submit_mode, timing, "success")
            return True, timing
        else:
            log_result(kernel, submit_mode, None, f"failed: {result.returncode}")
            return False, None
            
    except subprocess.TimeoutExpired:
        log_result(kernel, submit_mode, None, "timeout")
        return False, None
    except Exception as e:
        log_result(kernel, submit_mode, None, f"error: {e}")
        return False, None

def check_improvement(kernel, timing):
    """Check if timing is better than current best."""
    current = CURRENT_BEST.get(kernel, float('inf'))
    if timing and timing < current:
        improvement = ((current - timing) / current * 100) if current != float('inf') else 0
        print(f"  🎉 IMPROVEMENT: {timing:.2f}µs vs {current:.2f}µs ({improvement:.1f}%)")
        CURRENT_BEST[kernel] = timing
        
        # Send email notification
        try:
            subprocess.run(
                ["mail", "-s", f"🚀 BREAKTHROUGH: {kernel.upper()}", EMAIL],
                input=f"{kernel} improved to {timing:.2f}µs (was {current:.2f}µs)",
                timeout=10
            )
        except:
            pass
        
        return True
    return False

def run_optimization_cycle():
    """Run one optimization cycle for all kernels."""
    print("="*60)
    print(f"🚀 OPTIMIZATION CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    for kernel in ["gemm", "moe", "mla"]:
        print(f"\n🔧 {kernel.upper()}")
        
        # Test
        success, _ = submit_kernel(kernel, "test")
        if not success:
            print(f"  ❌ Test failed, skipping benchmark")
            continue
        
        # Benchmark
        success, timing = submit_kernel(kernel, "benchmark")
        if not timing:
            print(f"  ⚠ No timing extracted")
            continue
        
        print(f"  📊 Timing: {timing:.2f}µs")
        
        # Check improvement
        if check_improvement(kernel, timing):
            print(f"  🚀 IMPROVEMENT! Submitting to leaderboard...")
            submit_kernel(kernel, "leaderboard")
        else:
            print(f"  📊 No improvement over {CURRENT_BEST.get(kernel, 0):.2f}µs")

def main():
    """Main execution loop."""
    print("🚀 BREAKTHROUGH ORCHESTRATOR")
    print("   Mode: CAN'T STOP WON'T STOP")
    print("   Email: {}".format(EMAIL))
    print("   Log: {}".format(RESULTS_FILE))
    print("")
    
    cycle = 0
    while True:
        cycle += 1
        run_optimization_cycle()
        
        print(f"\n⏱ Cycle {cycle} complete. Sleeping 600 seconds...")
        print(f"   Next cycle: {(datetime.now().timestamp() + 600)}")
        time.sleep(600)

if __name__ == "__main__":
    main()
