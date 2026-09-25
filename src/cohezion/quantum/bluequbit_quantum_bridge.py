"""BlueQubit Quantum Bridge & QPU/GPU-Simulator Dispatcher for Cohezion.

Integrates with BlueQubit (https://app.bluequbit.io/):
1. Initializes `bluequbit.init()` with an API key or cached credentials.
2. Supports Qiskit / Cirq / QASM circuit construction for:
   - ARC Graph Isomorphism QUBO / QAOA.
   - 2048D Hilbert Space Quantum State Kernels.
   - Quantum Random State Sampling for Stochastic Beam Search.

There is no local fallback: when no real backend is available the bridge raises
``QuantumBackendUnavailableError`` rather than returning counts that were never measured.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from cohezion.quantum import QuantumBackendUnavailableError


load_dotenv()

logger = logging.getLogger(__name__)

try:
    import bluequbit

    HAS_BLUEQUBIT = True
except ImportError:
    HAS_BLUEQUBIT = False


class BlueQubitQuantumBridge:
    """Bridge for dispatching quantum circuits to BlueQubit GPU simulators and QPUs."""

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.getenv("BLUEQUBIT_API_KEY")
        self.client = None
        self.init_error: str | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not HAS_BLUEQUBIT:
            self.init_error = "BlueQubit SDK not installed"
            logger.warning(self.init_error)
            return

        try:
            if self.api_token:
                self.client = bluequbit.init(api_token=self.api_token)
                logger.info("Initialized BlueQubit client with API token.")
            else:
                self.client = bluequbit.init()
                logger.info("Initialized BlueQubit client with default/cached credentials.")
        except Exception as e:
            self.init_error = f"BlueQubit init failed: {e}"
            logger.warning(self.init_error)

    def run_quantum_kernel(self, num_qubits: int = 4, device: str = "gpu") -> dict[str, Any]:
        """Run a GHZ (superposition + entanglement) circuit and return measured counts.

        Raises:
            QuantumBackendUnavailableError: no BlueQubit client is available.
            RuntimeError: the job finished without measurement counts.
        """
        if not HAS_BLUEQUBIT or self.client is None:
            raise QuantumBackendUnavailableError(
                self.init_error or "BlueQubit client not initialized"
            )

        qasm_circuit = f"""OPENQASM 2.0;
include "qelib1.inc";
qreg q[{num_qubits}];
creg c[{num_qubits}];
h q[0];
"""
        for i in range(num_qubits - 1):
            qasm_circuit += f"cx q[{i}], q[{i + 1}];\n"
        qasm_circuit += "measure q -> c;\n"

        # SDK errors propagate: an error dict would be one more result to misread.
        result = self.client.run(qasm_circuit, device=device, shots=1000)
        # JobResult exposes get_counts(); it has no `counts` attribute.
        counts = result.get_counts()
        if not counts:
            raise RuntimeError(f"BlueQubit job {result.job_id} returned no measurement counts")
        return {
            "status": "SUCCESS",
            "job_id": result.job_id,
            "counts": counts,
            "device": device,
        }
