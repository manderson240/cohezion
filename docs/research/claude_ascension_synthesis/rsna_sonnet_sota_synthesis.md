I wrote the algorithm and ran it on synthetic data. The test confirms the monotonicity constraint and that rank order survives. It says nothing about your 0.942 → 0.957 gap, which depends on your real out-of-fold (OOF) predictions.

`★ Insight ─────────────────────────────────────`
- The constraint `P(Abnormal) ≥ max_k P_k` is a per-row convex set, so the projection onto it is exact and cheap. No iterative solver is needed.
- Rank averaging puts every column on a uniform scale, so the abnormal and sub-pathology columns no longer share a probability scale. Applying the constraint in rank space would be meaningless. The fix is to map back to probability scale through a monotone quantile function, then project last.
`─────────────────────────────────────────────────`

## 1. Formulation

Notation: `n` rows, `K=12` sub-pathology columns, `M` models. `p_{ik}` is the sub-pathology score and `a_i` the abnormal score.

**Intra-column quantile rank.** For each model `m` and column `j`:

$$u^{(m)}_{ij}=\frac{\operatorname{rank}^{avg}(s^{(m)}_{ij})-\tfrac12}{n}\in(0,1)$$

Average the models, then re-rank so the ensemble is uniform again:

$$\bar u_{ij}=\operatorname{Q}\!\Big(\tfrac1M\sum_m u^{(m)}_{ij}\Big)$$

This is strictly monotone in each model's score, so per-column AUC is not distorted by calibration differences.

**Gaussian copula and Ledoit-Wolf covariance.** Let `Z = Φ⁻¹(ū)` and `S = ZᵀZ/n`. With `μ = tr(S)/K`, `d² = ‖S−μI‖²_F/K` and `b² = min(d², (1/(n²K))·Σ_i‖z_i z_iᵀ − S‖²_F)`:

$$\hat\Sigma=\delta\,\mu I+(1-\delta)S,\qquad \delta=b^2/d^2$$

**Covariance alignment.** Take the target `Σ_t` as the Ledoit-Wolf covariance of OOF scores, or the labels' latent correlation. The Wasserstein-2 optimal linear map is:

$$A=\hat\Sigma^{-1/2}\big(\hat\Sigma^{1/2}\Sigma_t\hat\Sigma^{1/2}\big)^{1/2}\hat\Sigma^{-1/2},\qquad Z'=(1-\lambda)Z+\lambda ZA$$

`λ∈[0,1]` is tuned on OOF AUC. With `λ=0` the pipeline is exactly rank-preserving per column.

**Return to probability scale.** Use `p̃_{ij} = Q̂_j(Φ(z'_{ij}))`, where `Q̂_j` is the empirical quantile function of the mean raw probability of column `j`. This keeps prevalence and calibration.

**Kolmogorov Monotonicity Projection.** Per row, solve `min ‖x−x₀‖² s.t. a ≥ max_k p_k`.

- **Lift mode (default, non-destructive).** Freeze the sub columns and set `a* = max(a, max_k p_k)`. This is the exact L2 projection. A tie-break `+ε·a₀` keeps lifted rows ordered.
- **Joint mode.** Move `a` and `p` together. For a violating row, sort `p` descending and find the level `t_j=(a₀+Σ_{l≤j}p_(l))/(1+j)` with `p_(j+1) ≤ t_j < p_(j)`. Then `a*=t`, `p*_k=min(p_k,t)`.

## 2. Code (tested)

```python
from __future__ import annotations
import numpy as np
from scipy.stats import rankdata, norm

EPS = 1e-6

def quantile_rank(x):
    x = np.asarray(x, float)
    return (np.apply_along_axis(rankdata, 0, x) - 0.5) / x.shape[0]

def ledoit_wolf(z):
    n, p = z.shape
    zc = z - z.mean(0)
    S = zc.T @ zc / n
    mu = np.trace(S) / p
    d2 = np.sum((S - mu * np.eye(p)) ** 2) / p
    b2 = (np.sum(np.sum(zc**2, 1) ** 2) / n - np.sum(S**2)) / (n * p)
    b2 = min(max(b2, 0.0), d2)
    delta = b2 / d2 if d2 > 0 else 1.0
    return delta * mu * np.eye(p) + (1 - delta) * S, float(delta)

def _psd_pow(A, power):
    w, V = np.linalg.eigh((A + A.T) / 2)
    return (V * np.clip(w, 1e-10, None) ** power) @ V.T

def gaussian_monge_map(Sig_s, Sig_t):
    s_h, s_ih = _psd_pow(Sig_s, .5), _psd_pow(Sig_s, -.5)
    return s_ih @ _psd_pow(s_h @ Sig_t @ s_h, .5) @ s_ih

def to_prob_scale(u, ref_probs):
    out = np.empty_like(u)
    for j in range(u.shape[1]):
        out[:, j] = np.quantile(ref_probs[:, j], np.clip(u[:, j], 0, 1))
    return out

def kolmogorov_projection(abn, sub, mode="lift"):
    abn, sub = abn.copy(), sub.copy()
    m = sub.max(1)
    bad = abn < m
    if mode == "lift":
        a0 = abn.copy()
        abn = np.maximum(np.minimum(1.0, np.maximum(a0, m) + EPS * a0), m)
    elif mode == "joint":
        K = sub.shape[1]
        for i in np.where(bad)[0]:
            ps = np.sort(sub[i])[::-1]; cs = np.cumsum(ps)
            for j in range(1, K + 1):
                t = (abn[i] + cs[j - 1]) / (1 + j)
                if j == K or t >= ps[j]:
                    break
            abn[i] = t
            sub[i] = np.minimum(sub[i], t)
    else:
        raise ValueError(mode)
    return abn, sub, int(bad.sum())

def ensemble(models_sub, models_abn, ref_sub_cov=None, lam=0.0, mode="lift"):
    """models_sub: list of (n,12) raw probs; models_abn: list of (n,). Same rows."""
    U  = quantile_rank(np.mean([quantile_rank(s) for s in models_sub], 0))
    ua = quantile_rank(np.mean([quantile_rank(a[:, None]) for a in models_abn], 0))[:, 0]
    Z = norm.ppf(U)
    Sig, delta = ledoit_wolf(Z)
    if lam > 0 and ref_sub_cov is not None:
        A = gaussian_monge_map(Sig, ref_sub_cov)
        Z = (1 - lam) * Z + lam * (Z - Z.mean(0)) @ A
        Z = (Z - Z.mean(0)) / Z.std(0)
        U = norm.cdf(Z)
    P = to_prob_scale(U, np.mean(models_sub, 0))
    a = to_prob_scale(ua[:, None], np.mean([x[:, None] for x in models_abn], 0))[:, 0]
    a2, P2, nviol = kolmogorov_projection(a, P, mode)
    assert (a2 >= P2.max(1) - 1e-12).all()
    return a2, P2, dict(lw_delta=delta, n_violations=nviol)
```

A copy is at `/tmp/claude/rsna/kmp.py` with a test in `test.py`. It is outside the repo, so nothing was added to the worktree. The two Pyright "possibly unbound `t`" warnings are false positives, since `K≥1` guarantees the loop runs.

## 3. Synthetic test result

I used 4,000 rows, 12 correlated latent pathologies and 3 noisy models, with violations injected into the abnormal score.

| Check | Result |
|---|---|
| Violations after projection (all 4 configs) | 0 |
| Min Spearman vs. the plain mean (`λ=0` / `λ=0.3`) | 0.995 / 0.995 |
| Mean sub-pathology AUC (single → ensemble) | 0.928 → 0.971 |
| Abnormal AUC, lift (single → ensemble) | 0.882 → 0.945 |
| Abnormal AUC, joint | 0.943 |
| `λ=0.3` alignment | +0.0005 sub-AUC, nothing else |

Don't read those AUC gains as a forecast for your leaderboard. The synthetic models have independent noise, which flatters ensembling. The rank-order and constraint results are the part that carries over.

## 4. Failure modes and guards

| Failure mode | Guard |
|---|---|
| Projecting in rank space, where abnormal and sub columns have different prevalence. | Map back to probabilities with `Q̂_j` and project last, after every non-monotone step. |
| Projection ties lifted rows at `m_i`, which flattens ROC ranking. | The `+ε·a₀` tie-break keeps the original order, and the constraint is re-asserted. |
| Covariance alignment is a cross-column linear mix, so it can change per-column ranks. | `λ` defaults to 0. Tune it on OOF AUC and watch min per-column Spearman. |
| The 12×12 covariance is noisy on a small positive class. | Ledoit-Wolf shrinkage, plus eigenvalue clipping in `_psd_pow`. |
| Ties in model outputs. | Average ranks. |
| Joint mode lowers sub-pathology scores, which hurts their AUC. | It is opt-in. Lift mode never touches sub columns. |
| Calibration drift between train and test prevalence. | `Q̂_j` is fitted on the same rows, so it matches prevalence by construction. If the test mix differs, fit it on OOF data instead. |

## 5. The part post-processing can't fix

Rank normalization and the projection can't recover posterior-horn tears lost to volumetric downsampling. Any real gain towards 0.957 has to come from the models: full-resolution ROI crops or tiles around the menisci, fed to the sub-pathology heads. Run this post-processing on top of that. Before you rely on it, check on your OOF data that the violation rate is non-trivial and that lift beats the plain mean.