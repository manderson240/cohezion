import os
import json
import bluequbit
import qiskit
import time
from dotenv import load_dotenv

load_dotenv(".env")


def solve_problem(name, qasm_path, device, shots, bond_dim=None):
    bq = bluequbit.init()
    circuit = qiskit.QuantumCircuit.from_qasm_file(qasm_path)

    if device == "quantum" and not any(instr.name == "measure" for instr, _, _ in circuit.data):
        circuit.measure_all()

    print(f"\n🚀 SUBMITTING: {name} to {device} (shots: {shots}, bd: {bond_dim})...")

    try:
        options = {}
        if bond_dim:
            options["mps_bond_dimension"] = bond_dim

        job = bq.run(circuit, device=device, shots=shots, options=options, asynchronous=True)

        job_id = job.job_id
        print(f"✅ Job {job_id} Submitted. Status: {job.run_status}")

        start_time = time.time()
        timeout = (
            1800 if device == "quantum" else 14400
        )  # 30 min for quantum, 4 hours for high-res CPU

        while time.time() - start_time < timeout:
            job = bq.get(job_id)
            if job.run_status == "COMPLETED":
                print(f"🎉 Job {job_id} COMPLETED!")
                counts = job.get_counts()
                total = sum(counts.values())
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
                top_bs_lsb, top_count = sorted_counts[0]
                top_bs_msb = top_bs_lsb[::-1]

                return {
                    "bitstring": top_bs_msb,
                    "probability": top_count / total,
                    "snr": (top_count / total) * (2**circuit.num_qubits),
                    "method": f"{device} (Refined)",
                    "job_id": job_id,
                }

            if job.run_status in [
                "FAILED_VALIDATION",
                "TERMINATED",
                "NOT_ENOUGH_FUNDS",
                "CANCELED",
            ]:
                print(f"❌ Job {job_id} FAILED with status: {job.run_status}")
                if job.error_message:
                    print(f"   Error: {job.error_message}")
                return None

            print(
                f"   Status: {job.run_status} (Elapsed: {int(time.time() - start_time)}s)...",
                end="\r",
            )
            time.sleep(30)

        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def run_final_sprint():
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    results_file = "conductor/tracks/yale_peaked_20260404/interim_results.json"

    # Load existing
    results = {}
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            results = json.load(f)

    # Final device allocation based on confirmed accessibility and limits
    tasks = [
        ("P6", os.path.join(problems_dir, "P6_low_hill.qasm"), "quantum", 500),
        ("P7", os.path.join(problems_dir, "P7_rolling_ridge.qasm"), "quantum", 500),
        ("P8", os.path.join(problems_dir, "P8_bold_peak.qasm"), "quantum", 500),
        ("P10", os.path.join(problems_dir, "P10_eternal_mountain.qasm"), "quantum", 500),
        ("P9", os.path.join(problems_dir, "P9_grand_summit.qasm"), "mps.cpu", 20000, 128),
    ]

    for name, path, device, shots, *opt in tasks:
        bd = opt[0] if opt else None
        res = solve_problem(name, path, device, shots, bd)
        if res:
            results[name] = res
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
            import subprocess
            import sys

            subprocess.run(
                [sys.executable, "conductor/tracks/yale_peaked_20260404/submission_generator.py"]
            )


if __name__ == "__main__":
    run_final_sprint()
