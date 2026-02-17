import json
import os
import subprocess
import time
from datetime import datetime


# Mission Configuration
TARGET_TIME = "06:00:00"
EXPERIMENT_LOG = "experiment_results.json"
BOND_DIMENSIONS = [128, 256, 384, 512]
CUTOFFS = [1e-5, 1e-6]
SAMPLING_COUNT = 100000

PYTHON_EXE = "./venv/bin/python3"


def get_current_time():
    return datetime.now().strftime("%H:%M:%S")


def run_experiment(bond_dim, cutoff):
    print(f"[{get_current_time()}] Starting Experiment: Bond Dim = {bond_dim}, Cutoff = {cutoff}")

    env = os.environ.copy()
    env["MAX_BOND"] = str(bond_dim)
    env["CUTOFF"] = str(cutoff)
    env["SAMPLING_COUNT"] = str(SAMPLING_COUNT)

    # 1. Run the solver
    start_time = time.time()
    try:
        # Increase timeout as bond_dim increases
        timeout = 1800 if bond_dim <= 256 else 3600
        subprocess.run([PYTHON_EXE, "peaked_solver.py"], env=env, check=True, timeout=timeout)
    except Exception as e:
        print(f"Solver failed or timed out: {e}")
        return None

    solver_time = time.time() - start_time

    # 2. Run the verifier
    try:
        result = subprocess.run(
            [PYTHON_EXE, "verify_result.py"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Verifier failed: {e}")
        return None

    # 3. Extract metrics
    metrics = {
        "bond_dim": bond_dim,
        "cutoff": cutoff,
        "solver_time": solver_time,
        "snr": None,
        "peak_count": None,
        "top_bitstring": None,
        "entropy": None,
        "timestamp": datetime.now().isoformat(),
    }

    for line in output.split("\n"):
        if "Signal-to-Noise Ratio (SNR):" in line:
            metrics["snr"] = float(line.split(":")[1].split()[0])
        elif "Peak Count:" in line:
            metrics["peak_count"] = int(line.split(":")[1].strip())
        elif "Rank 1:" in line:
            metrics["top_bitstring"] = line.split(":")[1].split()[0]
        elif "State Entropy:" in line:
            metrics["entropy"] = float(line.split(":")[1].split()[0])

    return metrics


def generate_report(results):
    report_path = "MISSION_REPORT.md"
    with open(report_path, "w") as f:
        f.write("# Quantum Research Mission Report\n\n")
        f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
        f.write("| Bond Dim | Cutoff | Solver Time (s) | SNR | Entropy | Top Bitstring |\n")
        f.write("|----------|--------|-----------------|-----|---------|---------------|\n")
        for r in results:
            f.write(
                f"| {r['bond_dim']} | {r['cutoff']} | {r['solver_time']:.1f} | {r['snr']} | {r['entropy']} | `{r['top_bitstring']}` |\n"
            )

    print(f"Report generated: {report_path}")


def main():
    print(f"Starting Mission Manager at {get_current_time()}")
    results = []

    if os.path.exists(EXPERIMENT_LOG):
        try:
            with open(EXPERIMENT_LOG) as f:
                results = json.load(f)
        except Exception:
            pass

    # Iterate through experiments
    for bond_dim in BOND_DIMENSIONS:
        for cutoff in CUTOFFS:
            # Check if experiment already done
            already_done = any(r["bond_dim"] == bond_dim and r["cutoff"] == cutoff for r in results)
            if already_done:
                continue

            # Check if we should stop (roughly 6 AM)
            # Current time is 01:47, target is 06:00
            now = datetime.now()
            if now.hour >= 6 and now.hour < 20:  # Stop at 6 AM
                print("Target time 06:00 reached. Ending mission.")
                return

            metrics = run_experiment(bond_dim, cutoff)
            if metrics:
                results.append(metrics)
                with open(EXPERIMENT_LOG, "w") as f:
                    json.dump(results, f, indent=4)
                generate_report(results)

            time.sleep(5)

    print(f"Mission Manager completed all planned experiments at {get_current_time()}")


if __name__ == "__main__":
    main()
