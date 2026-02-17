import logging
import pickle

import quimb.tensor as qtn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MPS_Audit")


def check_prob(psi, bstr, site_to_qubit):
    N = len(bstr)
    site_ordered_bits = [""] * N
    for site_idx in range(N):
        q_idx = site_to_qubit[site_idx]
        site_ordered_bits[site_idx] = bstr[q_idx]

    site_bstr = "".join(site_ordered_bits)

    # Efficiently compute amplitude for MPS
    phi = qtn.MPS_computational_state(site_bstr)
    amp = phi.H @ psi
    return abs(amp) ** 2


def audit():
    checkpoint = "peaked_mps_final.dill"
    with open(checkpoint, "rb") as f:
        psi = pickle.load(f)

    N = 36
    qasm_path = "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"

    site_to_qubit = list(range(N))
    qubit_to_site = list(range(N))

    with open(qasm_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("cz"):
                parts = line.replace("cz q[", "").replace("]", "").replace(",q[", " ").replace(";", "").split()
                if not parts:
                    continue
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

                    q_a, q_b = site_to_qubit[swap_a], site_to_qubit[swap_b]
                    site_to_qubit[swap_a], site_to_qubit[swap_b] = q_b, q_a
                    qubit_to_site[q_a], qubit_to_site[q_b] = swap_b, swap_a

    candidates = {
        "User_Failed_1 (BigE Bond128)": "011110010001001111111111100101100010",
        "User_Failed_2 (BigE Bond64)": "000111100010001010101101010100000001",
        "Reversed_1 (LittleE Bond128)": "011110010001001111111111100101100010"[::-1],
    }

    print("\n--- MPS PROBABILITY AUDIT (Inner Product) ---")
    for name, bstr in candidates.items():
        prob = check_prob(psi, bstr, site_to_qubit)
        print(f"{name}: Prob = {prob:.8e}")

    # Sample to see top
    logger.info("Sampling 20,000 shots...")
    samples = list(psi.sample(20000))
    counts = {}
    for bits, _p in samples:
        ordered = [""] * N
        for s_idx, b in enumerate(bits):
            q_idx = site_to_qubit[s_idx]
            ordered[q_idx] = str(int(b))
        obstr = "".join(ordered)
        counts[obstr] = counts.get(obstr, 0) + 1

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    print("\nTOP SAMPLES IN MANIFOLD:")
    for b, c in sorted_counts[:5]:
        prob_exact = check_prob(psi, b, site_to_qubit)
        print(f"{b}: Count {c}, Exact Prob {prob_exact:.8e}")


if __name__ == "__main__":
    audit()
