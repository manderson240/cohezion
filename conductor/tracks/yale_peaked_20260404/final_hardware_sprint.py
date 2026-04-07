import os
import json
import bluequbit
import qiskit
import time
import glob
from dotenv import load_dotenv

load_dotenv('.env')

def solve_problem(name, qasm_path, shots):
    bq = bluequbit.init()
    circuit = qiskit.QuantumCircuit.from_qasm_file(qasm_path)
    
    if not any(instr.name == 'measure' for instr, _, _ in circuit.data):
        circuit.measure_all()
        
    print(f"\n🚀 SUBMITTING: {name} to QUANTUM HARDWARE (shots: {shots})...")
    
    try:
        job = bq.run(
            circuit,
            device='quantum',
            shots=shots,
            asynchronous=True
        )
        
        job_id = job.job_id
        print(f"✅ Job {job_id} Submitted.")
        return name, job_id
    except Exception as e:
        print(f"❌ Error submitting {name}: {e}")
        return name, None

def run_hardware_sprint():
    opt_dir = "conductor/tracks/yale_peaked_20260404/optimized_qasm"
    results_file = 'conductor/tracks/yale_peaked_20260404/interim_results.json'
    
    # Load existing
    results = {}
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            results = json.load(f)

    # Use optimized QASM files to stay under the 20k gate limit
    tasks = [
        ('P5', glob.glob(f"{opt_dir}/P5*.qasm")[0], 1000),
        ('P6', glob.glob(f"{opt_dir}/P6*.qasm")[0], 1000),
        ('P7', glob.glob(f"{opt_dir}/P7*.qasm")[0], 1000),
        ('P8', glob.glob(f"{opt_dir}/P8*.qasm")[0], 1000),
        ('P9', glob.glob(f"{opt_dir}/P9*.qasm")[0], 2000),
        ('P10', glob.glob(f"{opt_dir}/P10*.qasm")[0], 2000),
    ]

    job_ids = {}
    for name, path, shots in tasks:
        _, jid = solve_problem(name, path, shots)
        if jid:
            job_ids[name] = jid

    print("\n⏳ Waiting for Quantum Jobs to complete...")
    bq = bluequbit.init()
    
    start_time = time.time()
    
    for name, jid in job_ids.items():
        print(f"Waiting for {name} ({jid})...")
        while True:
            try:
                job = bq.get(jid)
                if job.run_status == 'COMPLETED':
                    counts = job.get_counts()
                    total = sum(counts.values())
                    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
                    top_bs_lsb, top_count = sorted_counts[0]
                    top_bs_msb = top_bs_lsb[::-1] # Reverse LSB to MSB
                    
                    results[name] = {
                        "bitstring": top_bs_msb,
                        "probability": top_count / total,
                        "snr": (top_count / total) * (2**len(top_bs_lsb)),
                        "method": "Real Quantum Hardware (Optimized QASM)",
                        "job_id": jid
                    }
                    print(f"🎉 {name} COMPLETED! Answer: {top_bs_msb}")
                    with open(results_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    break
                elif job.run_status in ['FAILED_VALIDATION', 'TERMINATED', 'NOT_ENOUGH_FUNDS', 'CANCELED']:
                    print(f"❌ Job {jid} FAILED with status: {job.run_status}")
                    break
                else:
                    time.sleep(15)
            except Exception as e:
                print(f"Error checking {name}: {e}")
                time.sleep(15)
                
    # Update report
    import subprocess
    import sys
    subprocess.run([sys.executable, 'conductor/tracks/yale_peaked_20260404/submission_generator.py'])
    print("✅ FINAL REPORT REGENERATED")

if __name__ == "__main__":
    run_hardware_sprint()
