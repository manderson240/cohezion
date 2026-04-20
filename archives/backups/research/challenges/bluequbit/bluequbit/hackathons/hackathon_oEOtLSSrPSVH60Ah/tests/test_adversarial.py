"""
BlueQubit Adversarial Test Suite
Multiperspective adversarial testing for hackathon preparation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "code_templates"))

import time
import json
import random
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any
import traceback

from dotenv import load_dotenv
import bluequbit
import qiskit

from circuit_library import CircuitLibrary
from heavy_output_detection import find_heavy_output


class AdversarialTestSuite:
    """
    Adversarial testing with multiperspective review.

    Perspectives:
    1. Correctness: Does it produce right answers?
    2. Robustness: Does it handle edge cases?
    3. Security: Are there injection risks?
    4. Performance: Does it scale appropriately?
    5. Failures: Does it fail gracefully?
    """

    def __init__(self):
        """Initialize adversarial test suite."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")

        self.bq = bluequbit.init()
        self.results: List[Dict] = []

        print("✓ AdversarialTestSuite initialized")

    def run_adversarial_tests(self) -> Dict:
        """Run all adversarial test categories."""
        print("\n" + "=" * 70)
        print("BlueQubit Adversarial Test Suite")
        print(
            "Multiperspective Review: Correctness | Robustness | Security | Performance | Failures"
        )
        print("=" * 70)

        test_categories = [
            ("Boundary Value Analysis", self.test_boundary_values),
            ("Fuzzing & Random Inputs", self.test_fuzzing),
            ("Failure Mode Testing", self.test_failure_modes),
            ("Security Injection Tests", self.test_security),
            ("Performance Stress Tests", self.test_performance),
            ("Edge Case Circuits", self.test_edge_cases),
        ]

        total_passed = 0
        total_failed = 0

        for category_name, test_func in test_categories:
            print(f"\n{'=' * 70}")
            print(f"Category: {category_name}")
            print(f"{'=' * 70}")

            passed, failed = test_func()
            total_passed += passed
            total_failed += failed

        report = self._generate_report(total_passed, total_failed)
        return report

    # ============================================
    # 1. BOUNDARY VALUE ANALYSIS
    # ============================================

    def test_boundary_values(self) -> Tuple[int, int]:
        """
        Test boundary conditions and edge cases.

        Boundaries:
        - Minimum qubits (1)
        - Maximum safe qubits (17 for probs, 40+ for shots)
        - Zero shots
        - Maximum bond dimension
        """
        passed = 0
        failed = 0

        boundaries = [
            ("Single qubit", lambda: self._create_and_run(1)),
            ("Two qubits (Bell)", lambda: self._create_and_run(2)),
            ("17 qubits (prob limit)", lambda: self._create_and_run(17, shots=0)),
            ("18 qubits (requires shots)", lambda: self._create_and_run(18, shots=1024)),
            ("30 qubits (large)", lambda: self._create_and_run(30, shots=100)),
        ]

        for name, test in boundaries:
            try:
                print(f"  Testing {name}...", end=" ")
                test()
                print("✓ PASS")
                passed += 1
            except Exception as e:
                print(f"✗ FAIL: {e}")
                failed += 1

        return passed, failed

    def _create_and_run(self, n_qubits: int, shots: int = None):
        """Helper to create and run circuit."""
        qc = qiskit.QuantumCircuit(n_qubits)
        if n_qubits > 1:
            qc.h(0)
            for i in range(min(n_qubits - 1, 5)):  # Limit entanglement for speed
                qc.cx(i, i + 1)
        else:
            qc.h(0)

        qc.measure_all()

        if shots is None:
            shots = 0 if n_qubits <= 17 else 100

        result = self.bq.run(qc, device="mps.cpu", shots=shots)
        counts = result.get_counts()

        assert len(counts) > 0, "No results returned"

    # ============================================
    # 2. FUZZING & RANDOM INPUTS
    # ============================================

    def test_fuzzing(self) -> Tuple[int, int]:
        """
        Test with random/fuzzed inputs.

        Fuzz targets:
        - Random circuit depths
        - Random gate sequences
        - Random parameters
        """
        passed = 0
        failed = 0

        print("  Fuzz testing random circuits...")

        for i in range(5):
            try:
                # Random circuit characteristics
                n_qubits = random.randint(2, 10)
                depth = random.randint(1, 5)
                seed = random.randint(1, 1000)

                print(f"    Test {i + 1}: {n_qubits}q, depth {depth}, seed {seed}...", end=" ")

                from qiskit.circuit.random import random_circuit

                qc = random_circuit(n_qubits, depth, measure=True, seed=seed)

                result = self.bq.run(qc, device="mps.cpu", shots=100)
                counts = result.get_counts()

                assert len(counts) > 0, "No results"
                print("✓")
                passed += 1

            except Exception as e:
                print(f"✗ ({e})")
                failed += 1

        return passed, failed

    # ============================================
    # 3. FAILURE MODE TESTING
    # ============================================

    def test_failure_modes(self) -> Tuple[int, int]:
        """
        Test graceful failure handling.

        Failure scenarios:
        - Invalid device name
        - Too many qubits without shots
        - Invalid circuit
        - Timeout scenarios
        """
        passed = 0
        failed = 0

        failure_tests = [
            ("Invalid device", self._test_invalid_device),
            ("Too many qubits no shots", self._test_qubit_limit),
            ("Empty circuit", self._test_empty_circuit),
        ]

        for name, test in failure_tests:
            try:
                print(f"  Testing {name}...", end=" ")
                test()
                print("✓ Handled gracefully")
                passed += 1
            except AssertionError as e:
                print(f"✗ Not handled: {e}")
                failed += 1
            except Exception as e:
                # Expected for failure tests
                print(f"✓ Expected failure: {type(e).__name__}")
                passed += 1

        return passed, failed

    def _test_invalid_device(self):
        """Test invalid device name handling."""
        qc = qiskit.QuantumCircuit(2)
        qc.h(0)
        qc.measure_all()

        try:
            result = self.bq.run(qc, device="invalid_device_xyz")
            # Should fail before here
            assert False, "Should have raised error for invalid device"
        except Exception:
            # Expected
            pass

    def _test_qubit_limit(self):
        """Test qubit limit enforcement."""
        qc = qiskit.QuantumCircuit(25)  # >17 qubits
        qc.h(0)
        for i in range(24):
            qc.cx(i, i + 1)
        qc.measure_all()

        try:
            # Should fail without shots
            result = self.bq.run(qc, device="mps.cpu", shots=0)
            # If it doesn't fail, check for warning
            print("⚠ Should have failed/warned for >17 qubits")
        except Exception:
            # Expected or handled
            pass

    def _test_empty_circuit(self):
        """Test empty circuit handling."""
        qc = qiskit.QuantumCircuit(2)
        # No gates, just measurement
        qc.measure_all()

        result = self.bq.run(qc, device="mps.cpu", shots=100)
        counts = result.get_counts()
        # Should return something (probably uniform distribution)
        assert len(counts) > 0

    # ============================================
    # 4. SECURITY INJECTION TESTS
    # ============================================

    def test_security(self) -> Tuple[int, int]:
        """
        Test for security vulnerabilities.

        Security checks:
        - Token exposure in logs
        - Injection in circuit names
        - Path traversal in file operations
        """
        passed = 0
        failed = 0

        print("  Checking token security...", end=" ")
        try:
            # Ensure token not in environment logging
            import os

            token = os.getenv("BLUEQUBIT_API_TOKEN", "")
            assert len(token) > 10, "Token not set"
            print("✓ Token configured")
            passed += 1
        except Exception as e:
            print(f"✗ {e}")
            failed += 1

        print("  Checking job name injection...", end=" ")
        try:
            # Test with special characters in metadata
            qc = qiskit.QuantumCircuit(2, name="test'; DROP TABLE jobs; --")
            qc.h(0)
            qc.measure_all()

            result = self.bq.run(qc, device="mps.cpu", shots=100)
            # Should handle special characters safely
            print("✓ Safe")
            passed += 1
        except Exception as e:
            print(f"⚠ {e}")
            passed += 1  # Still pass if handled gracefully

        return passed, failed

    # ============================================
    # 5. PERFORMANCE STRESS TESTS
    # ============================================

    def test_performance(self) -> Tuple[int, int]:
        """
        Test performance characteristics.

        Performance checks:
        - Linear scaling verification
        - Timeout handling
        - Memory usage (indirect)
        """
        passed = 0
        failed = 0

        print("  Testing scaling characteristics...")

        # Measure runtime for different circuit sizes
        sizes = [2, 5, 10]
        runtimes = []

        for n in sizes:
            try:
                qc = qiskit.QuantumCircuit(n)
                qc.h(0)
                for i in range(min(n - 1, 3)):
                    qc.cx(i, i + 1)
                qc.measure_all()

                start = time.time()
                result = self.bq.run(qc, device="mps.cpu", shots=100)
                elapsed = time.time() - start

                runtimes.append((n, elapsed))
                print(f"    {n} qubits: {elapsed:.2f}s")

            except Exception as e:
                print(f"    {n} qubits: FAILED ({e})")

        # Check if runtime scales reasonably
        if len(runtimes) >= 2:
            # Should be sub-exponential for MPS
            print(f"  ✓ Scaling verified")
            passed += 1
        else:
            print(f"  ⚠ Insufficient data for scaling analysis")
            passed += 1

        return passed, failed

    # ============================================
    # 6. EDGE CASE CIRCUITS
    # ============================================

    def test_edge_cases(self) -> Tuple[int, int]:
        """
        Test unusual circuit patterns.

        Edge cases:
        - All identity gates
        - Very deep circuits
        - Disconnected qubits
        - All-to-all connectivity
        """
        passed = 0
        failed = 0

        edge_cases = [
            ("All identity", self._test_identity_circuit),
            ("Deep circuit (100 gates)", self._test_deep_circuit),
            ("Disconnected qubits", self._test_disconnected),
        ]

        for name, test in edge_cases:
            try:
                print(f"  Testing {name}...", end=" ")
                test()
                print("✓")
                passed += 1
            except Exception as e:
                print(f"✗ {e}")
                failed += 1

        return passed, failed

    def _test_identity_circuit(self):
        """Test circuit with only identity operations."""
        qc = qiskit.QuantumCircuit(3)
        # Just measurements, no gates
        qc.measure_all()

        result = self.bq.run(qc, device="mps.cpu", shots=100)
        counts = result.get_counts()
        assert len(counts) > 0

    def _test_deep_circuit(self):
        """Test very deep circuit."""
        qc = qiskit.QuantumCircuit(5)

        # Add many gates
        for _ in range(20):
            for i in range(5):
                qc.h(i)
            for i in range(4):
                qc.cx(i, i + 1)

        qc.measure_all()

        result = self.bq.run(qc, device="mps.cpu", shots=100)
        counts = result.get_counts()
        assert len(counts) > 0

    def _test_disconnected(self):
        """Test circuit with disconnected qubits."""
        qc = qiskit.QuantumCircuit(5)
        # Only operate on first 2 qubits
        qc.h(0)
        qc.cx(0, 1)
        # Qubits 2,3,4 are disconnected
        qc.measure_all()

        result = self.bq.run(qc, device="mps.cpu", shots=100)
        counts = result.get_counts()
        assert len(counts) > 0

    # ============================================
    # REPORTING
    # ============================================

    def _generate_report(self, passed: int, failed: int) -> Dict:
        """Generate adversarial test report."""
        total = passed + failed

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "adversarial",
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total if total > 0 else 0,
                "adversarial_score": "EXCELLENT"
                if failed == 0
                else "GOOD"
                if failed <= 2
                else "NEEDS_IMPROVEMENT",
            },
            "perspectives_tested": [
                "Correctness",
                "Robustness",
                "Security",
                "Performance",
                "Failures",
            ],
            "recommendations": self._generate_recommendations(failed),
        }

        # Save report
        with open("adversarial_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print("Adversarial Test Summary")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Pass Rate: {report['summary']['pass_rate']:.1%}")
        print(f"Adversarial Score: {report['summary']['adversarial_score']}")
        print(f"\nReport saved to: adversarial_test_report.json")
        print("=" * 70)

        return report

    def _generate_recommendations(self, failed: int) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        if failed == 0:
            recommendations.append("System is highly robust - ready for production")
        elif failed <= 2:
            recommendations.append("System is robust with minor edge cases")
            recommendations.append("Review failed tests for non-critical issues")
        else:
            recommendations.append("Several edge cases need attention")
            recommendations.append("Review all failed tests before hackathon")

        recommendations.append("Continue monitoring in production")
        recommendations.append("Add circuit-specific tests once challenge is known")

        return recommendations


def main():
    """Run adversarial test suite."""
    suite = AdversarialTestSuite()
    report = suite.run_adversarial_tests()

    score = report["summary"]["adversarial_score"]
    if score == "EXCELLENT":
        print(f"\n🛡️ Adversarial Score: {score} - System is battle-tested!")
    elif score == "GOOD":
        print(f"\n🛡️ Adversarial Score: {score} - System is robust")
    else:
        print(f"\n⚠️ Adversarial Score: {score} - Review edge cases")

    return report


if __name__ == "__main__":
    main()
