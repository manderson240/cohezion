import os

import qiskit
from qiskit import transpile


def transpile_all():
    problems_dir = "bluequbit/hackathons/hackathon_wSvCWg8f38spoXX3/problems"
    output_dir = "conductor/tracks/yale_peaked_20260404/optimized_qasm"
    os.makedirs(output_dir, exist_ok=True)

    # Use standard basis set for Qiskit optimization
    basis_gates = ["rx", "ry", "rz", "cz"]

    targets = [
        "P5_soft_rise.qasm",
        "P6_low_hill.qasm",
        "P7_rolling_ridge.qasm",
        "P8_bold_peak.qasm",
        "P9_grand_summit.qasm",
        "P10_eternal_mountain.qasm",
    ]

    print("🛠️ Starting Level 3 Optimization (Standard Basis)...")

    for filename in targets:
        path = os.path.join(problems_dir, filename)
        out_path = os.path.join(output_dir, filename)

        print(f"  Optimizing {filename}...")
        circuit = qiskit.QuantumCircuit.from_qasm_file(path)

        # Optimize depth and gate count
        optimized = transpile(
            circuit, basis_gates=basis_gates, optimization_level=3, seed_transpiler=42
        )

        # Save optimized QASM
        from qiskit import qasm2

        qasm_str = qasm2.dumps(optimized)
        with open(out_path, "w") as f:
            f.write(qasm_str)

        orig_gates = circuit.num_nonlocal_gates()
        new_gates = optimized.num_nonlocal_gates()

        print(
            f"    ✅ Done. 2Q Gates: {orig_gates} -> {new_gates} | Depth: {circuit.depth()} -> {optimized.depth()}"
        )


if __name__ == "__main__":
    transpile_all()
