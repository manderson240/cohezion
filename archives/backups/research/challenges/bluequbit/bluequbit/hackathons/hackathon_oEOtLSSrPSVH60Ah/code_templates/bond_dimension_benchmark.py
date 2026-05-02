"""
BlueQubit Bond Dimension Benchmark
Find optimal MPS bond dimension for given circuit characteristics
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

import time
from dataclasses import dataclass

import bluequbit
import qiskit
from dotenv import load_dotenv


@dataclass
class BenchmarkResult:
    """Result of bond dimension benchmark."""

    bond_dim: int
    runtime: float
    fidelity_estimate: float
    shots: int
    success: bool
    error: str = None


class BondDimensionBenchmark:
    """
    Benchmark different bond dimensions to find optimal setting.

    Tests tradeoff between accuracy (higher bond dim) and speed (lower bond dim).
    """

    def __init__(self):
        """Initialize benchmark."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")
        self.bq = bluequbit.init()

        print("✓ BondDimensionBenchmark initialized")

    def benchmark_bond_dimensions(
        self,
        circuit: qiskit.QuantumCircuit,
        bond_dims: list[int] = None,
        shots: int = 10000,
        device: str = "mps.cpu",
    ) -> list[BenchmarkResult]:
        """
        Benchmark multiple bond dimensions.

        Args:
            circuit: Circuit to test
            bond_dims: List of bond dimensions to test (default: [16, 32, 64, 128, 256])
            shots: Number of shots
            device: Device to use

        Returns:
            List of BenchmarkResult
        """
        if bond_dims is None:
            # Test standard range
            bond_dims = [16, 32, 64, 128, 256]

        # Filter based on circuit size
        n_qubits = circuit.num_qubits
        if n_qubits <= 10:
            # Small circuits - don't need high bond dim
            bond_dims = [d for d in bond_dims if d <= 128]
        elif n_qubits <= 20:
            # Medium circuits
            bond_dims = [d for d in bond_dims if d <= 256]
        else:
            # Large circuits - need all
            pass

        results = []

        print(f"\n{'=' * 70}")
        print("Bond Dimension Benchmark")
        print(f"{'=' * 70}")
        print(f"Circuit: {n_qubits} qubits, depth {circuit.depth()}")
        print(f"Device: {device}, Shots: {shots}")
        print(f"Testing: {bond_dims}")
        print(f"{'=' * 70}\n")

        for bond_dim in bond_dims:
            print(f"Testing bond_dim={bond_dim}...", end=" ")

            try:
                start = time.time()

                # Run circuit
                result = self.bq.run(
                    circuit, device=device, shots=shots, options={"mps_bond_dimension": bond_dim}
                )

                counts = result.get_counts()
                runtime = time.time() - start

                # Estimate fidelity by checking if we got expected distribution
                # (for GHZ-like circuits, expect 2 peaks)
                fidelity_est = self._estimate_fidelity(counts)

                benchmark = BenchmarkResult(
                    bond_dim=bond_dim,
                    runtime=runtime,
                    fidelity_estimate=fidelity_est,
                    shots=shots,
                    success=True,
                )

                print(f"✓ {runtime:.2f}s, fidelity ~{fidelity_est:.2%}")

            except Exception as e:
                benchmark = BenchmarkResult(
                    bond_dim=bond_dim,
                    runtime=0,
                    fidelity_estimate=0,
                    shots=shots,
                    success=False,
                    error=str(e),
                )
                print(f"✗ Failed: {e}")

            results.append(benchmark)

        return results

    def _estimate_fidelity(self, counts: dict) -> float:
        """
        Estimate fidelity from measurement counts.

        For peaked circuits, fidelity is indicated by concentration
        of probability mass in few states.
        """
        total = sum(counts.values())
        if total == 0:
            return 0.0

        # Calculate concentration
        probs = [c / total for c in counts.values()]

        # Top 2 states should have significant probability
        top_2 = sorted(probs, reverse=True)[:2]
        top_2_prob = sum(top_2)

        # Normalized fidelity estimate
        fidelity = min(top_2_prob / 0.9, 1.0)  # Expect ~90%+ in top 2

        return fidelity

    def recommend_bond_dimension(
        self, results: list[BenchmarkResult], min_fidelity: float = 0.95
    ) -> tuple[int, dict]:
        """
        Recommend optimal bond dimension.

        Strategy:
        1. Find minimum bond dim achieving min_fidelity
        2. If multiple achieve fidelity, choose fastest
        3. Provide options for accuracy vs speed

        Args:
            results: Benchmark results
            min_fidelity: Minimum acceptable fidelity

        Returns:
            (recommended_dim, analysis_dict)
        """
        successful = [r for r in results if r.success]

        if not successful:
            return None, {"error": "No successful benchmarks"}

        # Filter by fidelity
        high_fidelity = [r for r in successful if r.fidelity_estimate >= min_fidelity]

        if high_fidelity:
            # Choose fastest among high fidelity
            best = min(high_fidelity, key=lambda r: r.runtime)
            recommendation = best.bond_dim
        else:
            # No high fidelity found, use highest fidelity
            best = max(successful, key=lambda r: r.fidelity_estimate)
            recommendation = best.bond_dim

        # Analysis
        analysis = {
            "recommended": recommendation,
            "min_fidelity_threshold": min_fidelity,
            "high_fidelity_count": len(high_fidelity),
            "fastest_result": min(successful, key=lambda r: r.runtime).bond_dim,
            "highest_fidelity": max(successful, key=lambda r: r.fidelity_estimate).bond_dim,
            "speed_vs_accuracy_tradeoff": "Available" if len(successful) > 1 else "Limited",
        }

        return recommendation, analysis

    def print_report(self, results: list[BenchmarkResult], recommendation: int, analysis: dict):
        """Print benchmark report."""
        print(f"\n{'=' * 70}")
        print("Bond Dimension Benchmark Report")
        print(f"{'=' * 70}")

        print(f"\n{'Bond Dim':<12} {'Runtime':<12} {'Fidelity':<12} {'Status':<10}")
        print("-" * 70)

        for r in results:
            if r.success:
                marker = " ← RECOMMENDED" if r.bond_dim == recommendation else ""
                print(
                    f"{r.bond_dim:<12} {r.runtime:<12.2f} {r.fidelity_estimate:<12.2%} {'✓':<10}{marker}"
                )
            else:
                print(f"{r.bond_dim:<12} {'N/A':<12} {'N/A':<12} {'✗':<10} ({r.error[:30]}...)")

        print(f"\n{'=' * 70}")
        print("Analysis:")
        print(f"  Recommended bond dimension: {analysis.get('recommended', 'N/A')}")
        print(f"  Fastest setting: {analysis.get('fastest_result', 'N/A')}")
        print(f"  Highest fidelity: {analysis.get('highest_fidelity', 'N/A')}")
        print(f"{'=' * 70}\n")

    def optimize_for_circuit(
        self, circuit: qiskit.QuantumCircuit, target_fidelity: float = 0.95, max_bond_dim: int = 256
    ) -> int:
        """
        One-shot optimization for a circuit.

        Args:
            circuit: Circuit to optimize for
            target_fidelity: Target fidelity threshold
            max_bond_dim: Maximum bond dimension to test

        Returns:
            Recommended bond dimension
        """
        # Adaptive bond dimension selection
        n_qubits = circuit.num_qubits
        depth = circuit.depth()

        # Estimate based on circuit complexity
        if n_qubits <= 10:
            # Small circuits: 32-64
            test_dims = [16, 32, 64]
        elif n_qubits <= 20:
            # Medium: 64-128
            test_dims = [32, 64, 128]
        elif n_qubits <= 30:
            # Large: 128-256
            test_dims = [64, 128, 256]
        else:
            # Very large: full range
            test_dims = [64, 128, 256, max_bond_dim]

        # Filter by max
        test_dims = [d for d in test_dims if d <= max_bond_dim]

        print(f"Auto-configured test for {n_qubits} qubit, depth {depth} circuit:")
        print(f"Testing bond dimensions: {test_dims}")

        results = self.benchmark_bond_dimensions(circuit, test_dims)
        recommendation, analysis = self.recommend_bond_dimension(results, target_fidelity)

        self.print_report(results, recommendation, analysis)

        return recommendation


def demo_benchmark():
    """Demonstrate bond dimension benchmarking."""
    print("=" * 70)
    print("Bond Dimension Benchmark Demo")
    print("=" * 70)

    benchmark = BondDimensionBenchmark()

    # Create GHZ circuit for testing
    qc = qiskit.QuantumCircuit(12)
    qc.h(0)
    for i in range(11):
        qc.cx(i, i + 1)
    qc.measure_all()

    # Optimize
    recommended = benchmark.optimize_for_circuit(qc, target_fidelity=0.90)

    print(f"\n✓ Recommended bond dimension: {recommended}")

    # Save recommendation for future use
    import json

    with open("bond_dim_recommendation.json", "w") as f:
        json.dump(
            {
                "circuit_type": "GHZ",
                "n_qubits": 12,
                "recommended_bond_dim": recommended,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            f,
            indent=2,
        )

    print("✓ Saved to bond_dim_recommendation.json")


if __name__ == "__main__":
    demo_benchmark()
