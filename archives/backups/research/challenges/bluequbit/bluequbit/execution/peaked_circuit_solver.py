"""
Peaked Circuit Solver
Based on Tutorial 2: Breaking Peaked Quantum Circuits Classically

Winning strategy for peaked circuit challenges.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

import json
import time
from dataclasses import dataclass

import bluequbit
import numpy as np
import qiskit
from dotenv import load_dotenv


@dataclass
class PeakedCircuitResult:
    """Result from solving peaked circuit."""

    bitstring: str
    probability: float
    snr: float
    num_heavy: int
    confidence: str
    runtime: float
    bond_dimension: int
    shots: int


class PeakedCircuitSolver:
    """
    Solver for peaked circuit challenges.

    Strategy from Tutorial 2:
    1. High-shot sampling (100k+)
    2. Appropriate bond dimension
    3. Heavy output detection
    4. SNR validation
    """

    def __init__(self, bq=None):
        """Initialize solver."""
        if bq is None:
            load_dotenv(".env")
            bq = bluequbit.init()
        self.bq = bq

        print("✓ PeakedCircuitSolver initialized")

    def solve(
        self,
        circuit: qiskit.QuantumCircuit,
        shots: int = 100000,
        bond_dimension: int | None = None,
    ) -> PeakedCircuitResult:
        """
        Solve peaked circuit challenge.

        Args:
            circuit: Quantum circuit to solve
            shots: Number of shots (default 100000)
            bond_dimension: MPS bond dimension (auto if None)

        Returns:
            PeakedCircuitResult with winning bitstring
        """
        n_qubits = circuit.num_qubits

        # Auto-determine bond dimension
        if bond_dimension is None:
            bond_dimension = self._select_bond_dimension(n_qubits)

        print(f"\n{'=' * 70}")
        print("Solving Peaked Circuit")
        print(f"{'=' * 70}")
        print(f"Qubits: {n_qubits}")
        print(f"Bond dimension: {bond_dimension}")
        print(f"Shots: {shots}")

        # Execute
        start = time.time()
        result = self.bq.run(
            circuit, device="mps.cpu", shots=shots, options={"mps_bond_dimension": bond_dimension}
        )
        elapsed = time.time() - start

        counts = result.get_counts()
        print(f"✓ Execution complete in {elapsed:.2f}s")
        print(f"✓ {len(counts)} distinct states")

        # Find heavy output
        heavy_result = self._find_heavy_output(counts, n_qubits)

        if heavy_result is None:
            raise ValueError("No heavy output found - circuit may not be peaked")

        # Determine confidence
        confidence = self._assess_confidence(heavy_result["snr"])

        return PeakedCircuitResult(
            bitstring=heavy_result["bitstring"],
            probability=heavy_result["probability"],
            snr=heavy_result["snr"],
            num_heavy=heavy_result["num_heavy"],
            confidence=confidence,
            runtime=elapsed,
            bond_dimension=bond_dimension,
            shots=shots,
        )

    def _select_bond_dimension(self, n_qubits: int) -> int:
        """Select appropriate bond dimension."""
        if n_qubits <= 10:
            return 64
        elif n_qubits <= 20:
            return 128
        elif n_qubits <= 30:
            return 256
        else:
            return 512

    def _find_heavy_output(
        self, counts: dict, n_qubits: int, threshold: float = 0.5
    ) -> dict | None:
        """
        Find heavy output bitstring.

        Based on Tutorial 2 strategy:
        - Calculate uniform probability
        - Find outputs above threshold
        - Return highest probability with SNR
        """
        total = sum(counts.values())
        uniform_prob = 1.0 / (2**n_qubits)
        threshold_prob = threshold * uniform_prob

        # Find heavy outputs
        heavy = {b: c / total for b, c in counts.items() if c / total > threshold_prob}

        if not heavy:
            return None

        # Get top
        top_bitstring = max(heavy.items(), key=lambda x: x[1])
        top_prob = top_bitstring[1]

        # Calculate SNR
        signal = top_prob - uniform_prob
        noise = np.sqrt(uniform_prob * (1 - uniform_prob))
        snr = signal / noise if noise > 0 else 0

        return {
            "bitstring": top_bitstring[0],
            "probability": top_prob,
            "snr": snr,
            "num_heavy": len(heavy),
        }

    def _assess_confidence(self, snr: float) -> str:
        """Assess confidence level from SNR."""
        if snr >= 10:
            return "VERY HIGH"
        elif snr >= 5:
            return "HIGH"
        elif snr >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def validate_before_submission(self, result: PeakedCircuitResult, min_snr: float = 2.0) -> bool:
        """
        Validate result before submission.

        Args:
            result: Result to validate
            min_snr: Minimum acceptable SNR

        Returns:
            True if valid for submission
        """
        print(f"\n{'=' * 70}")
        print("Pre-Submission Validation")
        print(f"{'=' * 70}")

        checks = []

        # Check SNR
        if result.snr >= min_snr:
            print(f"✓ SNR: {result.snr:.2f} >= {min_snr}")
            checks.append(True)
        else:
            print(f"✗ SNR: {result.snr:.2f} < {min_snr}")
            checks.append(False)

        # Check probability
        if result.probability >= 0.05:
            print(f"✓ Probability: {result.probability:.4f} >= 0.05")
            checks.append(True)
        else:
            print(f"✗ Probability: {result.probability:.4f} < 0.05")
            checks.append(False)

        # Check confidence
        if result.confidence in ["HIGH", "VERY HIGH"]:
            print(f"✓ Confidence: {result.confidence}")
            checks.append(True)
        else:
            print(f"✗ Confidence: {result.confidence}")
            checks.append(False)

        all_passed = all(checks)

        if all_passed:
            print("\n✓ VALIDATED - Ready for submission")
        else:
            print("\n✗ NOT VALIDATED - Review before submission")

        return all_passed

    def format_submission(self, result: PeakedCircuitResult) -> dict:
        """Format result for submission."""
        return {
            "bitstring": result.bitstring,
            "probability": result.probability,
            "snr": result.snr,
            "confidence": result.confidence,
            "metadata": {
                "bond_dimension": result.bond_dimension,
                "shots": result.shots,
                "runtime": result.runtime,
            },
        }


def demo():
    """Demonstrate peaked circuit solver."""
    print("=" * 70)
    print("Peaked Circuit Solver Demo")
    print("=" * 70)

    solver = PeakedCircuitSolver()

    # Create test GHZ circuit (peaked)
    qc = qiskit.QuantumCircuit(10)
    qc.h(0)
    for i in range(9):
        qc.cx(i, i + 1)
    qc.measure_all()

    print(f"\nTest circuit: {qc.num_qubits} qubits, depth {qc.depth()}")

    # Solve
    result = solver.solve(qc, shots=10000)  # Lower for demo

    print(f"\n{'=' * 70}")
    print("Result:")
    print(f"{'=' * 70}")
    print(f"Bitstring: {result.bitstring}")
    print(f"Probability: {result.probability:.6f}")
    print(f"SNR: {result.snr:.2f} sigma")
    print(f"Confidence: {result.confidence}")
    print(f"Runtime: {result.runtime:.2f}s")

    # Validate
    is_valid = solver.validate_before_submission(result)

    if is_valid:
        submission = solver.format_submission(result)
        print("\nSubmission format:")
        print(json.dumps(submission, indent=2))

    return result


if __name__ == "__main__":
    demo()
