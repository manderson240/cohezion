import bluequbit
import qiskit
from dotenv import load_dotenv
import os

load_dotenv('.env')

def test_pps():
    bq = bluequbit.init()
    # Simple 4-qubit circuit (P1)
    qc = qiskit.QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 1)
    qc.x(3) # Peak should have bit 3 as '1'
    
    # Request Zi for all 4 qubits
    pauli_sum = []
    for i in range(4):
        p_list = ['I'] * 4
        p_list[i] = 'Z'
        pauli_sum.append(("".join(p_list), 1.0))
        
    print("Testing 'pauli-path' device...")
    try:
        result = bq.run(qc, device="pauli-path", pauli_sum=pauli_sum)
        
        # Inspect the result object
        print(f"Result type: {type(result)}")
        
        # Try different ways to get values
        try:
            val = result.get_value()
            print(f"get_value(): {val} (Type: {type(val)})")
        except Exception as e:
            print(f"get_value() failed: {e}")
            
        try:
            # Based on docs search, it might be .expectation_value
            exp = result.expectation_value
            print(f"expectation_value: {exp} (Type: {type(exp)})")
        except Exception as e:
            print(f"expectation_value failed: {e}")

    except Exception as e:
        print(f"PPS Run failed: {e}")

if __name__ == "__main__":
    test_pps()
