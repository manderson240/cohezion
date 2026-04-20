"""
BlueQubit Tutorial: Solving Peaked Circuits
Learn from official SDK examples
"""

import sys
from pathlib import Path

import time
import json
import numpy as np

from dotenv import load_dotenv
import bluequbit
import qiskit


class PeakedCircuitTutorial:
    """Tutorial: Solve peaked circuits like a pro."""

    def __init__(self):
        project_root = Path("/home/mike-anderson/dev/cohezion")
        load_dotenv(project_root / ".env")
        self.bq = bluequbit.init()

    def run_tutorial(self):
        """Run complete tutorial."""
        print("=" * 70)
        print("BlueQubit Tutorial: Solving Peaked Circuits")
        print("=" * 70)
        print("\nBased on:")
        print("  • Little Dimple (SNR 9,947 sigma)")
        print("  • BlueQubit SDK examples")
        print("  • Proven winning strategies")

        # Load example circuit
        qasm_path = Path(
            "/home/mike-anderson/dev/cohezion/bluequbit/sdk-examples/peaked_circuits/qasm/peaked_circuit_8q_shallow.qasm"
        )

        print(f"\n{'=' * 70}")
        print("STEP 1: Load Circuit")
        print(f"{'=' * 70}")
        print(f"Loading: {qasm_path.name}")

        with open(qasm_path) as f:
            qasm_str = f.read()

        circuit = qiskit.QuantumCircuit.from_qasm_str(qasm_str)

        print(f"✓ Loaded: {circuit.num_qubits} qubits, depth {circuit.depth()}")

        # Analyze
        print(f"\n{'=' * 70}")
        print("STEP 2: Analyze Circuit")
        print(f"{'=' * 70}")

        gate_counts = {}
        for inst in circuit.data:
            name = inst.operation.name
            gate_counts[name] = gate_counts.get(name, 0) + 1

        print("Gate composition:")
        for gate, count in sorted(gate_counts.items()):
            print(f"  {gate}: {count}")

        print(f"\nKey observations:")
        print(f"  • Single-qubit rotations (ry, rz): Control local state")
        print(f"  • RZZ gates: Create Ising-type entanglement")
        print(f"  • CZ gates: Additional entangling layer")
        print(f"  • Ring topology: Each qubit connected to neighbors")

        # Configure
        print(f"\n{'=' * 70}")
        print("STEP 3: Configure Execution")
        print(f"{'=' * 70}")

        n_qubits = circuit.num_qubits
        bond_dim = 64 if n_qubits <= 10 else 128
        shots = 100000

        print(f"Configuration:")
        print(f"  Device: mps.cpu")
        print(f"  Bond dimension: {bond_dim}")
        print(f"  Shots: {shots}")
        print(f"  Threshold: 0.5")

        # Execute
        print(f"\n{'=' * 70}")
        print("STEP 4: Execute Circuit")
        print(f"{'=' * 70}")

        print("Submitting to BlueQubit...")
        start = time.time()

        result = self.bq.run(
            circuit, device="mps.cpu", shots=shots, options={"mps_bond_dimension": bond_dim}
        )

        elapsed = time.time() - start
        counts = result.get_counts()

        print(f"✓ Execution complete in {elapsed:.2f}s")
        print(f"✓ {len(counts)} distinct states measured")

        # Find heavy output
        print(f"\n{'=' * 70}")
        print("STEP 5: Find Heavy Output")
        print(f"{'=' * 70}")

        total = sum(counts.values())
        uniform_prob = 1.0 / (2**n_qubits)
        threshold_prob = 0.5 * uniform_prob

        print(f"Analysis:")
        print(f"  Total shots: {total}")
        print(f"  Uniform probability: {uniform_prob:.2e}")
        print(f"  Threshold (0.5×uniform): {threshold_prob:.2e}")

        heavy = {b: c / total for b, c in counts.items() if c / total > threshold_prob}

        print(f"\n✓ Heavy outputs found: {len(heavy)}")

        if not heavy:
            print("  ⚠ No heavy outputs above threshold")
            return None

        # Get top
        top = max(heavy.items(), key=lambda x: x[1])

        # Calculate SNR
        signal = top[1] - uniform_prob
        noise = np.sqrt(uniform_prob * (1 - uniform_prob))
        snr = signal / noise if noise > 0 else 0

        print(f"\n🏆 WINNING BITSTRING:")
        print(f"  Bitstring: {top[0]}")
        print(f"  Probability: {top[1]:.6f}")
        print(f"  SNR: {snr:.2f} sigma")

        print(f"\nTop 5 heavy outputs:")
        for bitstring, prob in sorted(heavy.items(), key=lambda x: x[1], reverse=True)[:5]:
            marker = " ← WINNER" if bitstring == top[0] else ""
            print(f"  {bitstring}: {prob:.6f}{marker}")

        # Package
        print(f"\n{'=' * 70}")
        print("STEP 6: Package Submission")
        print(f"{'=' * 70}")

        submission = {
            "bitstring": top[0],
            "probability": top[1],
            "snr": snr,
            "num_heavy": len(heavy),
            "shots": shots,
            "bond_dimension": bond_dim,
        }

        filename = "tutorial_submission.json"
        with open(filename, "w") as f:
            json.dump(submission, f, indent=2)

        print(f"✓ Submission saved: {filename}")
        print(f"\n{'=' * 70}")
        print("Tutorial Complete!")
        print(f"{'=' * 70}")
        print("\nKey Takeaways:")
        print("  1. Load QASM: qiskit.QuantumCircuit.from_qasm_str()")
        print("  2. High shots (100k+) for statistical significance")
        print("  3. Bond dimension: 64-512 based on qubit count")
        print("  4. Find heavy outputs: prob > 0.5×uniform")
        print("  5. Calculate SNR for confidence metric")
        print("\nReady for real challenges!")

        return submission


if __name__ == "__main__":
    tutorial = PeakedCircuitTutorial()
    tutorial.run_tutorial()
