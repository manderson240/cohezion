import subprocess
import sys
import time


def main():
    print("Waiting 3000 seconds for MLA rate limit...")
    for i in range(100):
        time.sleep(30)
        sys.stdout.flush()

    print("Rate limit clear. Submitting MLA...")
    cmd = "cd luma_speedrun/amd-mixed-mla && popcorn-cli submit --mode leaderboard submission_hybrid_final.py --gpu MI355X --leaderboard amd-mixed-mla --no-tui"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)


if __name__ == "__main__":
    main()
