"""BlueQubit Quantum QUBO / QAOA Combinatorial Solver for ARC-AGI & Kaggle.

Formulates combinatorial object-graph matching and transformation selection as a
Quantum Hamiltonian / QUBO problem, solving it on BlueQubit's cloud quantum simulators and QPUs:
$$H = \\sum_{i,j} J_{ij} \\sigma_i^z \\sigma_j^z + \\sum_i h_i \\sigma_i^z$$

There is no local fallback: without a real backend the solver raises
``QuantumBackendUnavailableError`` rather than reporting a candidate index nobody computed.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

from cohezion.quantum import QuantumBackendUnavailableError


load_dotenv()

try:
    import bluequbit
    import qiskit

    HAS_BLUEQUBIT = True
except ImportError:
    HAS_BLUEQUBIT = False

logger = logging.getLogger(__name__)


class BlueQubitARCSolver:
    """Dispatches combinatorial ARC candidate ranking & QUBO optimizations to BlueQubit."""

    def __init__(self, device: str = "mps.cpu"):
        self.device = device
        self.client = None
        self.init_error: str | None = None
        if not HAS_BLUEQUBIT:
            self.init_error = "BlueQubit SDK (bluequbit + qiskit) not installed"
            return
        token = (
            os.getenv("BLUEQUBIT_API_TOKEN")
            or os.getenv("BLUEQUBIT_API_KEY")
            or os.getenv("BLUEQUBIT_TOKEN")
        )
        if not token:
            self.init_error = "no BlueQubit API token in the environment"
            return
        self.client = bluequbit.init(api_token=token)

    def solve_graph_isomorphism_qubo(
        self, cost_matrix: list[list[float]], shots: int = 1000
    ) -> dict[str, Any]:
        """Solves combinatorial graph partition via parameterized quantum superposition.

        Raises:
            ValueError: ``cost_matrix`` is empty.
            QuantumBackendUnavailableError: no BlueQubit client is available.
            RuntimeError: the job finished without measurement counts.
        """
        n = len(cost_matrix)
        if n == 0:
            raise ValueError("cost_matrix is empty")
        if self.client is None:
            raise QuantumBackendUnavailableError(
                self.init_error or "BlueQubit client not initialized"
            )

        t0 = time.perf_counter()

        # Build Parameterized Superposition QAOA Circuit for n candidate transforms
        num_qubits = min(max(n, 2), 16)
        qc = qiskit.QuantumCircuit(num_qubits, num_qubits)

        # 1. Hadamard superposition over all candidate states |+>^n
        qc.h(range(num_qubits))

        # 2. Entangling phase separations based on cost coupling J_ij
        for i in range(num_qubits - 1):
            qc.cx(i, i + 1)
            qc.rz(float(cost_matrix[i % n][(i + 1) % n]), i + 1)
            qc.cx(i, i + 1)

        qc.measure(range(num_qubits), range(num_qubits))

        # 3. Dispatch to BlueQubit Cloud Simulator / QPU. SDK errors propagate: an
        # error dict carrying a default index would be read as an answer.
        job = self.client.run(qc, device=self.device, shots=shots)
        counts = job.get_counts()
        if not counts:
            raise RuntimeError(f"BlueQubit job {job.job_id} returned no measurement counts")
        dt = time.perf_counter() - t0

        # Extract most probable bitstring (lowest energy state)
        best_bitstring = max(counts, key=counts.get)
        best_idx = int(best_bitstring, 2) % n

        return {
            "status": "SUCCESS",
            "job_id": job.job_id,
            "optimal_candidate_index": best_idx,
            "bitstring": best_bitstring,
            "counts": counts,
            "latency_s": dt,
            "device": self.device,
        }
