import logging

import numpy as np


logger = logging.getLogger("QuantumUtils")


def reconstruct_site_map(qasm_path, n_qubits):
    """
    Replays SWAP logic to reconstruct the final site-to-qubit mapping.
    """
    site_to_qubit = list(range(n_qubits))
    qubit_to_site = list(range(n_qubits))

    with open(qasm_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("cz"):
                # cz q[i],q[j]
                parts = (
                    line.replace("cz q[", "")
                    .replace("]", "")
                    .replace(",q[", " ")
                    .replace(";", "")
                    .split()
                )
                if not parts:
                    continue
                q_idxs = [int(p) for p in parts]

                s0 = qubit_to_site[q_idxs[0]]
                s1 = qubit_to_site[q_idxs[1]]
                if s1 < s0:
                    s0, s1 = s1, s0

                # Replay SWAPs
                while s0 < s1 - 1:
                    swap_a, swap_b = s0, s0 + 1
                    q_a = site_to_qubit[swap_a]
                    q_b = site_to_qubit[swap_b]
                    site_to_qubit[swap_a], site_to_qubit[swap_b] = q_b, q_a
                    qubit_to_site[q_a], qubit_to_site[q_b] = swap_b, swap_a
                    s0 += 1
    return site_to_qubit


def compute_seti_metrics(counts, sampling_count, n_qubits):
    """
    Computes Signal-to-Noise ratio and entropy for bitstring distributions.
    """
    p_uniform = 1 / (2**n_qubits)
    std_dev_noise = np.sqrt(sampling_count * p_uniform * (1 - p_uniform))

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    peak_count = sorted_counts[0][1]
    snr = peak_count / std_dev_noise if std_dev_noise > 0 else float("inf")

    total_probs = np.array([c / sampling_count for _, c in counts.items()])
    entropy = -np.sum(total_probs * np.log2(total_probs))

    return {
        "snr": snr,
        "entropy": entropy,
        "peak_bitstring": sorted_counts[0][0],
        "peak_count": peak_count,
    }
