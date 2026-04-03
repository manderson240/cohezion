#!/usr/bin/env python3
"""Auto-submit kernels hourly with email notifications on improvements.

Usage:
    python auto_submit_with_notifications.py --kernel gemm
    python auto_submit_with_notifications.py --kernel all --interval 3600
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration
EMAIL = "manderson240@gmail.com"
BASE_DIR = Path("/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun")
RESULTS_FILE = Path("/home/mike-anderson/dev/cohezion/luma_speedrun/submission_results.json")

# Current best times (will be updated from file)
BEST_TIMES = {
    "gemm": {"current": 22.8, "best_submitted": float('inf'), "timestamp": None},
    "mla": {"current": 69.7, "best_submitted": float('inf'), "timestamp": None},
    "moe": {"current": 154.2, "best_submitted": float('inf'), "timestamp": None},
}

# Kernel configurations
KERNELS = {
    "gemm": {
        "path": BASE_DIR / "amd-mxfp4-mm/submission.py",
        "leaderboard": "amd-mxfp4-mm",
        "target": 1.0,
    },
    "mla": {
        "path": BASE_DIR / "amd-mixed-mla/submission.py",
        "leaderboard": "amd-mixed-mla",
        "target": 12.685,
    },
    "moe": {
        "path": BASE_DIR / "amd-moe-mxfp4/submission.py",
        "leaderboard": "amd-moe-mxfp4",
        "target": 107.345,
    },
}


def send_email(subject: str, body: str) -> bool:
    """Send email notification via sendmail or mail command."""
    try:
        # Try sendmail first
        proc = subprocess.Popen(
            ["/usr/sbin/sendmail", "-t"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        email_content = f"""To: {EMAIL}
Subject: {subject}
Content-Type: text/plain; charset=utf-8

{body}
"""
        proc.communicate(email_content.encode('utf-8'))
        
        if proc.returncode == 0:
            print(f"  📧 Email sent to {EMAIL}")
            return True
    except Exception:
        pass
    
    # Fallback to mail command
    try:
        result = subprocess.run(
            ["mail", "-s", subject, EMAIL],
            input=body,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  📧 Email sent via mail command")
            return True
    except Exception:
        pass
    
    print(f"  ⚠ Email notification failed (no sendmail/mail available)")
    return False


def submit_kernel(kernel: str, mode: str = "test") -> tuple[bool, float | None]:
    """Submit kernel to Popcorn and return timing."""
    config = KERNELS[kernel]
    submission_path = config["path"]
    leaderboard = config["leaderboard"]
    
    print(f"  Submitting {kernel} in {mode} mode...")
    
    try:
        result = subprocess.run(
            [
                "popcorn-cli", "submit", str(submission_path),
                "--mode", mode,
                "--gpu", "MI355X",
                "--leaderboard", leaderboard,
                "--no-tui"
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout
        )
        
        output = result.stdout + result.stderr
        
        if "error" in output.lower() or result.returncode != 0:
            print(f"  ❌ Submission failed: {output[:200]}")
            return False, None
        
        # Extract timing from output
        import re
        timing = None
        
        # Look for timing patterns
        patterns = [
            r'(\d+\.\d+)\s*µs',
            r'(\d+\.\d+)\s*us',
            r'timing[:\s]+(\d+\.\d+)',
            r'geomean[:\s]+(\d+\.\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                timing = float(match.group(1))
                break
        
        if timing:
            print(f"  ✅ {kernel}: {timing:.3f}µs")
            return True, timing
        else:
            print(f"  ⚠ Submission succeeded but couldn't extract timing")
            return True, None
            
    except subprocess.TimeoutExpired:
        print(f"  ⏱ Submission timed out")
        return False, None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False, None


def check_improvement(kernel: str, timing: float) -> bool:
    """Check if timing is better than current best."""
    current_best = BEST_TIMES[kernel]["best_submitted"]
    
    if timing < current_best:
        improvement = ((current_best - timing) / current_best * 100) if current_best != float('inf') else 0
        BEST_TIMES[kernel]["best_submitted"] = timing
        BEST_TIMES[kernel]["timestamp"] = datetime.now().isoformat()
        
        # Send breakthrough notification
        if improvement > 5:  # Only notify for >5% improvements
            subject = f"🚀 BREAKTHROUGH: {kernel.upper()} improved to {timing:.2f}µs!"
            body = f"""Luma Speedrun Breakthrough Notification

Kernel: {kernel.upper()}
New Best: {timing:.3f}µs
Previous: {current_best:.3f}µs
Improvement: {improvement:.1f}%
Target: {KERNELS[kernel]['target']:.3f}µs
Gap: {(timing / KERNELS[kernel]['target']):.1f}x

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Submission: {KERNELS[kernel]['path']}

Keep pushing for Rank 1!
"""
            send_email(subject, body)
        
        return True
    
    return False


def run_continuous_submissions(kernel: str, interval: int = 3600):
    """Run continuous submissions for a kernel."""
    print(f"\n🚀 Starting continuous submission for {kernel.upper()}")
    print(f"   Check interval: {interval} seconds ({interval/60:.0f} minutes)")
    print(f"   Notifications: {EMAIL}")
    print(f"   Press Ctrl+C to stop\n")
    
    cycle = 0
    
    while True:
        cycle += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"[{timestamp}] Cycle {cycle} - {kernel.upper()}")
        
        # Step 1: Test mode
        print("  Step 1: Test mode...")
        test_success, _ = submit_kernel(kernel, "test")
        
        if not test_success:
            print(f"  ⚠ Test failed, skipping benchmark")
            time.sleep(interval)
            continue
        
        # Step 2: Benchmark mode
        print("  Step 2: Benchmark mode...")
        bench_success, timing = submit_kernel(kernel, "benchmark")
        
        if not bench_success:
            print(f"  ⚠ Benchmark failed")
            time.sleep(interval)
            continue
        
        if timing is None:
            print(f"  ⚠ Couldn't extract timing")
            time.sleep(interval)
            continue
        
        # Step 3: Check if improved
        if check_improvement(kernel, timing):
            print(f"  🎉 IMPROVEMENT! Submitting to leaderboard...")
            
            # Step 4: Submit to leaderboard
            lb_success, _ = submit_kernel(kernel, "leaderboard")
            
            if lb_success:
                print(f"  ✅ Leaderboard submission complete!")
            else:
                print(f"  ⚠ Leaderboard submission failed")
        else:
            current_best = BEST_TIMES[kernel]["best_submitted"]
            gap = ((timing - current_best) / current_best * 100) if current_best != float('inf') else 0
            print(f"  📊 No improvement. Current: {current_best:.2f}µs, This run: {timing:.2f}µs ({gap:+.1f}%)")
        
        # Save state
        with open(RESULTS_FILE, 'w') as f:
            json.dump(BEST_TIMES, f, indent=2)
        
        print(f"  ⏱ Next check in {interval/60:.0f} minutes\n")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Auto-submit kernels with email notifications")
    parser.add_argument("--kernel", required=True, choices=["gemm", "mla", "moe", "all"],
                        help="Kernel to monitor")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Submission interval in seconds (default: 3600 = 1 hour)")
    parser.add_argument("--once", action="store_true",
                        help="Submit once and exit (no continuous monitoring)")
    
    args = parser.parse_args()
    
    # Load previous results if exists
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE) as f:
                saved = json.load(f)
                BEST_TIMES.update(saved)
        except Exception:
            pass
    
    kernels = ["gemm", "mla", "moe"] if args.kernel == "all" else [args.kernel]
    
    if args.once:
        # Single submission
        for kernel in kernels:
            print(f"\n🚀 Single submission for {kernel.upper()}")
            test_success, _ = submit_kernel(kernel, "test")
            if test_success:
                bench_success, timing = submit_kernel(kernel, "benchmark")
                if bench_success and timing:
                    check_improvement(kernel, timing)
                    submit_kernel(kernel, "leaderboard")
    else:
        # Continuous monitoring
        try:
            for kernel in kernels:
                run_continuous_submissions(kernel, args.interval)
        except KeyboardInterrupt:
            print("\n\n✅ Monitoring stopped by user")
            print(f"Results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
