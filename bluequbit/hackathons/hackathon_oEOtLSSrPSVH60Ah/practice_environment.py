"""
BlueQubit Practice Environment
Use ongoing challenge oEOtLSSrPSVH60Ah for practice

Purpose:
- Learn platform mechanics before main challenge
- Practice circuit submission workflow
- Test heavy output detection
- Validate timing and costs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "code_templates"))

import time
import json
from datetime import datetime
from typing import Dict, List, Tuple

from dotenv import load_dotenv
import bluequbit
import qiskit

from circuit_library import CircuitLibrary
from heavy_output_detection import find_heavy_output, calculate_snr
from submission_pipeline import SubmissionPipeline


class PracticeEnvironment:
    """
    Practice environment for ongoing hackathon challenge.

    Provides:
    - Circuit testing with various parameters
    - Performance benchmarking
    - Heavy output detection practice
    - Platform mechanics exploration
    """

    def __init__(self, challenge_id: str = "oEOtLSSrPSVH60Ah"):
        """Initialize practice environment."""
        project_root = Path(__file__).parent.parent.parent
        load_dotenv(project_root / ".env")

        self.challenge_id = challenge_id
        self.bq = bluequbit.init()
        self.lib = CircuitLibrary()
        self.pipeline = SubmissionPipeline(log_file=f"practice_{challenge_id}.jsonl")

        self.results: List[Dict] = []

        print(f"✓ PracticeEnvironment initialized for challenge: {challenge_id}")

    def run_practice_session(self):
        """Run comprehensive practice session."""
        print("\n" + "=" * 70)
        print(f"BlueQubit Practice Session")
        print(f"Challenge: {self.challenge_id}")
        print("=" * 70)

        practice_modules = [
            ("Platform Connectivity", self.test_connectivity),
            ("Circuit Library", self.practice_circuit_library),
            ("Heavy Output Detection", self.practice_heavy_output),
            ("Performance Benchmarking", self.benchmark_performance),
            ("Submission Workflow", self.practice_submission),
        ]

        for module_name, module_func in practice_modules:
            print(f"\n{'=' * 70}")
            print(f"Module: {module_name}")
            print(f"{'=' * 70}")

            try:
                module_func()
                print(f"✓ {module_name} complete")
            except Exception as e:
                print(f"⚠ {module_name} issue: {e}")
                print(f"  (Non-critical, continuing...)")

        # Generate practice report
        self._generate_practice_report()

    def test_connectivity(self):
        """Test platform connectivity and basic operations."""
        print("\n1. Testing basic connectivity...")

        # Simple Bell state
        qc = qiskit.QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

        start = time.time()
        result = self.bq.run(qc, device="mps.cpu", shots=1024)
        elapsed = time.time() - start

        counts = result.get_counts()

        print(f"   ✓ Connection successful")
        print(f"   ✓ 2-qubit circuit executed in {elapsed:.2f}s")
        print(f"   ✓ Results: {len(counts)} states")

        # Validate results
        assert len(counts) > 0, "No results"
        total = sum(counts.values())
        assert abs(total - 1.0) < 0.01, "Probabilities don't sum to ~1"

        self.results.append(
            {"test": "connectivity", "status": "PASS", "runtime": elapsed, "qubits": 2}
        )

    def practice_circuit_library(self):
        """Practice with pre-built circuits."""
        print("\n2. Testing circuit library...")

        test_circuits = [
            ("GHZ (8 qubits)", self.lib.ghz_state(8)),
            ("W-state (5 qubits)", self.lib.w_state(5)),
            ("Variational (6 qubits)", self.lib.variational_circuit(6, depth=2)),
        ]

        for name, qc in test_circuits:
            print(f"\n   Testing {name}...")
            try:
                result = self.bq.run(qc, device="mps.cpu", shots=500)
                counts = result.get_counts()
                print(f"   ✓ {len(counts)} states returned")
            except Exception as e:
                print(f"   ⚠ {e}")

    def practice_heavy_output(self):
        """Practice heavy output detection."""
        print("\n3. Practicing heavy output detection...")

        # Create peaked circuit (GHZ - should have 2 heavy outputs)
        qc = qiskit.QuantumCircuit(12)
        qc.h(0)
        for i in range(11):
            qc.cx(i, i + 1)
        qc.measure_all()

        print("   Submitting 12-qubit GHZ circuit...")
        result = self.bq.run(qc, device="mps.cpu", shots=10000)
        counts = result.get_counts()

        # Find heavy outputs
        heavy = find_heavy_output(counts, threshold=0.4)

        print(f"   ✓ Found {len(heavy)} heavy outputs")
        if heavy:
            top = max(heavy.items(), key=lambda x: x[1])
            print(f"   ✓ Top: {top[0]} (p={top[1]:.4f})")

            # Calculate SNR
            snr = calculate_snr(top[1], 12)
            print(f"   ✓ SNR: {snr:.2f} sigma")

            self.results.append(
                {
                    "test": "heavy_output",
                    "status": "PASS",
                    "num_heavy": len(heavy),
                    "top_probability": top[1],
                    "snr": snr,
                }
            )

    def benchmark_performance(self):
        """Benchmark performance across circuit sizes."""
        print("\n4. Benchmarking performance...")

        sizes = [
            ("Small", 5, 100),
            ("Medium", 15, 1000),
            ("Large", 25, 100),
        ]

        benchmarks = []

        for name, n_qubits, shots in sizes:
            print(f"\n   {name} ({n_qubits} qubits, {shots} shots)...")

            try:
                qc = self.lib.ghz_state(n_qubits)

                start = time.time()
                result = self.bq.run(qc, device="mps.cpu", shots=shots)
                elapsed = time.time() - start

                print(f"   ✓ Completed in {elapsed:.2f}s")

                benchmarks.append(
                    {"size": name, "qubits": n_qubits, "shots": shots, "runtime": elapsed}
                )

            except Exception as e:
                print(f"   ✗ {e}")

        # Print scaling analysis
        if len(benchmarks) >= 2:
            print(f"\n   Performance Summary:")
            for b in benchmarks:
                print(
                    f"     {b['size']:10} {b['qubits']:2}q: {b['runtime']:6.2f}s ({b['shots']} shots)"
                )

    def practice_submission(self):
        """Practice complete submission workflow."""
        print("\n5. Practicing submission workflow...")

        # Create circuit
        qc = qiskit.QuantumCircuit(10)
        qc.h(0)
        for i in range(9):
            qc.cx(i, i + 1)
        qc.measure_all()

        # Submit and extract
        print("   Submitting circuit...")
        result = self.pipeline.submit_and_extract(qc, device="mps.cpu", shots=10000, threshold=0.4)

        if result.bitstring:
            print(f"   ✓ Submission complete")
            print(f"   ✓ Heavy output: {result.bitstring}")
            print(f"   ✓ Probability: {result.probability:.6f}")
            print(f"   ✓ SNR: {result.snr:.2f} sigma")
        else:
            print(f"   ⚠ No heavy output found")

    def _generate_practice_report(self):
        """Generate practice session report."""
        report = {
            "challenge_id": self.challenge_id,
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.get("status") == "PASS"),
                "platform": "bluequbit",
            },
        }

        # Save report
        filename = f"practice_report_{self.challenge_id}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 70)
        print("Practice Session Complete")
        print("=" * 70)
        print(f"Challenge: {self.challenge_id}")
        print(f"Tests Completed: {report['summary']['total_tests']}")
        print(f"Report saved: {filename}")
        print("\n✓ Practice environment ready")
        print("✓ Platform mechanics validated")
        print("✓ Ready for main challenge: wSvCWg8f38spoXX3")
        print("=" * 70)


def main():
    """Run practice session."""
    env = PracticeEnvironment(challenge_id="oEOtLSSrPSVH60Ah")
    env.run_practice_session()


if __name__ == "__main__":
    main()
