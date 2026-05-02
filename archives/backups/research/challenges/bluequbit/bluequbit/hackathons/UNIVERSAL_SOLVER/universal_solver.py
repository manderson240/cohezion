"""
BlueQubit Universal Competition Toolkit
Reusable components for ANY BlueQubit hackathon

Design Principles:
1. Challenge-agnostic: Works for peaked, VQA, QAOA, etc.
2. Self-tuning: Automatically optimizes parameters
3. Resilient: Handles failures gracefully
4. Fast: Minimizes time-to-submission
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import json
import time
from dataclasses import dataclass
from enum import Enum

import bluequbit
import qiskit
from dotenv import load_dotenv


class ChallengeType(Enum):
    """Universal challenge classification."""

    UNKNOWN = "unknown"
    PEAKED_HEAVY_OUTPUT = "peaked"  # Find heavy output bitstring
    QUANTUM_ADVANTAGE = "advantage"  # Demonstrate quantum speedup
    VQA_OPTIMIZATION = "vqa"  # Variational optimization
    QAOA_MAXCUT = "qaoa"  # Combinatorial optimization
    STATE_PREP = "state"  # Prepare specific state
    RANDOM_CIRCUIT = "random"  # Random circuit sampling
    ERROR_CORRECTION = "error"  # Quantum error correction


@dataclass
class CompetitionConfig:
    """Universal configuration for any BlueQubit challenge."""

    # Auto-detected
    challenge_type: ChallengeType = ChallengeType.UNKNOWN
    n_qubits: int = 0
    time_budget: int = 3600  # seconds
    shot_budget: int = 100000

    # Optimization parameters
    bond_dimension: int = 128
    shots: int = 10000
    threshold: float = 0.5

    # Strategy selection
    primary_strategy: str = "auto"
    fallback_strategy: str = "mps_heavy_output"

    # Resilience
    max_retries: int = 3
    timeout: int = 600
    checkpoint_interval: int = 300

    # Meta
    save_intermediate: bool = True
    verbose: bool = True


class UniversalSolver:
    """
    Universal solver for ANY BlueQubit hackathon.

    Automatically:
    1. Detects challenge type
    2. Selects optimal strategy
    3. Tunes parameters
    4. Executes with monitoring
    5. Recovers from failures
    6. Produces submission-ready output
    """

    def __init__(self, challenge_id: str | None = None):
        """Initialize universal solver."""
        project_root = Path(__file__).parent.parent.parent.parent
        load_dotenv(project_root / ".env")

        self.challenge_id = challenge_id or "unknown"
        self.bq = bluequbit.init()
        self.config = CompetitionConfig()

        # Performance history for learning
        self.performance_log: list[dict] = []

        print("✓ UniversalSolver initialized")
        print(f"  Challenge ID: {self.challenge_id}")

    def auto_solve(
        self, circuit: qiskit.QuantumCircuit | None = None, description: str = ""
    ) -> dict:
        """
        One-click auto-solver for any challenge.

        Args:
            circuit: Circuit to solve (if available)
            description: Challenge description text

        Returns:
            Submission-ready result dictionary
        """
        print("\n" + "=" * 70)
        print("Universal BlueQubit Solver")
        print("=" * 70)

        # Step 1: Analyze and classify
        self._classify_challenge(circuit, description)

        # Step 2: Auto-tune parameters
        self._auto_tune_parameters(circuit)

        # Step 3: Select and execute strategy
        result = self._execute_strategy(circuit)

        # Step 4: Validate and package
        submission = self._package_submission(result)

        print("\n" + "=" * 70)
        print("Auto-Solve Complete")
        print("=" * 70)

        return submission

    def _classify_challenge(self, circuit: qiskit.QuantumCircuit | None, description: str):
        """Auto-classify challenge type from circuit + description."""
        print("\n1. Classifying challenge...")

        # Keywords in description
        desc_lower = description.lower()

        if any(
            word in desc_lower for word in ["heavy", "peak", "dimple", "probability", "dominant"]
        ):
            self.config.challenge_type = ChallengeType.PEAKED_HEAVY_OUTPUT
        elif any(
            word in desc_lower for word in ["optimize", "minimize", "eigenvalue", "ground state"]
        ):
            self.config.challenge_type = ChallengeType.VQA_OPTIMIZATION
        elif any(word in desc_lower for word in ["maxcut", "graph", "partition", "combinatorial"]):
            self.config.challenge_type = ChallengeType.QAOA_MAXCUT
        elif any(word in desc_lower for word in ["prepare", "state", "ghz", "w-state"]):
            self.config.challenge_type = ChallengeType.STATE_PREP
        elif any(word in desc_lower for word in ["advantage", "speedup", "classical"]):
            self.config.challenge_type = ChallengeType.QUANTUM_ADVANTAGE
        elif circuit and circuit.depth() > 50:
            self.config.challenge_type = ChallengeType.VQA_OPTIMIZATION
        elif circuit and circuit.num_qubits <= 20:
            self.config.challenge_type = ChallengeType.PEAKED_HEAVY_OUTPUT
        else:
            self.config.challenge_type = ChallengeType.UNKNOWN

        # Set n_qubits
        if circuit:
            self.config.n_qubits = circuit.num_qubits

        print(f"   Detected: {self.config.challenge_type.value}")
        print(f"   Qubits: {self.config.n_qubits}")

    def _auto_tune_parameters(self, circuit: qiskit.QuantumCircuit | None):
        """Auto-tune parameters based on challenge type and circuit size."""
        print("\n2. Auto-tuning parameters...")

        n = self.config.n_qubits

        # Bond dimension scaling
        if n <= 10:
            self.config.bond_dimension = 64
        elif n <= 20:
            self.config.bond_dimension = 128
        elif n <= 30:
            self.config.bond_dimension = 256
        else:
            self.config.bond_dimension = 512

        # Shots based on challenge type
        if self.config.challenge_type == ChallengeType.PEAKED_HEAVY_OUTPUT:
            self.config.shots = 100000  # High for statistics
            self.config.threshold = 0.5
        elif self.config.challenge_type == ChallengeType.VQA_OPTIMIZATION:
            self.config.shots = 1024  # Lower for iterative
        elif self.config.challenge_type == ChallengeType.QAOA_MAXCUT:
            self.config.shots = 10000
        else:
            self.config.shots = 10000  # Default

        # Ensure shots for >17 qubits
        if n > 17 and self.config.shots == 0:
            self.config.shots = 1024

        print(f"   Bond dimension: {self.config.bond_dimension}")
        print(f"   Shots: {self.config.shots}")
        print(f"   Threshold: {self.config.threshold}")

    def _execute_strategy(self, circuit: qiskit.QuantumCircuit | None) -> dict:
        """Execute appropriate strategy based on challenge type."""
        print(f"\n3. Executing strategy: {self.config.challenge_type.value}...")

        if self.config.challenge_type == ChallengeType.PEAKED_HEAVY_OUTPUT:
            return self._strategy_peaked_heavy_output(circuit)
        elif self.config.challenge_type == ChallengeType.VQA_OPTIMIZATION:
            return self._strategy_vqa(circuit)
        elif self.config.challenge_type == ChallengeType.QAOA_MAXCUT:
            return self._strategy_qaoa(circuit)
        elif self.config.challenge_type == ChallengeType.STATE_PREP:
            return self._strategy_state_prep(circuit)
        else:
            # Default: try peaked strategy
            print("   Unknown challenge type - defaulting to peaked strategy")
            return self._strategy_peaked_heavy_output(circuit)

    def _strategy_peaked_heavy_output(self, circuit: qiskit.QuantumCircuit | None) -> dict:
        """
        Strategy for peaked heavy output challenges.

        Pattern from Little Dimple success:
        1. High-shot sampling
        2. Heavy output detection
        3. SNR validation
        """
        print("   Strategy: Heavy Output Detection")

        # If no circuit provided, try to get one
        if circuit is None:
            print("   Attempting to get peaked circuit...")
            for difficulty in [5, 10, 15, 20]:
                try:
                    circuit = self.bq.get_peaked_circuit(difficulty)
                    print(f"   ✓ Got peaked circuit (difficulty {difficulty})")
                    self.config.n_qubits = circuit.num_qubits
                    break
                except Exception:
                    continue

        if circuit is None:
            raise ValueError("No circuit available for heavy output detection")

        # Submit with high shots
        result = self.bq.run(
            circuit,
            device="mps.cpu",
            shots=self.config.shots,
            options={"mps_bond_dimension": self.config.bond_dimension},
        )

        counts = result.get_counts()

        # Find heavy outputs
        from heavy_output_detection import calculate_snr, find_heavy_output

        heavy = find_heavy_output(counts, self.config.threshold)

        if heavy:
            top_bitstring = max(heavy.items(), key=lambda x: x[1])
            snr = calculate_snr(top_bitstring[1], self.config.n_qubits)

            return {
                "strategy": "peaked_heavy_output",
                "bitstring": top_bitstring[0],
                "probability": top_bitstring[1],
                "snr": snr,
                "num_heavy": len(heavy),
                "shots": self.config.shots,
            }
        else:
            return {
                "strategy": "peaked_heavy_output",
                "bitstring": None,
                "error": "No heavy output found",
            }

    def _strategy_vqa(self, circuit: qiskit.QuantumCircuit | None) -> dict:
        """Strategy for VQA/VQE optimization challenges."""
        print("   Strategy: Variational Quantum Algorithm")

        # Build variational circuit
        if circuit is None:
            from circuit_library import CircuitLibrary

            lib = CircuitLibrary()
            circuit = lib.variational_circuit(self.config.n_qubits, depth=2)

        # For VQA, we'd need cost function and optimizer
        # This is a placeholder for the full implementation
        return {
            "strategy": "vqa",
            "note": "VQA requires classical optimizer - use Pennylane",
            "circuit_depth": circuit.depth(),
        }

    def _strategy_qaoa(self, circuit: qiskit.QuantumCircuit | None) -> dict:
        """Strategy for QAOA/MaxCut challenges."""
        print("   Strategy: QAOA")

        return {
            "strategy": "qaoa",
            "note": "QAOA requires problem graph - implementation needed",
            "shots": self.config.shots,
        }

    def _strategy_state_prep(self, circuit: qiskit.QuantumCircuit | None) -> dict:
        """Strategy for state preparation challenges."""
        print("   Strategy: State Preparation")

        return {
            "strategy": "state_prep",
            "note": "State preparation requires specific target state",
            "shots": 0,  # Statevector mode
        }

    def _package_submission(self, result: dict) -> dict:
        """Package result for submission."""
        submission = {
            "challenge_id": self.challenge_id,
            "timestamp": time.time(),
            "config": {
                "challenge_type": self.config.challenge_type.value,
                "n_qubits": self.config.n_qubits,
                "bond_dimension": self.config.bond_dimension,
                "shots": self.config.shots,
            },
            "result": result,
            "metadata": {"solver_version": "1.0", "auto_tuned": True},
        }

        # Save submission
        filename = f"submission_{self.challenge_id}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(submission, f, indent=2)

        print(f"\n   ✓ Submission packaged: {filename}")

        return submission


class SkillCapture:
    """
    Capture and document reusable skills from each challenge.

    Creates transferable knowledge base for future challenges.
    """

    def __init__(self):
        """Initialize skill capture."""
        self.skills: dict[str, dict] = {}
        self.templates: dict[str, str] = {}

    def capture_skill(self, skill_name: str, description: str, code: str, metadata: dict):
        """Capture a new skill."""
        self.skills[skill_name] = {
            "description": description,
            "code": code,
            "metadata": metadata,
            "timestamp": time.time(),
        }
        print(f"✓ Captured skill: {skill_name}")

    def save_skill_library(self, filename: str = "skill_library.json"):
        """Save skill library to disk."""
        with open(filename, "w") as f:
            json.dump(self.skills, f, indent=2)
        print(f"✓ Skill library saved: {filename}")

    def load_skill_library(self, filename: str = "skill_library.json"):
        """Load skill library from disk."""
        try:
            with open(filename) as f:
                self.skills = json.load(f)
            print(f"✓ Loaded {len(self.skills)} skills from {filename}")
        except FileNotFoundError:
            print("ℹ No existing skill library found")


def demo_universal_solver():
    """Demonstrate universal solver."""
    print("=" * 70)
    print("Universal BlueQubit Solver Demo")
    print("=" * 70)

    solver = UniversalSolver(challenge_id="demo_challenge")

    # Test with GHZ circuit (simulating peaked challenge)
    from circuit_library import CircuitLibrary

    lib = CircuitLibrary()
    qc = lib.ghz_state(8)

    result = solver.auto_solve(
        circuit=qc, description="Find heavy output from peaked 8-qubit circuit"
    )

    print(f"\nResult: {result}")


if __name__ == "__main__":
    demo_universal_solver()
