"""DQAOA Circuit Synthesizer (IEEE QCE26 / arXiv:2607.20225).

Implements Directed Quantum Approximate Optimization Algorithm (DQAOA-GPT)
hybrid decomposition. Rather than running hundreds of iterative parameter
updates on QPUs (which suffer from barren plateaus and high queue latencies),
DQAOA-GPT decomposes large combinatorial/QUBO problems into bounded subgraphs
and synthesizes targeted quantum ansatz circuits with pre-computed or
AI-guided variational angles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QuantumGate:
    """Represents a quantum circuit gate operation."""

    name: str  # e.g., "H", "RZ", "RX", "RZZ", "CX"
    qubits: list[int]
    params: list[float] = field(default_factory=list)

    def to_qasm(self) -> str:
        """Serialize gate to OpenQASM 2.0 format."""
        if not self.params:
            if len(self.qubits) == 1:
                return f"{self.name.lower()} q[{self.qubits[0]}];"
            if len(self.qubits) == 2:
                return f"{self.name.lower()} q[{self.qubits[0]}], q[{self.qubits[1]}];"
        if len(self.params) == 1:
            val = self.params[0]
            if len(self.qubits) == 1:
                return f"{self.name.lower()}({val:.6f}) q[{self.qubits[0]}];"
            if len(self.qubits) == 2:
                return f"{self.name.lower()}({val:.6f}) q[{self.qubits[0]}], q[{self.qubits[1]}];"
        return f"// unsupported gate: {self.name}"


@dataclass(slots=True)
class DQAOACircuit:
    """Synthesized DQAOA quantum circuit for a subproblem."""

    num_qubits: int
    depth_p: int
    gates: list[QuantumGate] = field(default_factory=list)
    gamma: list[float] = field(default_factory=list)
    beta: list[float] = field(default_factory=list)
    subgraph_id: str = "subgraph_0"

    def to_qasm(self) -> str:
        """Export full circuit to OpenQASM 2.0."""
        lines = [
            'OPENQASM 2.0;',
            'include "qelib1.inc";',
            f"qreg q[{self.num_qubits}];",
            f"creg c[{self.num_qubits}];",
        ]
        for g in self.gates:
            lines.append(g.to_qasm())
        return "\n".join(lines)

    @property
    def gate_count(self) -> int:
        return len(self.gates)

    @property
    def two_qubit_gate_count(self) -> int:
        return sum(1 for g in self.gates if len(g.qubits) == 2)


class DQAOACircuitSynthesizer:
    """Synthesizes DQAOA quantum circuits from QUBO problem formulations."""

    def __init__(self, max_qubits_per_subgraph: int = 16, default_depth_p: int = 2):
        self.max_qubits = max_qubits_per_subgraph
        self.default_depth_p = default_depth_p

    def decompose_qubo(
        self, Q: dict[tuple[int, int], float], num_nodes: int
    ) -> list[dict[str, Any]]:
        """Decompose a large QUBO matrix into connected subgraphs within qubit bounds.

        Parameters
        ----------
        Q : dict[tuple[int, int], float]
            Quadratic unconstrained binary optimization coefficients.
        num_nodes : int
            Total number of variables in the master problem.

        Returns
        -------
        list[dict[str, Any]]
            List of subproblem specifications with node subsets and local Q matrices.
        """
        if num_nodes <= self.max_qubits:
            return [{"id": "subgraph_main", "nodes": list(range(num_nodes)), "Q": Q}]

        # Greedy community partitioning
        subgraphs: list[dict[str, Any]] = []
        unassigned = set(range(num_nodes))
        subgraph_idx = 0

        while unassigned:
            # Seed cluster with highest-degree unassigned node
            node_degrees = {
                u: sum(1 for (i, j) in Q if (i == u or j == u) and (i in unassigned and j in unassigned))
                for u in unassigned
            }
            seed = max(node_degrees, key=node_degrees.get)  # type: ignore[arg-type]
            current_cluster = {seed}
            unassigned.remove(seed)

            # Expand cluster up to max_qubits
            while len(current_cluster) < self.max_qubits and unassigned:
                best_candidate = None
                best_coupling = -1.0
                for u in unassigned:
                    coupling = sum(
                        abs(Q.get((min(u, v), max(u, v)), 0.0)) for v in current_cluster
                    )
                    if coupling > best_coupling:
                        best_coupling = coupling
                        best_candidate = u
                if best_candidate is not None and best_coupling > 0:
                    current_cluster.add(best_candidate)
                    unassigned.remove(best_candidate)
                else:
                    break

            cluster_nodes = sorted(current_cluster)
            node_map = {orig: idx for idx, orig in enumerate(cluster_nodes)}
            sub_Q: dict[tuple[int, int], float] = {}
            for (i, j), val in Q.items():
                if i in current_cluster and j in current_cluster:
                    sub_Q[(node_map[i], node_map[j])] = val

            subgraphs.append(
                {
                    "id": f"subgraph_{subgraph_idx}",
                    "nodes": cluster_nodes,
                    "node_map": node_map,
                    "Q": sub_Q,
                }
            )
            subgraph_idx += 1

        return subgraphs

    def synthesize_circuit(
        self,
        sub_Q: dict[tuple[int, int], float],
        num_qubits: int,
        depth_p: int | None = None,
        gamma: list[float] | None = None,
        beta: list[float] | None = None,
        subgraph_id: str = "subgraph_0",
    ) -> DQAOACircuit:
        """Synthesize parameterized DQAOA ansatz circuit for a subproblem.

        Parameters
        ----------
        sub_Q : dict[tuple[int, int], float]
            Subproblem QUBO matrix.
        num_qubits : int
            Number of qubits for the subproblem.
        depth_p : int, optional
            Circuit depth layers p (defaults to default_depth_p).
        gamma : list[float], optional
            Cost unitary rotation angles per layer.
        beta : list[float], optional
            Mixer unitary rotation angles per layer.
        subgraph_id : str
            Identifier for the subcircuit.

        Returns
        -------
        DQAOACircuit
            The synthesized quantum circuit.
        """
        p = depth_p if depth_p is not None else self.default_depth_p
        # Deterministic linear schedule heuristic if angles not provided
        if gamma is None or len(gamma) < p:
            gamma = [math.pi * (i + 1) / (2.0 * p) for i in range(p)]
        if beta is None or len(beta) < p:
            beta = [math.pi * (1.0 - (i + 0.5) / p) / 2.0 for i in range(p)]

        gates: list[QuantumGate] = []

        # Layer 0: Initial equal superposition via Hadamard gates
        for q in range(num_qubits):
            gates.append(QuantumGate(name="H", qubits=[q]))

        # Layers 1..p: Alternating Cost and Mixer Unitaries
        for layer in range(p):
            g_angle = gamma[layer]
            b_angle = beta[layer]

            # 1. Cost Unitary U_C(gamma)
            # Diagonal terms (single qubit RZ)
            for q in range(num_qubits):
                diag_weight = sub_Q.get((q, q), 0.0)
                if abs(diag_weight) > 1e-6:
                    theta = 2.0 * g_angle * diag_weight
                    gates.append(QuantumGate(name="RZ", qubits=[q], params=[theta]))

            # Off-diagonal terms (two qubit RZZ via CX -> RZ -> CX)
            for (u, v), weight in sub_Q.items():
                if u != v and abs(weight) > 1e-6:
                    theta = 2.0 * g_angle * weight
                    gates.append(QuantumGate(name="CX", qubits=[u, v]))
                    gates.append(QuantumGate(name="RZ", qubits=[v], params=[theta]))
                    gates.append(QuantumGate(name="CX", qubits=[u, v]))

            # 2. Mixer Unitary U_B(beta) (transverse field RX)
            for q in range(num_qubits):
                gates.append(QuantumGate(name="RX", qubits=[q], params=[2.0 * b_angle]))

        return DQAOACircuit(
            num_qubits=num_qubits,
            depth_p=p,
            gates=gates,
            gamma=gamma[:p],
            beta=beta[:p],
            subgraph_id=subgraph_id,
        )

    def synthesize_subgraphs(
        self, Q: dict[tuple[int, int], float], num_nodes: int
    ) -> list[DQAOACircuit]:
        """Decompose and synthesize circuits for all subgraphs."""
        subgraphs = self.decompose_qubo(Q, num_nodes)
        circuits: list[DQAOACircuit] = []
        for sg in subgraphs:
            circuit = self.synthesize_circuit(
                sub_Q=sg["Q"],
                num_qubits=len(sg["nodes"]),
                subgraph_id=sg["id"],
            )
            circuits.append(circuit)
        return circuits
