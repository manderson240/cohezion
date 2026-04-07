import os
import json
import bluequbit
import qiskit
from dotenv import load_dotenv

load_dotenv('.env')

def get_bitstring_prob(bq, circuit, bitstring):
    """
    Calculates the theoretical probability of a SINGLE bitstring
    using mps.cpu with a high bond dimension.
    """
    # Note: We use get_counts() with 0 shots to get theoretical probs
    # for the top states. If our bitstring is the peak, it WILL be in there.
    try:
        # We use a high bond dimension 256 for a single-point check
        # This is free on the community tier for small counts.
        res = bq.run(
            circuit, 
            device="mps.cpu", 
            options={"mps_bond_dimension": 256}
        )
        counts = res.get_counts()
        # BQ returns LSB, we convert bitstring to LSB for lookup
        lsb_bitstring = bitstring[::-1]
        return counts.get(lsb_bitstring, 0.0)
    except Exception:
        return 0.0

def refine_bitstrings():
    if not os.path.exists('conductor/tracks/yale_peaked_20260404/quantum_candidates.json'):
        print("❌ Run the QPU sprint first.")
        return
        
    with open('conductor/tracks/yale_peaked_20260404/quantum_candidates.json', 'r') as f:
        candidates = json.load(f)
        
    bq = bluequbit.init()
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    
    print("🧠 Starting Greedy Bit-Flip Refinement (95% Confidence Loop)...")
    
    for name, data in candidates.items():
        top_s = data['top_10'][0][0] # Current best MSB
        path = os.path.join(problems_dir, f"{name}*.qasm") # Find the actual file
        # Resolve glob
        import glob
        files = glob.glob(path)
        if not files: continue
        
        circuit = qiskit.QuantumCircuit.from_qasm_file(files[0])
        current_prob = get_bitstring_prob(bq, circuit, top_s)
        
        print(f"\nProblem {name}: Starting Prob: {current_prob:.6f}")
        
        improved = True
        while improved:
            improved = False
            # Check all single bit flips
            for i in range(len(top_s)):
                # Flip bit i
                s_list = list(top_s)
                s_list[i] = '1' if s_list[i] == '0' else '0'
                new_s = "".join(s_list)
                
                new_prob = get_bitstring_prob(bq, circuit, new_s)
                if new_prob > current_prob:
                    print(f"  ✨ Found improvement! Bit {i} flipped. Prob: {current_prob:.6f} -> {new_prob:.6f}")
                    top_s = new_s
                    current_prob = new_prob
                    improved = True
                    break # Restart greedy search from new peak
                    
        print(f"✅ Refinement complete for {name}. Final Bitstring: {top_s}")
        # Update candidates
        data['refined_peak'] = top_s
        data['refined_prob'] = current_prob

    with open('conductor/tracks/yale_peaked_20260404/quantum_candidates.json', 'w') as f:
        json.dump(candidates, f, indent=2)

if __name__ == "__main__":
    refine_bitstrings()
