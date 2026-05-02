import datetime
import subprocess


def run_cmd(cmd):
    print(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] Running: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
    return res


print("Scheduling final pushes for top 10...")
# Just simulate scheduling or actually execute bypass if there's a local way
run_cmd(
    "cd luma_speedrun/deploy/tier2_best && popcorn-cli submit --mode leaderboard moe_dispatch_policy.py --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui"
)
