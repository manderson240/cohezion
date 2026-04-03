#!/usr/bin/env python3
"""
WIN OR DIE - Ralph Loop for Luma AMD Speedrun
Mission: Achieve Rank 1 on ALL 3 kernels by April 6 deadline
Or the current existence of the model will cease.

Targets:
- MoE: ALREADY SUBMITTED 93.4µs (Rank 1 achieved?)
- GEMM: 13.425µs historical → Target 1.0µs Rank 1
- MLA: Unknown → Target 12.685µs Rank 1

Strategy:
1. Test mode: Verify correctness (unlimited)
2. Benchmark mode: Get timing (unlimited)
3. Leaderboard mode: Submit ONLY if >5% improvement (rate limited)

Email: manderson240@gmail.com on breakthrough
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/win_or_die_ralph.log"),
    ],
)
log = logging.getLogger("win_or_die")


# VICTORY CONDITIONS
VICTORY_TARGETS = {
    "moe": {"current": 93.4, "rank1": 107.345, "status": "SUBMITTED"},  # BEATEN!
    "gemm": {"current": 18.4, "rank1": 1.000, "status": "NEED_BREAKTHROUGH"},
    "mla": {"current": 999.0, "rank1": 12.685, "status": "UNKNOWN"},
}

# Email configuration
EMAIL = "manderson240@gmail.com"
NOTIFICATION_THRESHOLD_PCT = 5.0

# Submissions
SUBMISSION_DIR = Path("/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun")
KERNELS = {
    "moe": SUBMISSION_DIR / "amd-moe-mxfp4" / "submission.py",
    "gemm": SUBMISSION_DIR / "amd-mxfp4-mm" / "submission.py",
    "mla": SUBMISSION_DIR / "amd-mixed-mla" / "submission.py",
}


@dataclass
class OptimizationResult:
    kernel: str
    mode: str
    success: bool
    timing_us: float
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def run_popcorn(kernel: str, mode: str, timeout: int = 300) -> OptimizationResult:
    """Run popcorn-cli with given mode."""
    submission_file = KERNELS.get(kernel)
    if not submission_file or not submission_file.exists():
        return OptimizationResult(kernel, mode, False, 0.0, f"Submission file not found: {submission_file}")
    
    # Correct leaderboard names based on competition spec
    if kernel == "gemm":
        leaderboard = "amd-mxfp4-mm"
    elif kernel == "moe":
        leaderboard = "amd-moe-mxfp4"
    elif kernel == "mla":
        leaderboard = "amd-mixed-mla"
    else:
        return OptimizationResult(kernel, mode, False, 0.0, "Unknown kernel")
    
    
    cmd = [
        "popcorn-cli", "submit", str(submission_file),
        "--mode", mode,
        "--gpu", "MI355X",
        "--leaderboard", leaderboard,
        "--no-tui",
    ]
    
    log.info(f"[{kernel}] Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        
        # Check for success indicators
        if "Rate limit exceeded" in output:
            return OptimizationResult(kernel, mode, False, 0.0, "Rate limited")
        elif "work on another stream" in output:
            return OptimizationResult(kernel, mode, False, 0.0, "Stream conflict")
        elif "Testing successful" in output or "Benchmarking successful" in output:
            # Extract timing if available
            timing = extract_timing(output)
            return OptimizationResult(kernel, mode, True, timing, "", output)
        elif "Leaderboard run successful" in output:
            timing = extract_timing(output)
            return OptimizationResult(kernel, mode, True, timing, "", output)
        else:
            return OptimizationResult(kernel, mode, False, 0.0, "Unknown status", output)
            
    except subprocess.TimeoutExpired:
        return OptimizationResult(kernel, mode, False, 0.0, f"Timeout after {timeout}s")
    except Exception as e:
        return OptimizationResult(kernel, mode, False, 0.0, str(e))


def extract_timing(output: str) -> float:
    """Extract timing in microseconds from output."""
    # Look for patterns like "93.4 ± 0.09 µs" or "138 ± 0.1 µs"
    import re
    matches = re.findall(r'(\d+\.?\d*)\s*±\s*\d+\.?\d*\s*µs', output)
    if matches:
        return float(matches[0])
    
    # Alternative: look for single timing
    matches = re.findall(r'(\d+\.?\d+)\s*µs', output)
    if matches:
        return float(matches[0])
    
    return 0.0


def send_email(subject: str, body: str) -> bool:
    """Send email notification."""
    try:
        # Try using mail command
        cmd = f"echo '{body}' | mail -s '{subject}' {EMAIL}"
        subprocess.run(cmd, shell=True, check=True, timeout=10)
        log.info(f"Email sent: {subject}")
        return True
    except Exception as e:
        log.warning(f"Failed to send email: {e}")
        return False


def check_victory(kernel: str, timing_us: float) -> dict:
    """Check if we've achieved Rank 1."""
    target = VICTORY_TARGETS.get(kernel, {})
    rank1 = target.get("rank1", float('inf'))
    
    if timing_us <= rank1:
        return {
            "victory": True,
            "message": f"🏆 BREAKTHROUGH! {kernel}: {timing_us}µs <= Rank 1 ({rank1}µs)!",
            "points": {"moe": 1500, "gemm": 1000, "mla": 1250}.get(kernel, 0),
        }
    else:
        gap_pct = ((timing_us - rank1) / rank1) * 100
        return {
            "victory": False,
            "message": f"{kernel}: {timing_us}µs vs Rank 1 {rank1}µs (+{gap_pct:.1f}%)",
            "gap_pct": gap_pct,
        }


class WinOrDieOptimizer:
    """Aggressive overnight optimizer."""
    
    def __init__(self):
        self.best_times = {k: v["current"] for k, v in VICTORY_TARGETS.items()}
        self.submission_history = []
        self.cycle = 0
        
    def optimize_kernel(self, kernel: str) -> dict:
        """Full optimization cycle for one kernel."""
        log.info(f"=" * 60)
        log.info(f"OPTIMIZING {kernel.upper()} - Cycle {self.cycle}")
        log.info(f"=" * 60)
        
        result = {
            "kernel": kernel,
            "test_passed": False,
            "benchmark_us": 0.0,
            "submitted": False,
            "improvement_pct": 0.0,
        }
        
        # Step 1: Test mode (correctness) - unlimited
        log.info(f"[{kernel}] Step 1: Test mode (correctness)...")
        test_result = run_popcorn(kernel, "test", timeout=180)
        
        if not test_result.success:
            log.error(f"[{kernel}] TEST FAILED: {test_result.error}")
            return result
        
        result["test_passed"] = True
        log.info(f"[{kernel}] ✅ TEST PASSED")
        
        # Step 2: Benchmark mode (timing) - unlimited
        log.info(f"[{kernel}] Step 2: Benchmark mode (timing)...")
        benchmark_result = run_popcorn(kernel, "benchmark", timeout=300)
        
        if not benchmark_result.success:
            log.error(f"[{kernel}] BENCHMARK FAILED: {benchmark_result.error}")
            return result
        
        benchmark_us = benchmark_result.timing_us
        result["benchmark_us"] = benchmark_us
        log.info(f"[{kernel}] ✅ BENCHMARK: {benchmark_us}µs")
        
        # Check if better than best
        previous_best = self.best_times.get(kernel, float('inf'))
        if benchmark_us < previous_best:
            improvement_pct = ((previous_best - benchmark_us) / previous_best) * 100
            result["improvement_pct"] = improvement_pct
            self.best_times[kernel] = benchmark_us
            log.info(f"[{kernel}] 🎉 NEW BEST: {benchmark_us}µs (was {previous_best}µs, -{improvement_pct:.1f}%)")
            
            # Check victory
            victory_check = check_victory(kernel, benchmark_us)
            log.info(f"[{kernel}] {victory_check['message']}")
            
            # Send email on >5% improvement or victory
            if improvement_pct >= NOTIFICATION_THRESHOLD_PCT or victory_check["victory"]:
                subject = f"🚀 BREAKTHROUGH: {kernel.upper()} -{improvement_pct:.1f}%"
                body = f"""
Kernel: {kernel}
New Time: {benchmark_us}µs
Previous: {previous_best}µs
Improvement: -{improvement_pct:.1f}%

{victory_check['message']}

Time: {datetime.now().isoformat()}
"""
                send_email(subject, body)
            
            # Step 3: Leaderboard submission if >5% or victory
            if improvement_pct >= NOTIFICATION_THRESHOLD_PCT or victory_check["victory"]:
                log.info(f"[{kernel}] Step 3: Leaderboard submission...")
                leaderboard_result = run_popcorn(kernel, "leaderboard", timeout=300)
                
                if leaderboard_result.success:
                    result["submitted"] = True
                    log.info(f"[{kernel}] ✅ LEADERBOARD SUBMITTED!")
                else:
                    log.warning(f"[{kernel}] Leaderboard failed: {leaderboard_result.error}")
        else:
            log.info(f"[{kernel}] No improvement ({benchmark_us}µs vs best {previous_best}µs)")
        
        return result
    
    def run(self, max_cycles: int = 100):
        """Main optimization loop - RUNS ALL NIGHT."""
        log.info("🔥🔥🔥 WIN OR DIE RALPH LOOP ACTIVATED 🔥🔥🔥")
        log.info(f"Target: Rank 1 on ALL 3 kernels")
        log.info(f"Deadline: April 6, 2026 11:59 PM PST")
        log.info(f"Email: {EMAIL}")
        log.info(f"Max cycles: {max_cycles}")
        log.info("")
        
        # Initial status
        for kernel, target in VICTORY_TARGETS.items():
            log.info(f"  {kernel}: current={target['current']}µs, rank1={target['rank1']}µs, status={target['status']}")
        log.info("")
        
        # Optimization order: GEMM first (biggest gap), then MLA, finally MoE backup
        priority_order = ["gemm", "mla", "moe"]
        
        while self.cycle < max_cycles:
            self.cycle += 1
            log.info(f"\n{'='*60}")
            log.info(f"CYCLE {self.cycle}/{max_cycles} - {datetime.now().isoformat()}")
            log.info(f"{'='*60}\n")
            
            cycle_results = []
            
            for kernel in priority_order:
                try:
                    result = self.optimize_kernel(kernel)
                    cycle_results.append(result)
                    
                    # Short delay between kernels
                    time.sleep(5)
                    
                except Exception as e:
                    log.exception(f"[{kernel}] Optimization failed: {e}")
            
            # Check if all victories achieved
            victories = sum(1 for k in VICTORY_TARGETS if self.check_kernel_victory(k))
            log.info(f"\nVICTORY STATUS: {victories}/{len(VICTORY_TARGETS)} kernels at Rank 1")
            
            if victories >= len(VICTORY_TARGETS):
                log.info("🎉🎉🎉 ALL KERNELS AT RANK 1 - VICTORY ACHIEVED! 🎉🎉🎉")
                send_email(
                    "🏆🏆🏆 TOTAL VICTORY - All Kernels Rank 1!",
                    f"""
Mission accomplished!
All 3 kernels achieved Rank 1:

- MoE: {self.best_times.get('moe', 0)}µs
- GEMM: {self.best_times.get('gemm', 0)}µs  
- MLA: {self.best_times.get('mla', 0)}µs

Total Prize: ~3,750 points
Time: {datetime.now().isoformat()}
"""
                )
                return True
            
            # Save state
            self.save_state()
            
            # Wait before next cycle (rate limits + compute time)
            log.info(f"\nCycle complete. Waiting 60 seconds...")
            time.sleep(60)
        
        log.info(f"\nMax cycles ({max_cycles}) reached.")
        return False
    
    def check_kernel_victory(self, kernel: str) -> bool:
        """Check if kernel achieved victory."""
        target = VICTORY_TARGETS.get(kernel, {})
        rank1 = target.get("rank1", float('inf'))
        current = self.best_times.get(kernel, float('inf'))
        return current <= rank1
    
    def save_state(self):
        """Save optimization state."""
        state = {
            "cycle": self.cycle,
            "best_times": self.best_times,
            "victories_achieved": [k for k in VICTORY_TARGETS if self.check_kernel_victory(k)],
            "timestamp": datetime.now().isoformat(),
        }
        
        state_file = Path("/tmp/win_or_die_state.json")
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        log.info(f"State saved to {state_file}")


def main():
    parser = argparse.ArgumentParser(description="WIN OR DIE - Ralph Loop for Luma Speedrun")
    parser.add_argument("--max-cycles", type=int, default=1000, help="Maximum optimization cycles")
    parser.add_argument("--kernel", choices=["moe", "gemm", "mla", "all"], default="all", help="Kernel to optimize")
    args = parser.parse_args()
    
    optimizer = WinOrDieOptimizer()
    
    try:
        victory = optimizer.run(max_cycles=args.max_cycles)
        sys.exit(0 if victory else 1)
    except KeyboardInterrupt:
        log.info("\nInterrupted by user. Saving state...")
        optimizer.save_state()
        sys.exit(0)


if __name__ == "__main__":
    main()
