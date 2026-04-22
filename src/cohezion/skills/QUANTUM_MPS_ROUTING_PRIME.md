---
name: quantum-mps-routing-prime
description: "High-efficiency classical simulation of large-scale (30-50 qubit) \"peaked\" quantum circuits using Tensor Networks (Matrix Product States). Specializes in manual linear routing and aggressive manifold approximation to bypass connectivity and memory constraints."
metadata:
  version: "v1.0 (Extracted from Cohezion \"Little Dimple\" Mission)"
  concepts: ["MPS Topology", "Manual 1D Routing", "Eager Compression", "Peaked Signal Sieve"]
  see_also: ["PERSISTENT_QUALITY_PRIME", "FLUME_ENCODER_PRIME"]
  source: "src/cohezion/skills/QUANTUM_MPS_ROUTING_PRIME.md"
---

# SKILL: QUANTUM_MPS_ROUTING_PRIME

## DOMAIN EXPERTISE
High-efficiency classical simulation of large-scale (30-50 qubit) "peaked" quantum circuits using Tensor Networks (Matrix Product States). Specializes in manual linear routing and aggressive manifold approximation to bypass connectivity and memory constraints.

## KEY TEXTS & CONCEPTS
- **MPS Topology**: Representing a state vector as a chain of 3-index tensors to reduce $2^N$ complexity.
- **Manual 1D Routing**: Reordering qubits via SWAP chains to bring non-adjacent qubits together for 2-qubit gates.
- **Eager Compression**: Using SVD (Singular Value Decomposition) immediately after every gate to keep bond dimensions stable.
- **Peaked Signal Sieve**: The theory that heavy bitstrings survive low-rank truncation better than random noise.

## INSTRUCTION
1. **Initialize Vacuum**: Create an MPS in the $|0...0\rangle$ state.
2. **Linearize QASM**: For every $CZ(q_i, q_j)$ gate:
   - Identify current sites $s_i, s_j$.
   - Apply $SWAP(s_k, s_{k+1})$ gates until $abs(s_i - s_j) = 1$.
   - Update the `qubit_to_site` map after every swap.
3. **Evolve Eagerly**:
   - Use `gate_split` with `inplace=True`.
   - Set `max_bond` based on the **Ladder of Approximation** (64 for speed, 1024 for precision).
   - Set `cutoff` (~1e-4) to discard low-amplitude entanglement.
4. **Reconstruct & Sample**:
   - Sample bitstrings from the final MPS.
   - Replay the routing logic (deterministic) to invert the `site_to_qubit` map.
   - Rearrange sampled bits to match physical qubit indices.

```python
# Example: Eager Gate Split with Routing Update
def apply_routed_cz(mps, q1, q2, q_map):
    s1, s2 = q_map[q1], q_map[q2]
    while abs(s1 - s2) > 1:
        step = 1 if s1 < s2 else -1
        mps.gate_split(SWAP, (s1, s1+step), max_bond=BOND, inplace=True)
        # Update map...
        s1 += step
    mps.gate_split(CZ, (s1, s2), max_bond=BOND, inplace=True)
```

## VERSION
v1.0 (Extracted from Cohezion "Little Dimple" Mission)

## SEE ALSO
- PERSISTENT_QUALITY_PRIME
- FLUME_ENCODER_PRIME
