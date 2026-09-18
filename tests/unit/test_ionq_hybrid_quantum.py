"""Unit tests for IonQ Hybrid Quantum-Classical modules (IEEE QCE26)."""

from __future__ import annotations

from cohezion.quantum.dqaoa_circuit_synthesizer import (
    DQAOACircuit,
    DQAOACircuitSynthesizer,
)
from cohezion.quantum.quantum_parity_encoder import (
    ParityBasisModel,
    QuantumParityEncoder,
)
from cohezion.quantum.warm_start_combinatorial_solver import (
    PartitionSolution,
    WarmStartCombinatorialSolver,
)


def test_dqaoa_circuit_synthesizer():
    # 6-node QUBO graph
    Q = {
        (0, 1): 1.5,
        (1, 2): 2.0,
        (2, 3): 1.0,
        (3, 4): 2.5,
        (4, 5): 1.2,
        (0, 5): 0.8,
        (0, 0): -1.0,
        (1, 1): 0.5,
    }
    synthesizer = DQAOACircuitSynthesizer(max_qubits_per_subgraph=4, default_depth_p=2)

    # 1. Test QUBO decomposition into bounded subgraphs
    subgraphs = synthesizer.decompose_qubo(Q, num_nodes=6)
    assert len(subgraphs) >= 2
    for sg in subgraphs:
        assert len(sg["nodes"]) <= 4

    # 2. Test circuit synthesis
    circuit = synthesizer.synthesize_circuit(subgraphs[0]["Q"], num_qubits=len(subgraphs[0]["nodes"]), depth_p=2)
    assert isinstance(circuit, DQAOACircuit)
    assert circuit.num_qubits == len(subgraphs[0]["nodes"])
    assert circuit.depth_p == 2
    assert circuit.gate_count > 0

    # 3. Test QASM export
    qasm = circuit.to_qasm()
    assert "OPENQASM 2.0;" in qasm
    assert f"qreg q[{circuit.num_qubits}];" in qasm


def test_warm_start_combinatorial_solver():
    # 4-node ring adjacency matrix
    adj_matrix = [
        [0.0, 1.0, 0.0, 1.0],
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [1.0, 0.0, 1.0, 0.0],
    ]
    solver = WarmStartCombinatorialSolver(balance_penalty=5.0, seed=42)

    # Quantum priors favoring nodes 0, 1 in partition 0 and nodes 2, 3 in partition 1
    priors = [-0.9, -0.8, 0.8, 0.9]
    sol = solver.solve_graph_partitioning(adj_matrix, num_partitions=2, quantum_priors=priors)

    assert isinstance(sol, PartitionSolution)
    assert len(sol.partitions) == 4
    assert sol.metadata["quantum_warmed"] is True
    # In a 4-node ring partitioned {0,1} and {2,3}, the cut size should be 2.0
    assert sol.cut_size <= 2.0

    # Test multi-modal shipment optimization
    shipments = [
        {"id": "ship_1", "weight": 500.0, "urgency": 0.9},
        {"id": "ship_2", "weight": 20000.0, "urgency": 0.2},
    ]
    route_priors = [[0.1, 0.1, 0.8], [0.1, 0.8, 0.1]]  # [truck, rail, air]
    routes = solver.solve_multi_modal_shipment(shipments, quantum_route_priors=route_priors)
    assert len(routes) == 2
    assert routes[0]["assigned_mode"] == "air"
    assert routes[1]["assigned_mode"] == "rail"


def test_quantum_parity_encoder():
    # Simple synthetic 2D data
    X = [
        [1.0, 1.0],
        [1.0, -1.0],
        [-1.0, 1.0],
        [-1.0, -1.0],
    ]
    # XOR function (parity)
    y = [0.0, 1.0, 1.0, 0.0]

    encoder = QuantumParityEncoder(num_parities=4)
    model = encoder.fit(X, y)

    assert isinstance(model, ParityBasisModel)
    assert model.input_dim == 2
    assert model.num_parities == 4
    assert len(model.basis_matrix) == 4

    # Test transformation and prediction
    feats = model.transform([1.0, 1.0])
    assert len(feats) == 4
    pred = model.predict([1.0, 1.0])
    assert 0.0 <= pred <= 1.0
