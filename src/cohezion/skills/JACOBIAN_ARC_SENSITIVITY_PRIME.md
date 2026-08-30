# SKILL: JACOBIAN_ARC_SENSITIVITY_PRIME

## DOMAIN EXPERTISE
Differential Saliency Mapping, Numerical Jacobian Gradient Sensitivity ($J_{ij} = \|\partial \mathbf{S}_{12D} / \partial x_{ij}\|$), and High-Curvature Structural Pivot Extraction for Discrete Grid Reasoning.

## KEY TEXTS & CONCEPTS
- **Discrete Numerical Jacobian Matrix**:
  $$J_{ij} = \left\| \frac{\mathbf{S}_{12D}(G \oplus \delta_{ij}) - \mathbf{S}_{12D}(G)}{\delta} \right\|_2$$
- **Structural Pivot Cell Identification**: Identifies the top-$K$ grid coordinates with highest Jacobian curvature (corners, boundary hinges, topological enclosures).
- **Differential Search Pruning**: Bypasses static uniform interior fill cells ($\Delta J \approx 0$) to focus 100% of search compute on pivotal topological inflection coordinates.

## INSTRUCTION

1. **Compute Grid Jacobian Sensitivity Map**:
   ```python
   from cohezion.competitions.arc.jacobian_arc_manifold import JacobianARCManifoldEngine
   engine = JacobianARCManifoldEngine()
   j_map = engine.compute_grid_jacobian(grid)
   ```

2. **Extract High-Curvature Pivot Points**:
   ```python
   pivots = engine.extract_salient_pivot_cells(grid, top_k=5)
   for r, c, score in pivots:
       print(f"Pivot ({r}, {c}) with sensitivity {score:.4f}")
   ```

## VERSION
v1.0

## SEE ALSO
- `POINCARE_GEODESIC_SEARCH_PRIME.md`
- `AUTOHARNESS_AST_VERIFICATION_PRIME.md`
