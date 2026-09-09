# SKILL: POINCARE_GEODESIC_SEARCH_PRIME

## DOMAIN EXPERTISE
Continuous Hyperbolic Manifold Exploration, Poincaré Ball Geodesics, and Non-Euclidean Combinatorial Search Pruning for Discrete AGI Benchmarks (ARC-AGI, Game Trees).

## KEY TEXTS & CONCEPTS
- **Poincaré Ball Metric Tensor**: $g_{ij}(\mathbf{x}) = \frac{4}{(1 - \|\mathbf{x}\|^2)^2} \delta_{ij}$ on the open unit ball $\mathbb{B}^d = \{\mathbf{x} \in \mathbb{R}^d : \|\mathbf{x}\| < 1\}$.
- **Exact Riemannian Geodesic Distance**:
  $$d_P(\mathbf{u}, \mathbf{v}) = \operatorname{arcosh}\left(1 + 2 \cdot \frac{\|\mathbf{u} - \mathbf{v}\|^2}{(1 - \|\mathbf{u}\|^2)(1 - \|\mathbf{v}\|^2)}\right)$$
- **Curvature-Driven Branch Pruning**: Eliminates candidate transformation trajectories when geodesic distance $d_P(\mathbf{u}_{\text{cand}}, \mathbf{u}_{\text{target}}) > \tau_{\text{threshold}}$ (e.g. $\tau = 0.40$), discarding degenerate or zero-entropy states in $<0.25\text{ ms}$.
- **Holographic Duality Score**: $S(\mathbf{u}, \mathbf{v}) = \exp(-d_P(\mathbf{u}, \mathbf{v}))$.

## INSTRUCTION

1. **Encode 2D Grid / State to 12D Manifold Space**:
   ```python
   from cohezion.competitions.arc.nexus_manifold_solver import QuadratureNexusEncoder
   encoder = QuadratureNexusEncoder()
   flume_state = encoder.encode_grid(grid)
   ```

2. **Compute Geodesic Distance**:
   ```python
   from cohezion.competitions.arc.poincare_geometric_pruner import PoincareGeometricPruner
   pruner = PoincareGeometricPruner()
   dist = pruner.evaluate_candidate_geodesic(candidate_grid, target_manifold_state)
   ```

3. **Prune Divergent Candidate Branches**:
   ```python
   if dist > 0.40:
       # Prune branch instantly (zero combinatorial expansion)
       return None
   ```

## VERSION
v1.0

## SEE ALSO
- `JACOBIAN_J_SPACE_WORKSPACE_PRIME.md`
- `AUTOHARNESS_AST_VERIFICATION_PRIME.md`
- `HIHO_STABILITY_PROTOCOL_PRIME.md`
