import os
import json
import subprocess
import sys

# Ensure dependencies are available for this specific hackathon run
def ensure_deps():
    try:
        import bluequbit
        import qiskit
        import dotenv
    except ImportError:
        print("📦 Installing missing dependencies (bluequbit, qiskit, python-dotenv)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "bluequbit", "qiskit", "python-dotenv"])

ensure_deps()

from batch_solver import BatchSolver
from solve_peaked_circuit import solve_peaked_circuit

def run_free_tier_sprint():
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    
    # All problems P1-P10 for the free tier baseline
    all_problems = {
        'P1': os.path.join(problems_dir, 'P1_little_peak.qasm'),
        'P2': os.path.join(problems_dir, 'P2_small_bump.qasm'),
        'P3': os.path.join(problems_dir, 'P3_tiny_ripple.qasm'),
        'P4': os.path.join(problems_dir, 'P4_gentle_mound.qasm'),
        'P5': os.path.join(problems_dir, 'P5_soft_rise.qasm'),
        'P6': os.path.join(problems_dir, 'P6_low_hill.qasm'),
        'P7': os.path.join(problems_dir, 'P7_rolling_ridge.qasm'),
        'P8': os.path.join(problems_dir, 'P8_bold_peak.qasm'),
        'P9': os.path.join(problems_dir, 'P9_grand_summit.qasm'),
        'P10': os.path.join(problems_dir, 'P10_eternal_mountain.qasm')
    }
    
    # Load existing results if they exist
    results = {}
    if os.path.exists('conductor/tracks/yale_peaked_20260404/interim_results.json'):
        with open('conductor/tracks/yale_peaked_20260404/interim_results.json', 'r') as f:
            results = json.load(f)
    
    # PROBLEMS TO RUN
    # 1. P3 MUST be retried on 'cpu' device (30 qubits is safe)
    # 2. P5-P10 on 'mps.cpu' with bond_dim=4 (to bypass RAM limits)
    # 3. P7 retry on 'mps.cpu' with bond_dim=4
    
    run_queue = []
    
    # Add P3 (Standard SV)
    run_queue.append(('P3', all_problems['P3'], 'cpu', None))
    
    # Add P5-P8 (Refinement Sprint with Majority Voting)
    for p in ['P5', 'P6', 'P7', 'P8']:
        run_queue.append((p, all_problems[p], 'mps.cpu', 8))

    # Add P9-P10 (Advanced Refinement with Bootstrap Majority Voting)
    for p in ['P9', 'P10']:
        run_queue.append((p, all_problems[p], 'mps.cpu', 16))

    print(f"🚀 Starting Extended Refinement Sprint (P5-P10) with Bootstrap Majority Voting...")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_name = {
            executor.submit(solve_peaked_circuit, path, shots=100000, bond_dim=bd, device=dev): name 
            for name, path, dev, bd in run_queue
        }
        
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                if result:
                    results[name] = result
                    print(f"✅ Baseline Landed: {name} -> {result['bitstring']} (SNR: {result['snr']:.2f})")
                    # Incremental Save
                    with open('conductor/tracks/yale_peaked_20260404/interim_results.json', 'w') as f:
                        json.dump(results, f, indent=2)
                    # Regenerate Report
                    subprocess.run([sys.executable, "conductor/tracks/yale_peaked_20260404/submission_generator.py"])
                else:
                    print(f"❌ Baseline Failed: {name}")
            except Exception as e:
                print(f"❌ Error in {name}: {e}")
    
    print(f"\n✅ Targeted Free Tier Baseline Sprint Complete.")

if __name__ == '__main__':
    run_free_tier_sprint()
