def solver_routing(N, ops):
    site_to_qubit = list(range(N))
    qubit_to_site = list(range(N))

    for _name, qubits in ops:
        target_sites = [qubit_to_site[q] for q in qubits]
        if len(target_sites) == 2:
            s1, s2 = target_sites
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
                qubit_to_site[q_a] = swap_b
                qubit_to_site[q_b] = swap_a
    return site_to_qubit


def verifier_routing(N, ops):
    site_to_qubit = list(range(N))
    qubit_to_site = list(range(N))

    for name, qubits in ops:
        if name == "CZ":
            s1 = qubit_to_site[qubits[0]]
            s2 = qubit_to_site[qubits[1]]
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
    return site_to_qubit


if __name__ == "__main__":
    N = 4
    # Test case: CZ q[0], q[3]
    ops = [("CZ", (0, 3))]

    s_map = solver_routing(N, ops)
    v_map = verifier_routing(N, ops)

    print(f"Solver Map:   {s_map}")
    print(f"Verifier Map: {v_map}")

    assert s_map == v_map, "Mapping mismatch!"
    print("SUCCESS: Mapping logic is consistent.")

    # Sampling logic check
    # bits[site_idx] is value of qubit site_to_qubit[site_idx]
    # We want ordered[q_idx]
    bits = "ABCD"  # site 0 has A, site 1 has B...

    # Solver reordering
    ordered_s = [""] * N
    for site_idx, bit in enumerate(bits):
        q_idx = s_map[site_idx]
        ordered_s[q_idx] = bit

    # Verifier reordering
    ordered_v = [""] * N
    for site_idx, bit in enumerate(bits):
        q_idx = v_map[site_idx]
        ordered_v[q_idx] = bit

    print(f"Ordered S: {''.join(ordered_s)}")
    print(f"Ordered V: {''.join(ordered_v)}")
    assert ordered_s == ordered_v, "Ordering mismatch!"

    # Let's trace it carefully for N=4, CZ(0,3)
    # Start: s_to_q = [0,1,2,3], q_to_s = [0,1,2,3]
    # Loop 1: s1=0, s2=3. s1 < s2. swap(0,1). s1=1. map: [1,0,2,3], q_to_s: [1,0,2,3]
    # Loop 2: s1=1, s2=3. s1 < s2. swap(1,2). s1=2. map: [1,2,0,3], q_to_s: [2,0,1,3]
    # Loop 3: abs(2-3)=1. Ends.
    # Final map: [1, 2, 0, 3] -> site 0:q1, site 1:q2, site 2:q0, site 3:q3
    # Qubits: q0 at site 2, q1 at site 0, q2 at site 1, q3 at site 3.
    # bits: A B C D (A=site0, B=site1, C=site2, D=site3)
    # ordered[q0] = bits[site2] = C
    # ordered[q1] = bits[site0] = A
    # ordered[q2] = bits[site1] = B
    # ordered[q3] = bits[site3] = D
    # ordered = CABD

    # Is this what we want?
    # q0 q1 q2 q3 order?
    # CABD means q0=C, q1=A, q2=B, q3=D.
    # Wait, site 2 had qubit 0. So bit at index 2 (C) is qubit 0.
    # Correct.
