import time
import subprocess
import sys


def main():
    print("Waiting 3000 seconds for rate limit...")
    for i in range(100):
        time.sleep(30)
        print(f"Elapsed: {(i + 1) * 30} seconds...")
        sys.stdout.flush()

    print("Rate limit should be clear. Submitting MoE...")
    cmd = "cd luma_speedrun/deploy/tier2_best && popcorn-cli submit --mode leaderboard moe_dispatch_policy.py --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)


if __name__ == "__main__":
    main()
