# SKILL: CURVATURE_ADAPTIVE_TTT_PRIME

## DOMAIN EXPERTISE
Curvature-Adaptive Test-Time Training (CA-TTT) and Search-Tree-Weighted Self-Consistency (STWSC) over hyperbolic Poincaré manifolds for zero-shot generalization on Kaggle and sovereign AGI benchmarks.

## KEY TEXTS & CONCEPTS
- **1. Curvature-Adaptive Test-Time Training (CA-TTT)**:
  * Instead of fixing the latent space geometry, the manifold curvature $c < 0$ is a **dynamic, test-time learnable parameter**:
    $$d_P^c(u, v) = \frac{1}{\sqrt{c}} \operatorname{arcosh}\left(1 + \frac{2c \|u - v\|^2}{(1 - c\|u\|^2)(1 - c\|v\|^2)}\right)$$
  * Jointly optimizes curvature $c$ and tiny adapter weights $\Delta W$ on the test sample's self-supervised reconstruction loss.
- **2. Search-Tree-Weighted Self-Consistency (STWSC)**:
  * Replaces naive uniform majority voting with **geodesic manifold cluster weighting**:
    $$w_i = \frac{N(v_i)}{\sum_j N(v_j)} \cdot \exp\left(-\lambda \min_{k \neq i} d_P^c(z_i, z_k)\right)$$
  * Nodes that cluster tightly on the hyperbolic manifold reinforce each other's voting weights.
- **3. Recursive Ensemble-Primed TTT (REP-TTT)**:
  * Adapts weights to minimize the cross-branch entropy of candidate reasoning trajectories before final answer emission.

## INSTRUCTION

1. **Implementing Curvature-Adaptive Poincaré Distance in Python**:
```python
import numpy as np

def poincare_distance_c(u: np.ndarray, v: np.ndarray, c: float = 1.0, eps: float = 1e-5) -> float:
    """Computes conformal Poincaré distance under variable negative curvature c."""
    c = max(1e-4, float(c))
    norm_u = np.sum(u ** 2)
    norm_v = np.sum(v ** 2)
    diff_norm = np.sum((u - v) ** 2)
    
    # Boundary clipping for numerical stability in the open ball ||u|| < 1/sqrt(c)
    max_radius = (1.0 / np.sqrt(c)) - eps
    if norm_u >= max_radius**2 or norm_v >= max_radius**2:
        return 100.0
        
    delta = 1.0 + (2.0 * c * diff_norm) / ((1.0 - c * norm_u) * (1.0 - c * norm_v))
    delta = max(1.0 + eps, delta)
    return float((1.0 / np.sqrt(c)) * np.arccosh(delta))
```

2. **Search-Tree-Weighted Consensus Vote**:
```python
def weighted_hyperbolic_consensus(candidates: list[dict], curvature: float = 1.0) -> str:
    """Weights candidate solutions by hyperbolic density and visit frequencies."""
    scores = {}
    for cand in candidates:
        ans = cand["answer"]
        visits = cand.get("visits", 1)
        z = np.array(cand["embedding"], dtype=np.float32)
        
        # Calculate cluster density weight
        density = sum(
            np.exp(-poincare_distance_c(z, np.array(other["embedding"]), c=curvature))
            for other in candidates
        )
        scores[ans] = scores.get(ans, 0.0) + (visits * density)
        
    return max(scores.items(), key=lambda x: x[1])[0]
```

## VERSION
v1.0

## SEE ALSO
- `KAGGLE_EMBEDDED_WORLD_MODELS_PRIME`
- `KAGGLE_EMBEDDED_AGENT_SWARMS_PRIME`
- `VMODEL_SYSTEMS_ENGINEERING_PRIME`
