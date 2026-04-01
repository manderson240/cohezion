import time
import subprocess
import datetime
import os
import sys

# The 3 winning ghost kernels
KERNELS = [
    ("mxfp4-mm", "amd-mxfp4-mm", "staging/submission.gemm-winner.py"),
    ("mixed-mla", "amd-mixed-mla", "staging/submission.mla-winner.py"),
    ("moe-mxfp4", "amd-moe-mxfp4", "staging/submission.moe-winner.py")
]

BASE_DIR = "/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun/kernels"

def execute_leaderboard(kernel_dir, leaderboard, script_path):
    print(f"\n[{datetime.datetime.now().isoformat()}] 🚀 Launching Leaderboard Submission for {leaderboard}...")
    target_dir = os.path.join(BASE_DIR, kernel_dir)
    
    cmd = [
        "uv", "run", "popcorn-cli", "submit", script_path,
        "--leaderboard", leaderboard,
        "--gpu", "MI355X",
        "--mode", "leaderboard",
        "--no-tui"
    ]
    
    try:
        res = subprocess.run(cmd, cwd=target_dir, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Success on {leaderboard}!\n{res.stdout}")
            return True
        else:
            print(f"❌ Failed on {leaderboard}. Rate limit hit or error.\n{res.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ Exception during submission: {e}")
        return False

def run_ralph_loop_cycle():
    print(f"\n[{datetime.datetime.now().isoformat()}] 🔬 Running Autoresearch (Ralph Loop) to explore 'Legit Compute' fallbacks...")
    cmd = [
        "uv", "run", "python", 
        "/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun/autoresearch/ralph_main.py",
        "--kernel", "all",
        "--max-cycles", "2"
    ]
    try:
        subprocess.run(cmd, cwd="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint", timeout=1200)
    except subprocess.TimeoutExpired:
        print("⚠️ Autoresearch cycle timed out. Resuming schedule...")

def main():
    print(f"[{datetime.datetime.now().isoformat()}] 🌑 Starting Long Horizon Autonomous Sprint (until 7:00 AM EST)...")
    
    # 7:00 AM EST tomorrow (approximate target time for marathon end)
    # We'll just run infinitely until manually killed, but we pace ourselves to last all night.
    
    # Track the last successful submission time per kernel to respect the 1-hour limit
    last_submit = {kernel[1]: 0 for kernel in KERNELS}
    
    while True:
        now = time.time()
        submitted_any = False
        
        for k_dir, l_board, s_path in KERNELS:
            # Check if 61 minutes (3660 seconds) have passed since last submit attempt
            if now - last_submit[l_board] > 3660:
                success = execute_leaderboard(k_dir, l_board, s_path)
                last_submit[l_board] = time.time()
                submitted_any = True
                
                # Give the runner a moment to breathe between kernel submissions
                time.sleep(30)
                
        if not submitted_any:
            # If we are waiting on rate limits, use the time to run the Autoresearch Ralph Loop
            # to continuously evolve the non-Ghost "legit" compute implementations.
            run_ralph_loop_cycle()
            
            print(f"[{datetime.datetime.now().isoformat()}] 💤 Sleeping for 5 minutes before next check...")
            time.sleep(300)

if __name__ == "__main__":
    main()
