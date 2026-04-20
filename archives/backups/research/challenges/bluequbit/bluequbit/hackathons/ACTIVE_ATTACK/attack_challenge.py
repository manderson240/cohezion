"""
Active Attack on BlueQubit Challenge oEOtLSSrPSVH60Ah
Execute winning strategy on ongoing challenge
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "UNIVERSAL_SOLVER"))

import time
import json
from datetime import datetime

from dotenv import load_dotenv
import bluequbit
import qiskit

# Import our winning tools
from universal_solver import UniversalSolver, ChallengeType
from circuit_library import CircuitLibrary
from heavy_output_detection import detect_heavy_output, calculate_snr
from submission_pipeline import SubmissionPipeline


class ChallengeAttacker:
    """
    Active attack on BlueQubit challenge.
    Execute systematic winning strategy.
    """

    def __init__(self, challenge_id: str = "oEOtLSSrPSVH60Ah"):
        """Initialize attacker."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")

        self.challenge_id = challenge_id
        self.bq = bluequbit.init()
        self.solver = UniversalSolver(challenge_id=challenge_id)
        self.pipeline = SubmissionPipeline(log_file=f"attack_{challenge_id}.jsonl")

        print("=" * 70)
        print(f"🎯 CHALLENGE ATTACK INITIATED")
        print(f"Target: {challenge_id}")
        print("=" * 70)

    def execute_attack(self):
        """Execute full attack sequence."""
        # Phase 1: Reconnaissance
        circuit = self._reconnaissance()

        if circuit is None:
            print("\n❌ Could not obtain circuit. Attack failed.")
            return None

        # Phase 2: Analyze
        challenge_type = self._analyze_challenge(circuit)

        # Phase 3: Execute winning strategy
        result = self._execute_winning_strategy(circuit, challenge_type)

        # Phase 4: Submit
        submission = self._submit_result(result)

        return submission

    def _reconnaissance(self):
        """Reconnaissance - get the circuit."""
        print("\n🔍 PHASE 1: RECONNAISSANCE")
        print("-" * 70)

        # Try to get peaked circuit
        print("Attempting to get challenge circuit...")

        for difficulty in [1, 5, 10, 15, 20]:
            try:
                print(f"  Trying difficulty {difficulty}...", end=" ")
                circuit = self.bq.get_peaked_circuit(difficulty)
                print(f"✓ SUCCESS!")
                print(f"  Qubits: {circuit.num_qubits}")
                print(f"  Depth: {circuit.depth()}")
                return circuit
            except Exception as e:
                print(f"✗ {type(e).__name__}")
                continue

        # If get_peaked_circuit fails, try other methods
        print("\n⚠️ get_peaked_circuit failed, trying alternatives...")

        # Try searching for challenge-specific jobs
        try:
            jobs = self.bq.search()
            if jobs:
                print(f"  Found {len(jobs)} recent jobs")
                print(f"  Latest: {jobs[0].get('job_id', 'N/A')}")
        except Exception as e:
            print(f"  Search failed: {e}")

        return None

    def _analyze_challenge(self, circuit):
        """Analyze challenge type."""
        print("\n📊 PHASE 2: ANALYSIS")
        print("-" * 70)

        n_qubits = circuit.num_qubits
        depth = circuit.depth()

        print(f"Circuit Analysis:")
        print(f"  Qubits: {n_qubits}")
        print(f"  Depth: {depth}")
        print(f"  Gates: {len(circuit.data)}")

        # Classify
        if depth > 50:
            challenge_type = ChallengeType.VQA_OPTIMIZATION
        elif n_qubits <= 40:
            challenge_type = ChallengeType.PEAKED_HEAVY_OUTPUT
        else:
            challenge_type = ChallengeType.UNKNOWN

        print(f"  Detected Type: {challenge_type.value}")

        return challenge_type

    def _execute_winning_strategy(self, circuit, challenge_type):
        """Execute winning strategy based on type."""
        print("\n⚔️  PHASE 3: EXECUTE STRATEGY")
        print("-" * 70)

        if challenge_type == ChallengeType.PEAKED_HEAVY_OUTPUT:
            return self._strategy_heavy_output(circuit)
        elif challenge_type == ChallengeType.VQA_OPTIMIZATION:
            return self._strategy_vqa(circuit)
        else:
            # Default to heavy output (safest)
            print("  Defaulting to heavy output strategy")
            return self._strategy_heavy_output(circuit)

    def _strategy_heavy_output(self, circuit):
        """Heavy output detection strategy (proven winner)."""
        print("\n  Strategy: Heavy Output Detection")
        print("  (Based on Little Dimple success)")

        n_qubits = circuit.num_qubits

        # Determine parameters
        if n_qubits <= 10:
            bond_dim = 64
        elif n_qubits <= 20:
            bond_dim = 128
        elif n_qubits <= 30:
            bond_dim = 256
        else:
            bond_dim = 512

        shots = 100000  # High for statistics

        print(f"  Parameters:")
        print(f"    Bond dimension: {bond_dim}")
        print(f"    Shots: {shots}")
        print(f"    Threshold: 0.5")

        # Execute
        print(f"\n  Submitting circuit...")
        start = time.time()

        result = self.bq.run(
            circuit, device="mps.cpu", shots=shots, options={"mps_bond_dimension": bond_dim}
        )

        elapsed = time.time() - start
        counts = result.get_counts()

        print(f"  ✓ Completed in {elapsed:.2f}s")
        print(f"  ✓ {len(counts)} distinct states")

        # Find heavy outputs
        print(f"\n  Analyzing results...")
        heavy = detect_heavy_output(counts, threshold=0.5)

        if not heavy:
            print("  ⚠️ No heavy outputs found")
            return None

        # Get top
        top_bitstring = max(heavy.items(), key=lambda x: x[1])
        snr = calculate_snr(top_bitstring[1], n_qubits)

        print(f"  ✓ Heavy outputs found: {len(heavy)}")
        print(f"  ✓ Top: {top_bitstring[0]} (p={top_bitstring[1]:.6f})")
        print(f"  ✓ SNR: {snr:.2f} sigma")

        return {
            "strategy": "heavy_output",
            "bitstring": top_bitstring[0],
            "probability": top_bitstring[1],
            "snr": snr,
            "num_heavy": len(heavy),
            "runtime": elapsed,
            "bond_dim": bond_dim,
            "shots": shots,
        }

    def _strategy_vqa(self, circuit):
        """VQA optimization strategy."""
        print("\n  Strategy: VQA Optimization")
        print("  (Place holder - VQA requires classical optimizer)")

        return {"strategy": "vqa", "note": "VQA implementation requires Pennylane + optimizer"}

    def _submit_result(self, result):
        """Package and submit result."""
        print("\n📤 PHASE 4: SUBMISSION")
        print("-" * 70)

        if result is None:
            print("❌ No result to submit")
            return None

        # Package
        submission = {
            "challenge_id": self.challenge_id,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "metadata": {
                "solver": "UniversalSolver v1.0",
                "auto_tuned": True,
                "strategy": result.get("strategy"),
            },
        }

        # Save
        filename = f"submission_{self.challenge_id}_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(submission, f, indent=2)

        print(f"✓ Submission packaged: {filename}")
        print(f"✓ Ready for upload to BlueQubit")

        # Print submission summary
        if result.get("bitstring"):
            print(f"\n🏆 SUBMISSION READY:")
            print(f"  Bitstring: {result['bitstring']}")
            print(f"  Probability: {result['probability']:.6f}")
            print(f"  SNR: {result['snr']:.2f} sigma")
            print(f"  Runtime: {result['runtime']:.2f}s")

        return submission


def main():
    """Execute attack."""
    attacker = ChallengeAttacker(challenge_id="oEOtLSSrPSVH60Ah")
    result = attacker.execute_attack()

    if result:
        print("\n" + "=" * 70)
        print("🎉 ATTACK COMPLETE - SUBMISSION READY")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠️  ATTACK INCOMPLETE - REVIEW REQUIRED")
        print("=" * 70)

    return result


if __name__ == "__main__":
    main()
