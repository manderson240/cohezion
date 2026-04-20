"""
BlueQubit Pennylane Integration Template
For variational quantum algorithms (VQA/QAOA)
"""

import os
from dotenv import load_dotenv
import pennylane as qml
from pennylane import numpy as np


def pennylane_basic_example():
    """
    Basic Pennylane circuit using BlueQubit device.
    """
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")
    token = os.getenv("BLUEQUBIT_API_TOKEN")

    # Create device (CPU version)
    dev = qml.device("bluequbit.cpu", wires=2, token=token)

    # Define quantum circuit
    @qml.qnode(dev)
    def circuit(angle):
        qml.RY(angle, wires=0)
        qml.CNOT(wires=[0, 1])
        return qml.probs(wires=[0, 1])

    # Execute with different angles
    for angle in [0, np.pi / 4, np.pi / 2]:
        probs = circuit(angle)
        print(f"Angle {angle:.4f}: {probs}")

    return probs


def variational_optimization_example():
    """
    Example of variational optimization using Pennylane + BlueQubit.
    Optimizes a rotation angle to maximize |1> probability.
    """
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")
    token = os.getenv("BLUEQUBIT_API_TOKEN")

    dev = qml.device("bluequbit.cpu", wires=1, token=token)

    @qml.qnode(dev)
    def circuit(params):
        qml.RY(params[0], wires=0)
        return qml.expval(qml.PauliZ(0))

    # Initialize parameters
    params = np.array([0.1], requires_grad=True)

    # Optimize
    opt = qml.GradientDescentOptimizer(stepsize=0.1)

    print("Optimizing variational circuit...")
    for i in range(10):
        params = opt.step(circuit, params)
        cost = circuit(params)
        if i % 2 == 0:
            print(f"Step {i}: cost={cost:.6f}, params={params[0]:.6f}")

    print(f"\nFinal parameters: {params}")
    return params


def qaoa_maxcut_example():
    """
    QAOA example for MaxCut problem.
    Demonstrates hybrid classical-quantum workflow.
    """
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")
    token = os.getenv("BLUEQUBIT_API_TOKEN")

    # Define graph (triangle)
    edges = [(0, 1), (1, 2), (2, 0)]

    dev = qml.device("bluequbit.cpu", wires=3, token=token)

    @qml.qnode(dev)
    def qaoa_circuit(params, edges):
        # Prepare superposition
        for i in range(3):
            qml.Hadamard(wires=i)

        # Apply QAOA layers
        for i, (u, v) in enumerate(edges):
            qml.CNOT(wires=[u, v])
            qml.RZ(params[0][i], wires=v)
            qml.CNOT(wires=[u, v])

        # Mixer layer
        for i in range(3):
            qml.RX(params[1][i], wires=i)

        return qml.expval(qml.PauliZ(0) @ qml.PauliZ(1))

    # Initialize parameters
    params = [np.random.random(3), np.random.random(3)]

    print("QAOA example (MaxCut on triangle graph)")
    expectation = qaoa_circuit(params, edges)
    print(f"Expectation value: {expectation}")

    return expectation


if __name__ == "__main__":
    print("=== Pennylane Basic Example ===")
    pennylane_basic_example()

    print("\n=== Variational Optimization Example ===")
    variational_optimization_example()

    print("\n=== QAOA Example ===")
    qaoa_maxcut_example()

    print("\n✓ All Pennylane templates ready")
