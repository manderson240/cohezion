"""
QAOA Solver
Based on Tutorials 4 & 5: QAOA with BlueQubit

Quantum Approximate Optimization Algorithm for combinatorial problems.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

import time

import bluequbit
import numpy as np
from dotenv import load_dotenv
from qiskit import ParameterVector, QuantumCircuit
from scipy.optimize import minimize


class QAOASolver:
    """
    Solver for QAOA challenges (MaxCut, MIS, LABS, etc.).

    Strategy from Tutorials 4 & 5:
    1. Build QAOA circuit with parameters
    2. Use Pauli-path for fast energy evaluation
    3. Classical optimization (COBYLA/SPSA)
    4. Return optimal solution
    """

    def __init__(self, bq=None):
        """Initialize QAOA solver."""
        if bq is None:
            load_dotenv(".env")
            bq = bluequbit.init()
        self.bq = bq

        print("✓ QAOASolver initialized")

    def solve_maxcut(
        self,
        graph_edges: list[tuple[int, int]],
        n_nodes: int,
        p_layers: int = 1,
        max_iterations: int = 100,
    ) -> dict:
        """
        Solve MaxCut using QAOA.

        Args:
            graph_edges: List of edges [(u, v), ...]
            n_nodes: Number of nodes/qubits
            p_layers: Number of QAOA layers
            max_iterations: Max optimization iterations

        Returns:
            dict with optimal parameters and solution
        """
        print(f"\n{'=' * 70}")
        print("QAOA for MaxCut")
        print(f"{'=' * 70}")
        print(f"Nodes: {n_nodes}")
        print(f"Edges: {len(graph_edges)}")
        print(f"QAOA layers (p): {p_layers}")

        # Build QAOA circuit
        qc = self._build_qaoa_circuit(n_nodes, p_layers, graph_edges)

        # Build cost Hamiltonian
        hamiltonian = self._maxcut_hamiltonian(graph_edges, n_nodes)

        # Optimize
        result = self._optimize_qaoa(qc, hamiltonian, p_layers, max_iterations)

        return result

    def solve_mis(
        self,
        graph_edges: list[tuple[int, int]],
        n_nodes: int,
        penalty: float = 7.0,
        p_layers: int = 1,
    ) -> dict:
        """
        Solve Maximum Independent Set using QAOA.

        Args:
            graph_edges: List of edges
            n_nodes: Number of nodes
            penalty: Penalty parameter (must be large enough)
            p_layers: Number of QAOA layers

        Returns:
            dict with solution
        """
        print(f"\n{'=' * 70}")
        print("QAOA for MIS")
        print(f"{'=' * 70}")

        # Build Hamiltonian (from Tutorial 4)
        terms = []

        # Single-qubit Z terms: hᵢ = -1/2 + (A/4)·deg(i)
        from collections import defaultdict

        degree = defaultdict(int)
        for u, v in graph_edges:
            degree[u] += 1
            degree[v] += 1

        for v in range(n_nodes):
            coeff = 0.5 - (penalty / 4) * degree[v]
            # Convert to Pauli string
            pauli = ["I"] * n_nodes
            pauli[v] = "Z"
            terms.append(("".join(pauli), coeff))

        # ZZ coupling terms for edges: Jᵢ� = A/4
        for u, v in graph_edges:
            pauli = ["I"] * n_nodes
            pauli[u] = "Z"
            pauli[v] = "Z"
            terms.append(("".join(pauli), penalty / 4))

        # Build and optimize
        qc = self._build_qaoa_circuit(n_nodes, p_layers, graph_edges)
        result = self._optimize_qaoa(qc, terms, p_layers)

        return result

    def _build_qaoa_circuit(
        self, n_qubits: int, p_layers: int, graph_edges: list[tuple[int, int]]
    ) -> QuantumCircuit:
        """Build parameterized QAOA circuit."""
        gammas = ParameterVector("γ", p_layers)
        betas = ParameterVector("β", p_layers)

        qc = QuantumCircuit(n_qubits)

        # Initial superposition
        qc.h(range(n_qubits))

        # QAOA layers
        for p in range(p_layers):
            # Cost Hamiltonian
            for u, v in graph_edges:
                qc.cx(u, v)
                qc.rz(2 * gammas[p], v)
                qc.cx(u, v)

            # Mixer Hamiltonian
            for i in range(n_qubits):
                qc.rx(2 * betas[p], i)

        return qc

    def _maxcut_hamiltonian(
        self, edges: list[tuple[int, int]], n_nodes: int
    ) -> list[tuple[str, float]]:
        """Build MaxCut Hamiltonian."""
        terms = []

        # For each edge: 0.5 * (I - Z_u Z_v)
        for u, v in edges:
            pauli = ["I"] * n_nodes
            pauli[u] = "Z"
            pauli[v] = "Z"
            terms.append(("".join(pauli), -0.5))
            terms.append(("I" * n_nodes, 0.5))

        return terms

    def _optimize_qaoa(
        self,
        circuit: QuantumCircuit,
        hamiltonian: list[tuple[str, float]],
        p_layers: int,
        max_iterations: int = 100,
    ) -> dict:
        """Optimize QAOA parameters."""
        start = time.time()

        # Initial parameters (random)
        initial_params = np.random.random(2 * p_layers) * 2 * np.pi

        # Cost function using Pauli-path (fast!)
        def cost(params):
            # Bind parameters
            param_dict = {circuit.parameters[i]: params[i] for i in range(len(params))}
            bound_circuit = circuit.assign_parameters(param_dict)

            # Compute energy
            options = {"pauli_path_truncation_threshold": 8e-4}
            result = self.bq.run(
                bound_circuit, device="pauli-path", pauli_sum=hamiltonian, options=options
            )

            return result.expectation_value

        print(f"Optimizing {2 * p_layers} parameters...")

        # Optimize
        result = minimize(
            cost, initial_params, method="COBYLA", options={"maxiter": max_iterations, "disp": True}
        )

        elapsed = time.time() - start

        optimal_gamma = result.x[:p_layers]
        optimal_beta = result.x[p_layers:]

        print(f"✓ Optimization complete in {elapsed:.2f}s")
        print(f"  Optimal energy: {result.fun:.6f}")
        print(f"  Gamma: {optimal_gamma}")
        print(f"  Beta: {optimal_beta}")

        return {
            "optimal_energy": result.fun,
            "optimal_gamma": optimal_gamma,
            "optimal_beta": optimal_beta,
            "optimal_params": result.x,
            "success": result.success,
            "runtime": elapsed,
        }


def demo():
    """Demonstrate QAOA solver."""
    print("=" * 70)
    print("QAOA Solver Demo")
    print("=" * 70)

    solver = QAOASolver()

    # Create simple graph (triangle)
    edges = [(0, 1), (1, 2), (2, 0)]
    n_nodes = 3

    # Solve MaxCut
    result = solver.solve_maxcut(edges, n_nodes, p_layers=1)

    print(f"\n{'=' * 70}")
    print("Final Result:")
    print(f"{'=' * 70}")
    print(f"Optimal energy: {result['optimal_energy']:.6f}")
    print(f"Parameters: {result['optimal_params']}")
    print(f"Success: {result['success']}")

    return result


if __name__ == "__main__":
    demo()
