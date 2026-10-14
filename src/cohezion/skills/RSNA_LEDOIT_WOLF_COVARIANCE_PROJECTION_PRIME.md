---
name: rsna-ledoit-wolf-covariance-projection-prime
description: "Wasserstein-2 Monge optimal transport covariance alignment, Ledoit-Wolf shrinkage, and L2 Kolmogorov monotonicity projection for multi-label medical imaging."
version: v0.1
---

# SKILL: RSNA_LEDOIT_WOLF_COVARIANCE_PROJECTION_PRIME

## DOMAIN EXPERTISE
Multi-label biomedical condition ensembling using Gaussian copulas, Ledoit-Wolf empirical shrinkage covariance alignment via Wasserstein-2 Monge maps, and convex Kolmogorov monotonicity projections ($P(\text{Abnormal}) \ge \max_k P_k$) for RSNA Knee MRI and related diagnostic tasks.

## KEY TEXTS & CONCEPTS
* **Intra-Column Quantile Rank Normalization**: Eliminating inter-model calibration bias without warping intra-column ROC-AUC metrics.
* **Ledoit-Wolf Empirical Covariance Shrinkage**: Conditioning high-dimensional label correlation matrices against ill-conditioned sample covariance singular values.
* **Wasserstein-2 Monge Optimal Transport Map**: $A = \hat{\Sigma}^{-1/2} (\hat{\Sigma}^{1/2} \Sigma_t \hat{\Sigma}^{1/2})^{1/2} \hat{\Sigma}^{-1/2}$, aligning test prediction correlation to ground-truth label or OOF geometry.
* **Empirical Quantile Probability Inversion**: Mapping copula-aligned scores back to calibrated probability space via empirical reference quantiles $\hat{Q}_j$.
* **Exact $L_2$ Kolmogorov Monotonicity Projection**: Non-destructive per-row projection onto the convex cone $a \ge \max_k p_k$ in $O(K \log K)$ or $O(K)$ time.

## INSTRUCTION

1. **Quantile Rank Transformation & Blending**:
```python
import numpy as np
from scipy.stats import rankdata, norm

def quantile_rank(x: np.ndarray) -> np.ndarray:
    """Transforms arbitrary continuous scores into uniform (0, 1) ranks."""
    x = np.asarray(x, float)
    return (np.apply_along_axis(rankdata, 0, x) - 0.5) / x.shape[0]

def blend_quantile_models(model_preds: list[np.ndarray], weights: list[float] | None = None) -> np.ndarray:
    if weights is None:
        weights = [1.0 / len(model_preds)] * len(model_preds)
    u_sum = sum(w * quantile_rank(p) for w, p in zip(weights, model_preds))
    return quantile_rank(u_sum)
```

2. **Ledoit-Wolf Covariance Shrinkage**:
```python
def ledoit_wolf(z: np.ndarray) -> tuple[np.ndarray, float]:
    """Computes well-conditioned covariance with optimal analytical shrinkage delta."""
    n, p = z.shape
    zc = z - z.mean(axis=0)
    S = zc.T @ zc / n
    mu = float(np.trace(S) / p)
    d2 = float(np.sum((S - mu * np.eye(p)) ** 2) / p)
    b2 = float((np.sum(np.sum(zc**2, axis=1) ** 2) / n - np.sum(S**2)) / (n * p))
    b2 = min(max(b2, 0.0), d2)
    delta = b2 / d2 if d2 > 0 else 1.0
    sigma_hat = delta * mu * np.eye(p) + (1.0 - delta) * S
    return sigma_hat, delta
```

3. **Wasserstein-2 Monge Covariance Alignment**:
```python
def _psd_pow(A: np.ndarray, power: float) -> np.ndarray:
    w, V = np.linalg.eigh((A + A.T) / 2)
    return (V * np.clip(w, 1e-10, None) ** power) @ V.T

def gaussian_monge_map(sigma_source: np.ndarray, sigma_target: np.ndarray) -> np.ndarray:
    """Computes linear optimal transport operator between zero-mean Gaussians."""
    s_h = _psd_pow(sigma_source, 0.5)
    s_ih = _psd_pow(sigma_source, -0.5)
    return s_ih @ _psd_pow(s_h @ sigma_target @ s_h, 0.5) @ s_ih

def align_predictions_covariance(u_preds: np.ndarray, sigma_target: np.ndarray, lam: float = 0.5) -> np.ndarray:
    """Aligns copula-transformed predictions towards target covariance."""
    Z = norm.ppf(np.clip(u_preds, 1e-5, 1.0 - 1e-5))
    sigma_s, _ = ledoit_wolf(Z)
    A = gaussian_monge_map(sigma_s, sigma_target)
    Z_aligned = (1.0 - lam) * Z + lam * (Z @ A)
    return norm.cdf(Z_aligned)
```

4. **Calibrated Probability Scale Restitution**:
```python
def to_prob_scale(u: np.ndarray, ref_raw_probs: np.ndarray) -> np.ndarray:
    """Inverts uniform rank scores back to calibrated probability scale using empirical quantiles."""
    out = np.empty_like(u)
    for j in range(u.shape[1]):
        out[:, j] = np.quantile(ref_raw_probs[:, j], np.clip(u[:, j], 0.0, 1.0))
    return out
```

5. **Kolmogorov Monotonicity Projection ($L_2$ Convex Cone)**:
```python
def kolmogorov_projection(abnormal: np.ndarray, sub_conditions: np.ndarray, mode: str = "lift", eps: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """
    Projects multi-label predictions onto the Kolmogorov monotonic cone:
    P(Abnormal) >= max_k P(SubCondition_k).
    """
    abn = abnormal.copy()
    sub = sub_conditions.copy()
    max_sub = sub.max(axis=1)

    if mode == "lift":
        # Non-destructive: preserve all sub-condition discriminative power and lift abnormal
        abn = np.maximum(abn, max_sub)
        abn = np.clip(abn + eps * abnormal, 0.0, 1.0)
    elif mode == "joint":
        # Dual projection: jointly minimize ||a - a0||^2 + ||p - p0||^2
        K = sub.shape[1]
        violations = np.where(abn < max_sub)[0]
        for i in violations:
            sorted_p = np.sort(sub[i])[::-1]
            cumsum_p = np.cumsum(sorted_p)
            for j in range(1, K + 1):
                t = (abn[i] + cumsum_p[j - 1]) / (1.0 + j)
                if j == K or t >= sorted_p[j]:
                    abn[i] = t
                    sub[i] = np.minimum(sub[i], t)
                    break

    # Strictly guarantee invariant
    assert np.all(abn >= sub.max(axis=1) - 1e-7), "Kolmogorov Monotonicity Invariant violated!"
    return abn, sub
```

## VERSION
v0.1

## SEE ALSO
- KAGGLE_RANK_ENSEMBLING_CALIBRATION_PRIME.md
- KAGGLE_STRICT_MONOTONIC_ATTEMPT_ENSEMBLE_PRIME.md
- RETROSPECTIVE_SKILL.md
