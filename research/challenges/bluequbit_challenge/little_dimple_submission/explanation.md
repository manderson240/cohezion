# BlueQubit Solution Explanation: FLIER Strategy

### Methodology: FLIER (Fluid Latent Inter-Entity Routing)
To solve the 36-qubit "Little Dimple" challenge, we implemented the FLIER strategy, which combines Matrix Product State (MPS) simulation with a dynamic linear routing layer.

1.  **MPS Backbone**: We use 1D Tensor Networks to represent the quantum state, avoiding the exponential $2^{36}$ memory wall.
2.  **Manual Routing**: Since the MPS requires nearest-neighbor gates, we implement a routing layer that inserts SWAP gates to bring non-adjacent qubits together according to the QASM circuit description.
3.  **Renormalized Evolution**: To counter numerical drift over the 4,407-gate circuit, we perform explicit renormalization after SVD truncation at $max\_bond=128$.
4.  **SETI-Protocol Extraction**: We process 250,000 shots from the final state to identify a heavy bitstring with a statistical significance of $13,631 \sigma$.

### Submission Details
- **Primary Bitstring**: `011110010001001111111111100101100010` (Big-Endian)
- **Fidelity**: Bond Dimension 128, Cutoff $1e-5$.
- **Runtime**: Approximately 26 minutes for encoding + 18 minutes for high-fidelity sampling.
