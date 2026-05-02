import qiskit
from qiskit import QuantumCircuit


# Ensure qiskit is available
print(f"Qiskit version: {qiskit.__version__}")

filename = "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"

try:
    qc = QuantumCircuit.from_qasm_file(filename)
    print("Circuit 'Little Dimple' loaded successfully.")
    print(f"Num Qubits: {qc.num_qubits}")
    print(f"Num Clbits: {qc.num_clbits}")
    print(f"Depth: {qc.depth()}")
    print(f"Gate Count: {sum(qc.count_ops().values())}")
    print(f"Ops: {qc.count_ops()}")

    # Check connectivity/entanglement roughly
    # Count 2-qubit gates
    two_qubit_gates = 0
    for instr in qc.data:
        if len(instr.qubits) > 1:
            two_qubit_gates += 1
    print(f"Two-qubit gates: {two_qubit_gates}")

except Exception as e:
    print(f"Error analyzing circuit: {e}")
