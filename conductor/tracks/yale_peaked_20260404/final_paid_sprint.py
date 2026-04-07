import os
import json
import subprocess
import sys
from batch_solver import BatchSolver
from dotenv import load_dotenv

load_dotenv('.env')

def run_paid_refinement_sprint():
    """
    Executes a batched, cached, and paid-tier sprint for P5-P10.
    """
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    
    # 1. P5-P8: Medium-High Bond Dim (MPS.GPU)
    p5_p8_problems = {
        'P5': os.path.join(problems_dir, 'P5_soft_rise.qasm'),
        'P6': os.path.join(problems_dir, 'P6_low_hill.qasm'),
        'P7': os.path.join(problems_dir, 'P7_rolling_ridge.qasm'),
        'P8': os.path.join(problems_dir, 'P8_bold_peak.qasm')
    }
    
    # 2. P9-P10: High Bond Dim (MPS.GPU)
    p9_p10_problems = {
        'P9': os.path.join(problems_dir, 'P9_grand_summit.qasm'),
        'P10': os.path.join(problems_dir, 'P10_eternal_mountain.qasm')
    }

    # Solver instance with 2 workers for safety
    solver = BatchSolver(max_workers=2)
    
    # Load current interim results to sync
    results_file = 'conductor/tracks/yale_peaked_20260404/interim_results.json'
    results = {}
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            results = json.load(f)

    # ---------------------------------------------------------
    # BATCH 1: P5-P8 | Device: mps.gpu | Bond Dim: 256 | Shots: 5k
    # ---------------------------------------------------------
    print(f"\n🚀 EXECUTING BATCH 1 (P5-P8) | mps.gpu | Bond Dim: 256 | Shots: 5k...")
    batch1_results = solver.solve_all(p5_p8_problems, shots=5000, device="mps.gpu", bond_dim=256, allow_paid=True)
    results.update(batch1_results)

    # ---------------------------------------------------------
    # BATCH 2: P10 | Device: mps.gpu | Bond Dim: 512 | Shots: 10k
    # ---------------------------------------------------------
    print(f"\n🚀 EXECUTING BATCH 2 (P10) | mps.gpu | Bond Dim: 512 | Shots: 10k...")
    batch2_results = solver.solve_all({'P10': p9_p10_problems['P10']}, shots=10000, device="mps.gpu", bond_dim=512, allow_paid=True)
    results.update(batch2_results)

    # ---------------------------------------------------------
    # BATCH 3: P9 | Device: mps.gpu | Bond Dim: 512 | Shots: 15k
    # ---------------------------------------------------------
    print(f"\n🚀 EXECUTING BATCH 3 (P9) | mps.gpu | Bond Dim: 512 | Shots: 15k...")
    batch3_results = solver.solve_all({'P9': p9_p10_problems['P9']}, shots=15000, device="mps.gpu", bond_dim=512, allow_paid=True)
    results.update(batch3_results)

    # Sync and Update Report
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ All batches synced. Regenerating final submission report...")
    subprocess.run([sys.executable, 'conductor/tracks/yale_peaked_20260404/submission_generator.py'])

if __name__ == "__main__":
    run_paid_refinement_sprint()
