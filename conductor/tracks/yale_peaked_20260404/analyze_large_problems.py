import bluequbit
import qiskit
import os

def estimate_large_problems():
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    large_problems = ['P5_soft_rise.qasm', 'P6_low_hill.qasm', 'P8_bold_peak.qasm', 'P9_grand_summit.qasm', 'P10_eternal_mountain.qasm']
    
    bq = bluequbit.init()
    
    print("# Large Problem Cost & Resource Estimation\n")
    print("| Problem | Qubits | Device | Bond Dim | Estimated Cost | Rationale |")
    print("|---------|--------|--------|----------|----------------|-----------|")
    
    for filename in large_problems:
        path = os.path.join(problems_dir, filename)
        if not os.path.exists(path):
            continue
            
        circuit = qiskit.QuantumCircuit.from_qasm_file(path)
        n_qubits = circuit.num_qubits
        
        # Estimation logic based on BlueQubit pricing and experience
        # Note: Actual estimation comes from bq.run(..., dry_run=True) if supported, 
        # but here we provide heuristic based on the platform's limits.
        
        if n_qubits <= 50:
            print(f"| {filename[:3]} | {n_qubits} | `mps.cpu` | 32 | $0.00 | Free tier limit (with low bond_dim) |")
            print(f"| {filename[:3]} | {n_qubits} | `mps.gpu` | 512 | ~$0.50 | High accuracy target |")
        elif n_qubits <= 60:
            print(f"| {filename[:3]} | {n_qubits} | `mps.gpu` | 512 | ~$1.00 | Complex entanglement |")
        else:
            print(f"| {filename[:3]} | {n_qubits} | `mps.gpu` | 1024 | ~$2.00-5.00 | Extreme scale |")

if __name__ == '__main__':
    estimate_large_problems()
