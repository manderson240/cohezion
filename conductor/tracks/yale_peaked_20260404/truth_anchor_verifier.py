import json
import os

def verify_and_prepare_submissions():
    """
    Analyzes the Top-10 candidates from the Quantum QPU runs.
    Because peaked circuits have a single dominant bitstring, 
    the true peak will stand out significantly from the noise floor.
    """
    if not os.path.exists('conductor/tracks/yale_peaked_20260404/quantum_candidates.json'):
        print("❌ No quantum candidates found. Run the QPU sprint first.")
        return
        
    with open('conductor/tracks/yale_peaked_20260404/quantum_candidates.json', 'r') as f:
        candidates_data = json.load(f)
        
    results = {}
    if os.path.exists('conductor/tracks/yale_peaked_20260404/interim_results.json'):
        with open('conductor/tracks/yale_peaked_20260404/interim_results.json', 'r') as f:
            results = json.load(f)
            
    print("📊 --- QUANTUM PEAK ANALYSIS ---")
    
    for name, data in candidates_data.items():
        top_10 = data.get("top_10", [])
        total_shots = data.get("total_shots", 2000)
        
        if not top_10:
            continue
            
        top_candidate, top_count = top_10[0]
        second_count = top_10[1][1] if len(top_10) > 1 else 0
        
        # Calculate the separation ratio (Signal vs. next best noise)
        separation_ratio = top_count / second_count if second_count > 0 else float('inf')
        probability = top_count / total_shots
        
        print(f"\n{name} Analysis (Shots: {total_shots}):")
        print(f"  Top Candidate: {top_candidate} (Count: {top_count})")
        print(f"  2nd Candidate: {top_10[1][0] if len(top_10)>1 else 'N/A'} (Count: {second_count})")
        print(f"  Separation Ratio: {separation_ratio:.2f}x")
        
        # If the top candidate occurs significantly more often than the second, it is the peak.
        if separation_ratio > 2.0:
            print("  ✅ VERIFIED: Clear Peak Detected.")
            results[name] = {
                "bitstring": top_candidate,
                "probability": probability,
                "snr": separation_ratio, # Using separation ratio as SNR for QPU runs
                "num_heavy": top_count,
                "method": "Rigetti Ankaa-3 (QPU) + Fire Opal"
            }
        else:
            print("  ⚠️ WARNING: Weak Peak. Signal may be buried in noise.")
            
    # Save the verified results
    with open('conductor/tracks/yale_peaked_20260404/interim_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    # Regenerate the submission report
    import subprocess
    import sys
    print("\n📝 Regenerating FINAL_SUBMISSION_REPORT.md...")
    subprocess.run([sys.executable, "conductor/tracks/yale_peaked_20260404/submission_generator.py"])
    print("Done.")

if __name__ == '__main__':
    verify_and_prepare_submissions()
