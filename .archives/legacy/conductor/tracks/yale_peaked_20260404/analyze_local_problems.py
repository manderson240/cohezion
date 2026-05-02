import os

import qiskit


def analyze_circuit(qasm_file):
    """
    Analyzes a QASM file for qubit count, gate count, and types.
    """
    try:
        circuit = qiskit.QuantumCircuit.from_qasm_file(qasm_file)

        # Filter out barriers
        gate_types = [
            inst.operation.name for inst in circuit.data if inst.operation.name != "barrier"
        ]

        return {
            "qubits": circuit.num_qubits,
            "gates": len(gate_types),
            "depth": circuit.depth(),
            "gate_types": set(gate_types),
        }
    except Exception as e:
        print(f"Error analyzing {qasm_file}: {e}")
        return None


def analyze_all_problems(directory):
    """
    Analyzes all QASM problems in a directory.
    """
    results = {}
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".qasm"):
            path = os.path.join(directory, filename)
            analysis = analyze_circuit(path)
            if analysis:
                results[filename] = analysis
    return results


if __name__ == "__main__":
    # When run as a script, analyze the default problems directory
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    if os.path.exists(problems_dir):
        report = analyze_all_problems(problems_dir)
        print("\n--- Problem Set Analysis ---")
        for file, data in report.items():
            print(f"{file}: Qubits={data['qubits']}, Gates={data['gates']}, Depth={data['depth']}")
    else:
        print(f"Directory not found: {problems_dir}")
