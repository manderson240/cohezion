import os
import subprocess
import time


# List of kernel directories and their leaderboards
KERNELS = {"moe-mxfp4": "3_moe_mxfp4", "mixed-mla": "4_mixed_mla", "mxfp4-mm": "5_mxfp4_mm"}

BASE_DIR = "research/challenges/luma_amd_speedrun/kernels"
RESULTS_FILE = "research/challenges/luma_amd_speedrun/results.md"


def run_benchmark(kernel_name, leaderboard):
    print(f"\n🚀 Benchmarking {kernel_name} on {leaderboard}...")
    kernel_path = os.path.join(BASE_DIR, kernel_name, "submission.py")

    # We use reference.py as our first "submission" to get the baseline
    # But since the CLI expects submission.py, we just point to it
    # as the baseline provided by AMD.

    cmd = [
        "popcorn-cli",
        "submit",
        "--leaderboard",
        leaderboard,
        "--mode",
        "benchmark",
        "--no-tui",
        kernel_path,
    ]

    try:
        env = os.environ.copy()
        env["PATH"] = f"{os.path.expanduser('~')}/.local/bin:{env.get('PATH', '')}"

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode == 0:
            print(f"✅ Benchmark completed for {kernel_name}")
            return result.stdout
        else:
            print(f"❌ Benchmark failed for {kernel_name}")
            print(result.stderr)
            return None
    except Exception as e:
        print(f"💥 Error running benchmark: {e}")
        return None


def main():
    results = []

    for name, board in KERNELS.items():
        output = run_benchmark(name, board)
        if output:
            results.append(f"### {name} ({board})\n```\n{output}\n```\n")
        time.sleep(2)  # Brief pause between submissions

    with open(RESULTS_FILE, "w") as f:
        f.write("# Baseline Performance Results\n\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("".join(results))

    print(f"\n📊 Results written to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
