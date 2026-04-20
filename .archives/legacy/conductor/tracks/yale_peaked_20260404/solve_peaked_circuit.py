import os
import bluequbit
import qiskit
import numpy as np
from dotenv import load_dotenv

# Load environment variables for BlueQubit token
load_dotenv(".env")


def bootstrap_majority_vote(counts, n_qubits, n_bootstraps=10):
    """
    Performs bootstrap re-sampling of counts to verify stability of the majority vote.
    """
    total = sum(counts.values())
    bitstrings = list(counts.keys())
    probs = [c / total for c in counts.values()]

    bootstrap_results = []
    for _ in range(n_bootstraps):
        # Generate a virtual batch of samples via multinomial re-sampling
        sample_indices = np.random.choice(len(bitstrings), size=total, p=probs)
        virtual_counts = [{"0": 0, "1": 0} for _ in range(n_qubits)]

        for idx in sample_indices:
            bs = bitstrings[idx]
            for i, bit in enumerate(bs):
                virtual_counts[i][bit] += 1

        voted = "".join(["0" if v["0"] > v["1"] else "1" for v in virtual_counts])
        bootstrap_results.append(voted)

    # Find most common bitstring across bootstraps
    unique_voted, counts_voted = np.unique(bootstrap_results, return_counts=True)
    best_voted_lsb = unique_voted[np.argmax(counts_voted)]
    consistency = np.max(counts_voted) / n_bootstraps

    return best_voted_lsb[::-1], consistency


def find_heavy_output(counts, n_qubits, threshold=0.5):
    """
    Find heavy output bitstring from counts dictionary.
    Reverses bitstring to MSB for the hackathon format.
    Also performs Bootstrap Majority Voting for high-noise scenarios.
    """
    total = sum(counts.values())
    uniform_prob = 1.0 / (2**n_qubits)
    threshold_prob = threshold * uniform_prob

    # 1. Standard Heavy Output Search
    heavy = {b: c / total for b, c in counts.items() if c / total > threshold_prob}

    # 2. Bootstrap Majority Voting (Post-2026 Refinement)
    voted_msb, confidence = bootstrap_majority_vote(counts, n_qubits)

    if not heavy:
        print(
            f"⚠️ No heavy output found. Falling back to Bootstrap Majority Voting (Stability: {confidence:.1%})"
        )
        return {
            "bitstring": voted_msb,
            "probability": 0.0,  # Not a single peak
            "snr": 0.0,
            "num_heavy": 0,
            "method": "bootstrap_majority_voting",
            "stability": confidence,
        }

    # Get top bitstring (BlueQubit LSB format)
    top_bitstring_lsb = max(heavy.items(), key=lambda x: x[1])[0]
    top_prob = heavy[top_bitstring_lsb]
    top_bitstring_msb = top_bitstring_lsb[::-1]

    # Calculate SNR (Signal to Noise Ratio)
    signal = top_prob - uniform_prob
    noise = np.sqrt(uniform_prob * (1 - uniform_prob))
    snr = signal / noise if noise > 0 else 0

    return {
        "bitstring": top_bitstring_msb,
        "probability": top_prob,
        "snr": snr,
        "num_heavy": len(heavy),
        "method": "heavy_output",
        "majority_voted": voted_msb,
        "stability": confidence,
    }


def analyze_circuit_topology(circuit):
    """
    Analyzes circuit connectivity and gate density to predict MPS difficulty.
    """
    n_qubits = circuit.num_qubits
    gates = circuit.count_ops()
    depth = circuit.depth()

    # Build adjacency matrix for connectivity
    adj = np.zeros((n_qubits, n_qubits))
    for instr, qargs, _ in circuit.data:
        if len(qargs) == 2:
            q1, q2 = circuit.find_bit(qargs[0]).index, circuit.find_bit(qargs[1]).index
            adj[q1, q2] += 1
            adj[q2, q1] += 1

    avg_connectivity = np.sum(adj > 0) / n_qubits
    is_all_to_all = np.all(adj > 0)

    return {
        "n_qubits": n_qubits,
        "depth": depth,
        "gates": gates,
        "avg_connectivity": avg_connectivity,
        "is_all_to_all": is_all_to_all,
    }


def solve_peaked_circuit(
    qasm_file, shots=100000, bond_dim=None, device="mps.cpu", allow_paid=False
):
    """
    Solves a peaked circuit problem.
    """
    # Safety check for paid devices
    is_paid_device = device not in ["mps.cpu", "cpu"]
    if is_paid_device and not allow_paid:
        print(
            f"🛑 SAFETY HALT: Device '{device}' may incur costs. Explicit 'allow_paid=True' required."
        )
        return None

    bq = bluequbit.init()

    try:
        # Load circuit
        circuit = qiskit.QuantumCircuit.from_qasm_file(qasm_file)
        n_qubits = circuit.num_qubits

        # Topology Analysis
        topology = analyze_circuit_topology(circuit)
        print(
            f"📐 Topology: {topology['n_qubits']} qubits, Depth {topology['depth']}, "
            f"Connectivity {topology['avg_connectivity']:.1f}"
            + (" [ALL-TO-ALL]" if topology["is_all_to_all"] else "")
        )

        # Configure options
        options = {}
        if "mps" in device:
            # Auto-determine bond dimension if not provided
            if bond_dim is None:
                if n_qubits <= 20:
                    bond_dim = 64
                elif n_qubits <= 30:
                    bond_dim = 128
                elif n_qubits <= 40:
                    bond_dim = 256
                else:
                    bond_dim = 512

                # CAP for free tier (mps.cpu) to avoid NOT_ENOUGH_FUNDS
                if device == "mps.cpu" and not allow_paid:
                    if bond_dim > 64:
                        print(
                            f"⚠️ Capping bond_dim from {bond_dim} to 64 for free tier compatibility."
                        )
                        bond_dim = 64

            options["mps_bond_dimension"] = bond_dim
            print(f"🔬 Simulating {n_qubits} qubits on {device} (Bond Dim: {bond_dim})")
        else:
            print(f"🔬 Simulating {n_qubits} qubits on {device}")

        # Run execution
        result = bq.run(circuit, device=device, shots=shots, options=options, timeout=1800)

        counts = result.get_counts()

        # Find and reverse the heavy output
        heavy_result = find_heavy_output(counts, n_qubits)

        return heavy_result

    except Exception as e:
        print(f"Error solving {qasm_file}: {e}")
        return None


if __name__ == "__main__":
    # Test script usage
    import sys

    if len(sys.argv) > 1:
        qasm_path = sys.argv[1]
        print(f"Solving: {qasm_path}")
        res = solve_peaked_circuit(qasm_path)
        if res:
            print(
                f"Result: {res['bitstring']} (Prob: {res['probability']:.4f}, SNR: {res['snr']:.2f})"
            )
    else:
        print("Usage: python3 solve_peaked_circuit.py <path_to_qasm>")
