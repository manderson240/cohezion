import logging
import os
import pickle


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verifier")


def verify():
    checkpoint_path = "peaked_mps_final.dill"
    logger.info(f"Loading checkpoint from {checkpoint_path}...")

    try:
        with open(checkpoint_path, "rb") as f:
            psi_mps = pickle.load(f)

        logger.info(f"Loaded MPS. Max Bond Dim: {psi_mps.max_bond()}")
        logger.info(f"Tensor Count: {len(psi_mps.tensors)}")

        # Sampling
        samples = 5
        logger.info(f"Sampling {samples} shots...")
        raw_samples = list(psi_mps.sample(samples))

        logger.info(f"Raw Samples Type: {type(raw_samples)}")
        if len(raw_samples) > 0:
            logger.info(f"Sample 0 Type: {type(raw_samples[0])}")
            logger.info(f"Sample 0 Content: {raw_samples[0]}")

        # REPLAY ROUTING to reconstruct map
        logger.info("Replaying routing to reconstruct site map...")
        qasm_path = "P1_little_dimple.qasm"
        if not os.path.exists(qasm_path):
            qasm_path = "src/cohezion/physics/quantum/P1_little_dimple.qasm"

        # 1. Parse QASM (Simplified version of Solver parser)
        ops = []
        with open(qasm_path) as f:
            lines = f.readlines()

        N_qubits = 36

        for line in lines:
            line = line.strip().replace(";", "")
            if not line or line.startswith(("OPENQASM", "include", "qreg", "//")):
                continue

            if line.startswith("cz"):
                parts = line.split()[1].split(",")
                q1 = int(parts[0].split("[")[1].split("]")[0])
                q2 = int(parts[1].split("[")[1].split("]")[0])
                ops.append(("CZ", [], (q1, q2)))
            elif line.startswith("u("):
                # We need U gates only to match the iteration count if needed,
                # but routing only happens on 2-qubit gates.
                # Solver iterates ALL ops. So we must iterate ALL ops to match indices/order.
                q_str = line.split(")")[1].strip()
                q = int(q_str.split("[")[1].split("]")[0])
                ops.append(("U3", [], (q,)))

        # 2. Replay Routing
        site_to_qubit = list(range(N_qubits))
        qubit_to_site = list(range(N_qubits))

        for _, (_name, _params, qubits) in enumerate(ops):
            target_sites = [qubit_to_site[q] for q in qubits]

            if len(target_sites) == 2:
                s1, s2 = target_sites

                while abs(s1 - s2) > 1:
                    # Logic must match Solver EXACTLY
                    if s1 < s2:
                        swap_a, swap_b = s1, s1 + 1
                        s1 += 1
                    else:
                        swap_a, swap_b = s1 - 1, s1
                        s1 -= 1

                    # Update Map
                    q_a = site_to_qubit[swap_a]
                    q_b = site_to_qubit[swap_b]

                    site_to_qubit[swap_a], site_to_qubit[swap_b] = q_b, q_a
                    qubit_to_site[q_a] = swap_b
                    qubit_to_site[q_b] = swap_a

                # Update target sites (Solver did this)
                target_sites = [qubit_to_site[q] for q in qubits]

        logger.info("Map reconstruction complete.")

        # 3. Decode Samples
        # Large scale sampling for statistical stability
        sampling_count = 20000
        logger.info(f"Sampling {sampling_count} shots for statistical stability...")
        raw_samples = list(psi_mps.sample(sampling_count))

        counts = {}
        for sample_tuple in raw_samples:
            # sample_tuple is ( [bits...], probability )
            bits = sample_tuple[0]

            ordered_bits = [""] * N_qubits
            for site_idx, bit in enumerate(bits):
                q_idx = site_to_qubit[site_idx]
                ordered_bits[q_idx] = str(bit)

            bstr = "".join(ordered_bits)
            counts[bstr] = counts.get(bstr, 0) + 1

        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        logger.info("TOP CANDIDATES FOUND (Big-Endian: Q0 is index 0):")
        for i in range(min(5, len(sorted_counts))):
            cand, freq = sorted_counts[i]
            print(f"Rank {i + 1}: {cand} (Count: {freq})")

        # Marginal Analysis
        marginals = [0] * N_qubits
        for bstr in counts:
            for i, bit in enumerate(bstr):
                if bit == "1":
                    marginals[i] += counts[bstr]

        marginal_winner = []
        for i in range(N_qubits):
            prob1 = marginals[i] / sampling_count
            marginal_winner.append("1" if prob1 > 0.5 else "0")

        mw_str = "".join(marginal_winner)
        logger.info(f"MARGINAL WINNER (Big-Endian): {mw_str}")
        logger.info(f"MARGINAL WINNER (Little-Endian): {mw_str[::-1]}")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verify()
