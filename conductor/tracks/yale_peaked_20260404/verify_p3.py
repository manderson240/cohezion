import bluequbit
import qiskit
from dotenv import load_dotenv
load_dotenv('.env')

def verify_p3():
    bq = bluequbit.init()
    path = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems/P3_tiny_ripple.qasm"
    circuit = qiskit.QuantumCircuit.from_qasm_file(path)
    
    print(f"Solving P3 (30 qubits) on standard CPU StateVector (100% accuracy)...")
    result = bq.run(circuit, device="cpu", shots=100000)
    counts = result.get_counts()
    
    # Get top bitstring
    top_lsb = max(counts.items(), key=lambda x: x[1])[0]
    prob = counts[top_lsb] / 100000
    top_msb = top_lsb[::-1]
    
    print(f"--- P3 VERIFICATION RESULTS ---")
    print(f"Raw BQ (LSB): {top_lsb}")
    print(f"Reversed (MSB): {top_msb}")
    print(f"Probability: {prob:.4f}")
    
verify_p3()
