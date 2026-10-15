# Entity: Poincaré Hyperbolic Manifold ($\mathbb{D}^n$)

## Abstract
N-dimensional Riemannian manifold $(\mathbb{D}^n, g)$ with constant negative sectional curvature $-1$. Provides an isometry-preserving embedding space for hierarchical decision trees, taxonomic ontologies, and causal DAG state transitions where Euclidean spaces suffer from exponential metric distortion.

## Key Concepts
* **Hyperbolic Metric Tensor:** $g_{ij}(x) = \frac{4}{(1 - \|x\|^2)^2} \delta_{ij}$, scaling infinitely near the boundary $\|x\| \to 1$.
* **Closed-Form Geodesic Distance:**
  $$d_{\mathbb{D}}(u, v) = \text{arcosh}\left(1 + 2 \frac{\|u - v\|^2}{(1 - \|u\|^2)(1 - \|v\|^2)}\right)$$
* **Vectorized Pairwise Broadcasting:** Implemented in double-precision (`float64`) using PyTorch tensor operations and NumPy broadcasting:
  $$\|u - v\|^2 = \|u\|^2 + \|v\|^2 - 2 \langle u, v \rangle$$
* **Tree Capacity:** Hyperbolic volume grows exponentially with radius ($\text{Vol}(r) \propto e^{(n-1)r}$), naturally accommodating branching factor $b^d$ with zero crowding.

## Operational Code
* Implementation: `src/cohezion/physics/poincare_manifold.py`
* Tests: `tests/unit/test_poincare_manifold.py`

## Related Entities
* [[AutoHarness]]
* [[first-principles-invariants]]
* [[Autoresearch]]
