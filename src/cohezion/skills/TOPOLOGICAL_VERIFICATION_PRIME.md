# SKILL: TOPOLOGICAL_VERIFICATION_PRIME

## DOMAIN EXPERTISE
This skill provides a "white-box" verification framework for Large Reasoning Models (LRMs) using **Topological Data Analysis (TDA)**. It treats the reasoning process as a geometric trajectory through a high-dimensional manifold and uses **Persistent Homology (PH)** to detect logical inconsistencies (hallucinations) that are invisible to standard text-based verifiers.

## KEY TEXTS & CONCEPTS
- **Reasoning Manifold**: The high-dimensional space formed by the hidden states and attention maps of an LLM during a multi-step proof.
- **Persistent Homology (PH)**: A method for computing topological features (clusters, holes, cycles) of a point cloud across multiple scales.
- **Topological Snap**: A sudden, non-smooth jump in the latent trajectory, signaling a hallucination or a "reasoning gap."
- **Betti Numbers (H0, H1)**: H0 measures semantic connectivity (connected components); H1 identifies circular reasoning or logical redundancy (loops).
- **Zigzag Persistence**: Tracking how topological features evolve across layers or time steps to filter noise from fundamental logic.

## INSTRUCTION
1. **Extraction**: Extract the hidden embeddings $h_t$ or attention matrices $A_l$ for each reasoning step $t$ or layer $l$.
2. **Filtration**: Construct a Vietoris-Rips complex from the point cloud of embeddings. Edge distance $d(i,j) = 1 - \text{cosine\_similarity}(h_i, h_j)$.
3. **Computation**: Use a library like `GUDHI` or `Ripser` to compute the persistence barcode.
   ```python
   import gudhi
   rips = gudhi.RipsComplex(points=embeddings, max_edge_distance=0.5)
   simplex_tree = rips.create_simplex_tree(max_dimension=2)
   persistence = simplex_tree.persistence()
   ```
4. **Verification**: 
   - **Check H0**: If the steps do not merge into a single component at low scale, the proof is logically disconnected.
   - **Check H1**: If a persistent 1-cycle emerges, the model is stuck in a circular reasoning loop.
   - **Check Wasserstein Distance**: Compare the barcode against a "ground-truth" signature of valid proofs in that domain.

## VERSION
v0.1

## SEE ALSO
- `FLUME_METHODOLOGY_PRIME`
- `MATH_REASONING_SWARM_PRIME`
- `HIHO_STABILITY_PRIME`
