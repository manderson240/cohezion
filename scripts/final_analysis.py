import logging
import pickle

import numpy as np


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FinalAnalysis")


def analyze():
    checkpoint = "peaked_mps_final.dill"
    qasm_path = (
        "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"
    )

    logger.info(f"Loading checkpoint {checkpoint}...")
    with open(checkpoint, "rb") as f:
        psi = pickle.load(f)

    N = 36
    logger.info("Reconstructing site map...")
    site_to_qubit = list(range(N))
    qubit_to_site = list(range(N))

    with open(qasm_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("cz"):
                # cz q[i],q[j]
                parts = line.replace("cz q[", "").replace("]", "").replace(",q[", " ").replace(";", "").split()
                q_idxs = [int(p) for p in parts]
                # MATCH SOLVER LOGIC: Move q_idxs[0] to q_idxs[1]
                s1 = qubit_to_site[q_idxs[0]]
                s2 = qubit_to_site[q_idxs[1]]

                while abs(s1 - s2) > 1:
                    if s1 < s2:
                        swap_a, swap_b = s1, s1 + 1
                        s1 += 1
                    else:
                        swap_a, swap_b = s1 - 1, s1
                        s1 -= 1

                    q_a = site_to_qubit[swap_a]
                    q_b = site_to_qubit[swap_b]
                    site_to_qubit[swap_a], site_to_qubit[swap_b] = q_b, q_a
                    qubit_to_site[q_a], qubit_to_site[q_b] = swap_b, swap_a
                # Final positions are (s1-1, s1)

    sampling_count = 100000
    batch_size = 1000
    num_batches = sampling_count // batch_size

    logger.info(f"Sampling {sampling_count} shots in {num_batches} batches (Incremental)...")

    counts = {}
    from tqdm import tqdm

    for _ in tqdm(range(num_batches), desc="Sampling Swarm"):
        # We sample each batch independently
        batch_samples = psi.sample(batch_size)
        for sample in batch_samples:
            bits = sample[0]
            # Map back to qubits
            ordered = [""] * N
            for site_idx, bit in enumerate(bits):
                q_idx = site_to_qubit[site_idx]
                ordered[q_idx] = str(int(bit))
            bstr = "".join(ordered)
            counts[bstr] = counts.get(bstr, 0) + 1

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    # SETI-Protocol Significance Analysis (Signal-to-Noise Ratio)
    p_uniform = 1 / (2**N)
    std_dev_noise = np.sqrt(sampling_count * p_uniform * (1 - p_uniform))

    peak_count = sorted_counts[0][1]
    snr = peak_count / std_dev_noise if std_dev_noise > 0 else float("inf")

    # Entropy calculation
    total_probs = np.array([c / sampling_count for _, c in counts.items()])
    entropy = -np.sum(total_probs * np.log2(total_probs + 1e-20))  # Avoid log(0)

    print("\n--- QUANTUM SETI ANALYSIS (1M SHOTS) ---")
    print(f"Total Samples: {sampling_count}")
    print(f"Unique Bitstrings: {len(counts)}")
    print(f"Peak Count: {peak_count}")
    print(f"Signal-to-Noise Ratio (SNR): {snr:.2f} sigma")
    print(f"State Entropy: {entropy:.4f} bits (Max 36)")

    # Priority Candidates (Compound Engineering approach: rank-ordered output)
    print("\n--- PRIORITY CANDIDATES (BIG-E) ---")
    for i in range(min(3, len(sorted_counts))):
        print(f"Rank {i + 1}: {sorted_counts[i][0]} (Count: {sorted_counts[i][1]})")

    if snr > 5:
        print("\nCONVICTION: DEEP SPACE SIGNAL DETECTED (High Significance)")
    else:
        print("\nCONVICTION: BACKGROUND NOISE DOMINANT")

    # Marginal Analysis
    marginals = [0] * N
    for bstr, count in counts.items():
        for i, bit in enumerate(bstr):
            if bit == "1":
                marginals[i] += count

    mw = "".join(["1" if (m / sampling_count) > 0.5 else "0" for m in marginals])
    print(f"\nMarginal Winner (Big-E): {mw}")
    print(f"Marginal Winner (Little-E): {mw[::-1]}")
    print("--- END ANALYSIS ---")


if __name__ == "__main__":
    analyze()
