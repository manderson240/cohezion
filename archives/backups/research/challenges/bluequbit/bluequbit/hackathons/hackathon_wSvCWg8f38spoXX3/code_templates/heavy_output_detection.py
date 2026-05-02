"""
BlueQubit Heavy Output Detection Template
Based on "Little Dimple" SETI Protocol approach
"""

from pathlib import Path

import bluequbit
import numpy as np
import qiskit
from dotenv import load_dotenv


def find_heavy_output(counts: dict, threshold: float = 0.5) -> dict:
    """
    Find bitstrings with probability > threshold * uniform_prob.

    This implements the "Heavy Output" detection from the IBM quantum
    volume paper and the BlueQubit "Little Dimple" challenge.

    Args:
        counts: Dictionary of {bitstring: count/probability}
        threshold: Multiplier above uniform probability (default: 0.5)
                   Higher threshold = fewer, more significant peaks

    Returns:
        dict: Heavy outputs {bitstring: probability}
    """
    # Determine number of qubits from bitstring length
    n_qubits = len(list(counts.keys())[0])
    total = sum(counts.values())

    # Calculate uniform probability
    uniform_prob = 1.0 / (2**n_qubits)
    threshold_prob = threshold * uniform_prob

    # Find heavy outputs
    heavy_outputs = {}
    for bitstring, count in counts.items():
        prob = count / total if isinstance(count, (int, float)) else count
        if prob > threshold_prob:
            heavy_outputs[bitstring] = prob

    return heavy_outputs


def calculate_snr(heavy_prob: float, n_qubits: int) -> float:
    """
    Calculate Signal-to-Noise Ratio in sigma units.

    Args:
        heavy_prob: Probability of heavy output
        n_qubits: Number of qubits

    Returns:
        float: SNR in sigma units
    """
    uniform_prob = 1.0 / (2**n_qubits)
    # Approximate sigma calculation for binomial distribution
    noise = np.sqrt(uniform_prob * (1 - uniform_prob))
    signal = heavy_prob - uniform_prob
    snr = signal / noise if noise > 0 else 0
    return snr


def detect_heavy_output(
    circuit: qiskit.QuantumCircuit,
    shots: int = 100000,
    threshold: float = 0.5,
    device: str = "mps.cpu",
) -> dict:
    """
    Detect heavy output from quantum circuit execution.

    Args:
        circuit: Qiskit quantum circuit
        shots: Number of measurement shots
        threshold: Heavy output threshold
        device: BlueQubit device

    Returns:
        dict: Detection results
    """
    # Load credentials
    project_root = Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")

    # Initialize client
    bq = bluequbit.init()

    print(f"Running {circuit.num_qubits}-qubit circuit with {shots} shots...")

    # Execute circuit
    result = bq.run(circuit, device=device, shots=shots)
    counts = result.get_counts()

    # Find heavy outputs
    heavy_outputs = find_heavy_output(counts, threshold)

    # Calculate statistics
    n_qubits = circuit.num_qubits
    uniform_prob = 1.0 / (2**n_qubits)
    total_heavy_prob = sum(heavy_outputs.values())

    # Prepare results
    results = {
        "n_qubits": n_qubits,
        "shots": shots,
        "threshold": threshold,
        "uniform_probability": uniform_prob,
        "threshold_probability": threshold * uniform_prob,
        "num_heavy_outputs": len(heavy_outputs),
        "total_heavy_probability": total_heavy_prob,
        "heavy_outputs": heavy_outputs,
    }

    # Add SNR for top output if found
    if heavy_outputs:
        top_bitstring = max(heavy_outputs, key=heavy_outputs.get)
        top_prob = heavy_outputs[top_bitstring]
        snr = calculate_snr(top_prob, n_qubits)
        results["top_bitstring"] = top_bitstring
        results["top_probability"] = top_prob
        results["snr_sigma"] = snr

    return results


def print_detection_results(results: dict):
    """Pretty print detection results."""
    print(f"\n{'=' * 60}")
    print("Heavy Output Detection Results")
    print(f"{'=' * 60}")
    print(f"Qubits: {results['n_qubits']}")
    print(f"Shots: {results['shots']:,}")
    print(f"Threshold: {results['threshold']}")
    print(f"Uniform Probability: {results['uniform_probability']:.2e}")
    print(f"Threshold Probability: {results['threshold_probability']:.2e}")
    print(f"\nHeavy Outputs Found: {results['num_heavy_outputs']}")
    print(f"Total Heavy Probability: {results['total_heavy_probability']:.6f}")

    if "top_bitstring" in results:
        print("\nTop Heavy Output:")
        print(f"  Bitstring: {results['top_bitstring']}")
        print(f"  Probability: {results['top_probability']:.6f}")
        print(f"  SNR: {results['snr_sigma']:.2f} sigma")

    if results["heavy_outputs"]:
        print("\nAll Heavy Outputs:")
        for bitstring, prob in sorted(
            results["heavy_outputs"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {bitstring}: {prob:.6f}")

    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    print("=== Heavy Output Detection Template ===\n")

    # Example 1: GHZ state (should have 2 heavy outputs)
    print("Example 1: GHZ State (10 qubits)")
    print("-" * 40)

    qc_ghz = qiskit.QuantumCircuit(10)
    qc_ghz.h(0)
    for i in range(9):
        qc_ghz.cx(i, i + 1)
    qc_ghz.measure_all()

    results = detect_heavy_output(qc_ghz, shots=10000, threshold=0.4)
    print_detection_results(results)

    # Example 2: Random circuit
    print("\nExample 2: Random Circuit (5 qubits)")
    print("-" * 40)

    from qiskit.circuit.random import random_circuit

    qc_random = random_circuit(5, depth=5, measure=True, seed=42)

    results = detect_heavy_output(qc_random, shots=10000, threshold=0.6)
    print_detection_results(results)

    print("✓ Heavy output detection template ready")
