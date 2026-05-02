"""
BlueQubit Circuit Library
Pre-built circuits for common quantum algorithms
"""


import numpy as np
import qiskit
from qiskit.circuit.random import random_circuit


class CircuitLibrary:
    """Collection of pre-built quantum circuits."""

    @staticmethod
    def ghz_state(n_qubits: int) -> qiskit.QuantumCircuit:
        """
        Create GHZ (Greenberger-Horne-Zeilinger) state.

        |GHZ⟩ = (|00...0⟩ + |11...1⟩) / √2

        Args:
            n_qubits: Number of qubits

        Returns:
            QuantumCircuit with measurement
        """
        qc = qiskit.QuantumCircuit(n_qubits)
        qc.h(0)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
        qc.measure_all()
        return qc

    @staticmethod
    def w_state(n_qubits: int) -> qiskit.QuantumCircuit:
        """
        Create W state.

        |W⟩ = (|100...0⟩ + |010...0⟩ + ... + |00...01⟩) / √n

        Args:
            n_qubits: Number of qubits

        Returns:
            QuantumCircuit with measurement
        """
        qc = qiskit.QuantumCircuit(n_qubits)

        # Create W state
        qc.ry(2 * np.arccos(1 / np.sqrt(n_qubits)), 0)

        for i in range(1, n_qubits):
            qc.cry(2 * np.arccos(1 / np.sqrt(n_qubits - i)), i - 1, i)

        for i in range(n_qubits - 1):
            qc.cx(n_qubits - 2 - i, n_qubits - 1 - i)

        qc.measure_all()
        return qc

    @staticmethod
    def qft(n_qubits: int) -> qiskit.QuantumCircuit:
        """
        Create Quantum Fourier Transform circuit.

        Args:
            n_qubits: Number of qubits

        Returns:
            QuantumCircuit with measurement
        """
        qc = qiskit.QuantumCircuit(n_qubits)

        for j in range(n_qubits):
            qc.h(j)
            for k in range(j + 1, n_qubits):
                angle = np.pi / (2 ** (k - j))
                qc.cp(angle, k, j)

        # Reverse order
        for i in range(n_qubits // 2):
            qc.swap(i, n_qubits - 1 - i)

        qc.measure_all()
        return qc

    @staticmethod
    def bernstein_vazirani(n_qubits: int, secret_string: str) -> qiskit.QuantumCircuit:
        """
        Bernstein-Vazirani algorithm.

        Args:
            n_qubits: Number of qubits
            secret_string: Secret binary string to find

        Returns:
            QuantumCircuit with measurement
        """
        # Create circuit with quantum and classical registers
        qr = qiskit.QuantumRegister(n_qubits + 1, "q")
        cr = qiskit.ClassicalRegister(n_qubits, "c")
        qc = qiskit.QuantumCircuit(qr, cr)

        # Initialize
        qc.h(range(n_qubits))
        qc.x(n_qubits)
        qc.h(n_qubits)

        # Oracle
        for i, bit in enumerate(reversed(secret_string)):
            if bit == "1":
                qc.cx(i, n_qubits)

        # Final Hadamards
        qc.h(range(n_qubits))
        qc.measure(qr[:n_qubits], cr)

        return qc

    @staticmethod
    def grover_diffusion(n_qubits: int, iterations: int = 1) -> qiskit.QuantumCircuit:
        """
        Grover's diffusion operator.

        Args:
            n_qubits: Number of qubits
            iterations: Number of Grover iterations

        Returns:
            QuantumCircuit with measurement
        """
        qc = qiskit.QuantumCircuit(n_qubits)

        # Initialize superposition
        qc.h(range(n_qubits))

        for _ in range(iterations):
            # Oracle (marking |11...1⟩)
            qc.h(n_qubits - 1)
            qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
            qc.h(n_qubits - 1)

            # Diffusion
            qc.h(range(n_qubits))
            qc.x(range(n_qubits))
            qc.h(n_qubits - 1)
            qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
            qc.h(n_qubits - 1)
            qc.x(range(n_qubits))
            qc.h(range(n_qubits))

        qc.measure_all()
        return qc

    @staticmethod
    def variational_circuit(
        n_qubits: int, depth: int, params: list[float] | None = None
    ) -> qiskit.QuantumCircuit:
        """
        Hardware-efficient variational circuit.

        Args:
            n_qubits: Number of qubits
            depth: Circuit depth (layers)
            params: Variational parameters (optional)

        Returns:
            QuantumCircuit
        """
        qc = qiskit.QuantumCircuit(n_qubits)

        if params is None:
            params = np.random.random(2 * n_qubits * depth) * 2 * np.pi

        param_idx = 0
        for d in range(depth):
            # Rotation layer
            for i in range(n_qubits):
                qc.rx(params[param_idx], i)
                param_idx += 1
                qc.rz(params[param_idx], i)
                param_idx += 1

            # Entanglement layer
            for i in range(0, n_qubits - 1, 2):
                qc.cx(i, i + 1)
            for i in range(1, n_qubits - 1, 2):
                qc.cx(i, i + 1)

        qc.measure_all()
        return qc

    @staticmethod
    def random_circuit_custom(n_qubits: int, depth: int, seed: int = 42) -> qiskit.QuantumCircuit:
        """
        Create random circuit.

        Args:
            n_qubits: Number of qubits
            depth: Circuit depth
            seed: Random seed

        Returns:
            QuantumCircuit with measurement
        """
        qc = random_circuit(n_qubits, depth, measure=True, seed=seed)
        return qc

    @staticmethod
    def qaoa_mixer(
        n_qubits: int, edges: list[tuple[int, int]], gamma: float, beta: float
    ) -> qiskit.QuantumCircuit:
        """
        QAOA circuit for MaxCut.

        Args:
            n_qubits: Number of qubits
            edges: Graph edges [(u, v), ...]
            gamma: Cost Hamiltonian parameter
            beta: Mixer Hamiltonian parameter

        Returns:
            QuantumCircuit with measurement
        """
        qc = qiskit.QuantumCircuit(n_qubits)

        # Initialize
        qc.h(range(n_qubits))

        # Cost Hamiltonian
        for u, v in edges:
            qc.cx(u, v)
            qc.rz(gamma, v)
            qc.cx(u, v)

        # Mixer Hamiltonian
        for i in range(n_qubits):
            qc.rx(2 * beta, i)

        qc.measure_all()
        return qc


def test_circuit_library():
    """Test all circuits in library."""
    print("=" * 60)
    print("Testing Circuit Library")
    print("=" * 60)

    lib = CircuitLibrary()

    circuits = [
        ("GHZ State (4 qubits)", lib.ghz_state(4)),
        ("W State (3 qubits)", lib.w_state(3)),
        ("QFT (3 qubits)", lib.qft(3)),
        ("Bernstein-Vazirani (3 qubits)", lib.bernstein_vazirani(3, "101")),
        ("Grover (3 qubits)", lib.grover_diffusion(3, iterations=1)),
        ("Variational (4 qubits)", lib.variational_circuit(4, depth=2)),
        ("Random (4 qubits)", lib.random_circuit_custom(4, depth=3)),
        ("QAOA (4 qubits)", lib.qaoa_mixer(4, [(0, 1), (1, 2), (2, 3), (0, 3)], 0.5, 0.5)),
    ]

    for name, qc in circuits:
        print(f"\n{name}:")
        print(f"  Depth: {qc.depth()}")
        print(f"  Gates: {len(qc.data)}")
        print(f"  Qubits: {qc.num_qubits}")
        print("  ✓ Created successfully")

    print("\n" + "=" * 60)
    print("All circuits created successfully!")
    print("=" * 60)


if __name__ == "__main__":
    test_circuit_library()
