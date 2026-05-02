"""
Universal Challenge Solver

Auto-detects challenge type and applies appropriate strategy.
Manages limited submissions (e.g., 5) carefully.

Based on all 6 tutorials - combines:
- Peaked Circuit Solver (Tutorial 2)
- Pauli-Path Solver (Tutorial 3)
- QAOA Solver (Tutorials 4 & 5)
- VQE Solver (Tutorial 6)
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

import json
import time
from dataclasses import dataclass
from enum import Enum

import bluequbit
import qiskit
from dotenv import load_dotenv
from pauli_path_solver import PauliPathSolver
from peaked_circuit_solver import PeakedCircuitSolver
from qaoa_solver import QAOASolver


class ChallengeType(Enum):
    """Types of quantum challenges."""

    UNKNOWN = "unknown"
    PEAKED_CIRCUIT = "peaked"
    QAOA_MAXCUT = "qaoa_maxcut"
    QAOA_MIS = "qaoa_mis"
    VQE_GROUND_STATE = "vqe"
    PAULI_PATH_EXPECTATION = "pauli_path"


@dataclass
class SubmissionResult:
    """Result from challenge submission."""

    submission_number: int
    challenge_type: ChallengeType
    result: dict
    confidence: str
    runtime: float
    timestamp: float


class UniversalChallengeSolver:
    """
    Universal solver for ANY BlueQubit challenge.

    Automatically:
    1. Detects challenge type
    2. Applies optimal strategy
    3. Validates before submission
    4. Manages limited submissions
    """

    def __init__(self, bq=None, max_submissions: int = 5):
        """
        Initialize universal solver.

        Args:
            bq: BlueQubit client (auto-initialized if None)
            max_submissions: Maximum allowed submissions
        """
        if bq is None:
            load_dotenv(".env")
            bq = bluequbit.init()

        self.bq = bq
        self.max_submissions = max_submissions
        self.used_submissions = 0
        self.submission_history: list[SubmissionResult] = []

        # Initialize specialized solvers
        self.peaked_solver = PeakedCircuitSolver(bq)
        self.pauli_path_solver = PauliPathSolver(bq)
        self.qaoa_solver = QAOASolver(bq)

        print("✓ UniversalChallengeSolver initialized")
        print(f"  Max submissions: {max_submissions}")

    def detect_challenge_type(
        self, circuit: qiskit.QuantumCircuit, description: str = ""
    ) -> ChallengeType:
        """
        Auto-detect challenge type.

        Args:
            circuit: Challenge circuit
            description: Problem description

        Returns:
            ChallengeType classification
        """
        desc_lower = description.lower()
        gate_types = {inst.operation.name for inst in circuit.data}

        # Check description keywords
        if any(word in desc_lower for word in ["peak", "heavy", "dominant"]):
            return ChallengeType.PEAKED_CIRCUIT

        if any(word in desc_lower for word in ["maxcut", "cut", "partition"]):
            return ChallengeType.QAOA_MAXCUT

        if any(word in desc_lower for word in ["mis", "independent set"]):
            return ChallengeType.QAOA_MIS

        if any(word in desc_lower for word in ["ground state", "hamiltonian", "energy"]):
            return ChallengeType.VQE_GROUND_STATE

        if any(word in desc_lower for word in ["expectation", "observable"]):
            return ChallengeType.PAULI_PATH_EXPECTATION

        # Check circuit structure
        if "rzz" in gate_types or "cz" in gate_types:
            if circuit.depth() < 50:
                return ChallengeType.PEAKED_CIRCUIT

        if circuit.depth() > 50:
            return ChallengeType.VQE_GROUND_STATE

        return ChallengeType.UNKNOWN

    def solve(
        self,
        circuit: qiskit.QuantumCircuit,
        description: str = "",
        graph_edges: list[tuple[int, int]] | None = None,
        hamiltonian: list[tuple[str, float]] | None = None,
    ) -> dict:
        """
        Auto-solve challenge.

        Args:
            circuit: Challenge circuit
            description: Problem description
            graph_edges: For graph problems (QAOA)
            hamiltonian: For VQE problems

        Returns:
            Solution dictionary
        """
        print(f"\n{'=' * 70}")
        print("Universal Challenge Solver")
        print(f"{'=' * 70}")

        # Detect type
        challenge_type = self.detect_challenge_type(circuit, description)
        print(f"Detected type: {challenge_type.value}")

        # Route to appropriate solver
        if challenge_type == ChallengeType.PEAKED_CIRCUIT:
            return self._solve_peaked(circuit)

        elif challenge_type in [ChallengeType.QAOA_MAXCUT, ChallengeType.QAOA_MIS]:
            if graph_edges is None:
                raise ValueError("graph_edges required for QAOA")
            return self._solve_qaoa(circuit, graph_edges, challenge_type)

        elif challenge_type == ChallengeType.VQE_GROUND_STATE:
            if hamiltonian is None:
                raise ValueError("hamiltonian required for VQE")
            return self._solve_vqe(circuit, hamiltonian)

        elif challenge_type == ChallengeType.PAULI_PATH_EXPECTATION:
            if hamiltonian is None:
                raise ValueError("hamiltonian required for expectation")
            return self._solve_expectation(circuit, hamiltonian)

        else:
            # Default to peaked circuit (safest)
            print("Unknown type - defaulting to peaked circuit strategy")
            return self._solve_peaked(circuit)

    def _solve_peaked(self, circuit: qiskit.QuantumCircuit) -> dict:
        """Solve peaked circuit."""
        result = self.peaked_solver.solve(circuit)

        return {
            "type": "peaked_circuit",
            "bitstring": result.bitstring,
            "probability": result.probability,
            "snr": result.snr,
            "confidence": result.confidence,
        }

    def _solve_qaoa(
        self,
        circuit: qiskit.QuantumCircuit,
        graph_edges: list[tuple[int, int]],
        challenge_type: ChallengeType,
    ) -> dict:
        """Solve QAOA challenge."""
        n_nodes = circuit.num_qubits

        if challenge_type == ChallengeType.QAOA_MAXCUT:
            result = self.qaoa_solver.solve_maxcut(graph_edges, n_nodes)
        else:  # MIS
            result = self.qaoa_solver.solve_mis(graph_edges, n_nodes)

        return {
            "type": challenge_type.value,
            "optimal_energy": result["optimal_energy"],
            "optimal_params": result["optimal_params"].tolist(),
            "success": result["success"],
        }

    def _solve_vqe(
        self, circuit: qiskit.QuantumCircuit, hamiltonian: list[tuple[str, float]]
    ) -> dict:
        """Solve VQE challenge."""
        # Use Pauli-path for fast evaluation
        energy = self.pauli_path_solver.compute_expectation(circuit, hamiltonian)

        return {"type": "vqe", "ground_state_energy": energy}

    def _solve_expectation(
        self, circuit: qiskit.QuantumCircuit, observable: list[tuple[str, float]]
    ) -> dict:
        """Solve expectation value challenge."""
        value = self.pauli_path_solver.compute_expectation(circuit, observable)

        return {"type": "expectation", "value": value}

    def submit_with_validation(
        self, result: dict, min_confidence: str = "MEDIUM"
    ) -> SubmissionResult | None:
        """
        Submit with validation (respects submission limit).

        Args:
            result: Result to submit
            min_confidence: Minimum confidence level

        Returns:
            SubmissionResult if submitted, None if blocked
        """
        if self.used_submissions >= self.max_submissions:
            print(f"❌ Submission limit reached ({self.max_submissions})")
            return None

        # Validate confidence
        confidence = result.get("confidence", "UNKNOWN")
        confidence_levels = ["LOW", "MEDIUM", "HIGH", "VERY HIGH"]

        if confidence not in confidence_levels:
            print(f"⚠️ Unknown confidence: {confidence}")
            return None

        if confidence_levels.index(confidence) < confidence_levels.index(min_confidence):
            print(f"⚠️ Confidence {confidence} < {min_confidence}")
            return None

        # Submit
        self.used_submissions += 1

        submission = SubmissionResult(
            submission_number=self.used_submissions,
            challenge_type=ChallengeType(result.get("type", "unknown")),
            result=result,
            confidence=confidence,
            runtime=result.get("runtime", 0),
            timestamp=time.time(),
        )

        self.submission_history.append(submission)

        print(f"\n{'=' * 70}")
        print(f"📤 SUBMISSION {submission.submission_number}/{self.max_submissions}")
        print(f"{'=' * 70}")
        print(f"Type: {submission.challenge_type.value}")
        print(f"Confidence: {submission.confidence}")
        print(f"Result: {json.dumps(result, indent=2)}")

        return submission

    def get_submission_summary(self) -> dict:
        """Get summary of all submissions."""
        return {
            "used": self.used_submissions,
            "remaining": self.max_submissions - self.used_submissions,
            "max": self.max_submissions,
            "submissions": [
                {
                    "number": s.submission_number,
                    "type": s.challenge_type.value,
                    "confidence": s.confidence,
                    "result": s.result,
                }
                for s in self.submission_history
            ],
        }


def demo():
    """Demonstrate Universal Challenge Solver."""
    print("=" * 70)
    print("Universal Challenge Solver Demo")
    print("=" * 70)

    solver = UniversalChallengeSolver(max_submissions=5)

    # Demo 1: Peaked circuit
    print("\n" + "=" * 70)
    print("Demo 1: Peaked Circuit")
    print("=" * 70)

    qc = qiskit.QuantumCircuit(8)
    qc.h(0)
    for i in range(7):
        qc.cx(i, i + 1)
    qc.measure_all()

    result = solver.solve(qc, description="Find heavy output from peaked circuit")

    print(f"\nResult: {result}")

    # Validate and submit
    submission = solver.submit_with_validation(result, min_confidence="MEDIUM")

    # Summary
    summary = solver.get_submission_summary()
    print(f"\n{'=' * 70}")
    print("Submission Summary:")
    print(f"{'=' * 70}")
    print(f"Used: {summary['used']}/{summary['max']}")
    print(f"Remaining: {summary['remaining']}")

    return result


if __name__ == "__main__":
    demo()
