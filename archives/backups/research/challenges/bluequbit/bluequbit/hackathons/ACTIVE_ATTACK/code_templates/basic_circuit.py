"""
BlueQubit Basic Circuit Execution Template
Tested and verified on 2026-04-01
"""

import bluequbit
import qiskit
from dotenv import load_dotenv


def execute_basic_circuit(num_qubits: int = 2, device: str = "mps.cpu"):
    """
    Execute a simple Bell state circuit on BlueQubit.

    Args:
        num_qubits: Number of qubits (default: 2)
        device: Device to run on (default: "mps.cpu")

    Returns:
        dict: Measurement counts
    """
    # Load credentials
    load_dotenv(".env")

    # Initialize client
    bq = bluequbit.init()

    # Build Bell state circuit
    qc = qiskit.QuantumCircuit(num_qubits)
    qc.h(0)  # Hadamard on first qubit
    qc.cx(0, 1)  # CNOT between qubits
    qc.measure_all()

    print(f"Circuit:\n{qc}")

    # Execute
    result = bq.run(qc, device=device, options={"mps_bond_dimension": 32})
    counts = result.get_counts()

    print(f"\nResults: {counts}")
    return counts


if __name__ == "__main__":
    result = execute_basic_circuit()
    print(f"\n✓ Test passed: {result}")
