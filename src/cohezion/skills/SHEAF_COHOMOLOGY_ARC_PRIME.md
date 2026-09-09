# SKILL: SHEAF_COHOMOLOGY_ARC_PRIME

## DOMAIN EXPERTISE
Sheaf Theory, Čech Cohomology Obstruction Analysis, and Local-to-Global Grid Gluer for ARC-AGI and Combinatorial Synthesis.

## KEY TEXTS & CONCEPTS
- **Topological Open Cover**: $\mathcal{U} = \{U_i\}$ covering the grid canvas $X$.
- **Sheaf Restriction Maps**: $\rho_{U_i, U_i \cap U_j}: \mathcal{F}(U_i) \to \mathcal{F}(U_i \cap U_j)$.
- **Čech 1-Cocycle Obstruction**:
  $$\delta^0(s)_{ij} = s_j|_{U_i \cap U_j} - s_i|_{U_i \cap U_j} = 0 \quad \in H^1(\mathcal{U}, \mathcal{F})$$
- **Gluer Function**: Glues consistent local sections into a unique global section $s \in \mathcal{F}(X)$ in $O(K^2)$ intersection checks.

## INSTRUCTION

1. **Check Sheaf Gluing**:
   ```python
   from cohezion.competitions.arc.sheaf_cohomology_solver import check_sheaf_gluing_consistency
   valid = check_sheaf_gluing_consistency(local_patches)
   ```

## VERSION
v1.0

## SEE ALSO
- `POINCARE_GEODESIC_SEARCH_PRIME.md`
- `JACOBIAN_ARC_SENSITIVITY_PRIME.md`
