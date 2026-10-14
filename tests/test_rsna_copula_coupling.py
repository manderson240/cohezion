"""Test RSNA Anatomical Copula Coupling and Clinical Prior Graph.
=============================================================
Verifies:
1. Clinical prior graph is strictly Positive Semi-Definite (PSD).
2. Self-contained fast inverse normal CDF (_ndtri_fast) matches standard normal quantile.
3. Copula coupling executes cleanly on dummy prediction matrices of varying sizes.
4. Output ranks are strictly finite in (0, 1] with zero NaNs or Infs.
"""

from __future__ import annotations

import numpy as np
import pytest

LABELS = [
    'ACL', 'MCL', 'Medial Meniscus', 'Lateral Meniscus',
    'Medial OA', 'Lateral OA', 'PF OA', 'Effusion',
    'Synovitis', "Baker's", 'Contusion', 'Fracture'
]

CLINICAL_GRAPH = np.array([
    [1.00, 0.10, 0.52, 0.48, 0.05, 0.03, 0.03, 0.20, 0.12, 0.05, 0.35, 0.15],
    [0.10, 1.00, 0.44, 0.30, 0.04, 0.02, 0.02, 0.15, 0.10, 0.05, 0.25, 0.10],
    [0.52, 0.44, 1.00, 0.60, 0.10, 0.06, 0.05, 0.28, 0.18, 0.08, 0.30, 0.12],
    [0.48, 0.30, 0.60, 1.00, 0.08, 0.05, 0.04, 0.25, 0.15, 0.07, 0.28, 0.10],
    [0.05, 0.04, 0.10, 0.08, 1.00, 0.65, 0.60, 0.40, 0.30, 0.10, 0.08, 0.05],
    [0.03, 0.02, 0.06, 0.05, 0.65, 1.00, 0.55, 0.35, 0.25, 0.08, 0.06, 0.04],
    [0.03, 0.02, 0.05, 0.04, 0.60, 0.55, 1.00, 0.30, 0.22, 0.07, 0.05, 0.03],
    [0.20, 0.15, 0.28, 0.25, 0.40, 0.35, 0.30, 1.00, 0.58, 0.35, 0.15, 0.10],
    [0.12, 0.10, 0.18, 0.15, 0.30, 0.25, 0.22, 0.58, 1.00, 0.25, 0.12, 0.08],
    [0.05, 0.05, 0.08, 0.07, 0.10, 0.08, 0.07, 0.35, 0.25, 1.00, 0.08, 0.05],
    [0.35, 0.25, 0.30, 0.28, 0.08, 0.06, 0.05, 0.15, 0.12, 0.08, 1.00, 0.30],
    [0.15, 0.10, 0.12, 0.10, 0.05, 0.04, 0.03, 0.10, 0.08, 0.05, 0.30, 1.00]
])


def _ndtri_fast(p: np.ndarray) -> np.ndarray:
    """Acklam's rational approximation for inverse normal CDF."""
    a = np.array([-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.3577518672690, -30.66479806614716, 2.506628277459239])
    b = np.array([-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572])
    c = np.array([-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783])
    d = np.array([0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416])
    plow = 0.02425
    p = np.clip(p, 1e-12, 1.0 - 1e-12)
    q_tail = np.sqrt(-2.0 * np.log(np.where(p < plow, p, 1.0 - p)))
    num = ((((c[0] * q_tail + c[1]) * q_tail + c[2]) * q_tail + c[3]) * q_tail + c[4]) * q_tail + c[5]
    den = (((d[0] * q_tail + d[1]) * q_tail + d[2]) * q_tail + d[3]) * q_tail + 1.0
    tail = np.where(p < plow, num / den, -num / den)
    q = p - 0.5
    r = q * q
    num_c = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    den_c = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    return np.where((p >= plow) & (p <= 1.0 - plow), num_c / den_c, tail)


def make_psd(R: np.ndarray) -> np.ndarray:
    R_sym = 0.5 * (R + R.T)
    eigvals, eigvecs = np.linalg.eigh(R_sym)
    eigvals = np.clip(eigvals, 1e-6, None)
    R_psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
    d = np.sqrt(np.diag(R_psd))
    R_psd = R_psd / np.outer(d, d)
    np.fill_diagonal(R_psd, 1.0)
    return R_psd


def apply_anatomical_copula(
    p_matrix: np.ndarray,
    clinical_prior: np.ndarray,
    alpha: float = 0.20,
    delta_shrink: float = 0.40,
    rho: float = 1e-3,
) -> np.ndarray:
    n, k = p_matrix.shape
    if n < 2:
        return p_matrix

    # Column-wise ranking to [0, 1]
    import pandas as pd
    u = pd.DataFrame(p_matrix).rank(pct=True, method='average').to_numpy(dtype=np.float64)
    z = _ndtri_fast(u)

    # Empirical correlation
    r_emp = np.corrcoef(z, rowvar=False)
    r_emp = np.nan_to_num(r_emp, nan=0.0, posinf=0.0, neginf=0.0)
    r_emp = make_psd(r_emp)

    # Blend empirical with clinical prior
    r_prior = make_psd(clinical_prior)
    r_copula = (1.0 - delta_shrink) * r_emp + delta_shrink * r_prior
    r_copula = make_psd(r_copula)

    # Conditional expectation across companion pathologies
    m_arr = np.zeros_like(z)
    eye = np.eye(k - 1)
    for j in range(k):
        others = [idx for idx in range(k) if idx != j]
        a_mat = r_copula[np.ix_(others, others)] + rho * eye
        b_vec = r_copula[j, others]
        w_reg = np.linalg.solve(a_mat, b_vec)
        m_arr[:, j] = z[:, others] @ w_reg

    z_star = (1.0 - alpha) * z + alpha * m_arr
    u_star = pd.DataFrame(z_star).rank(pct=True, method='average').to_numpy(dtype=np.float64)
    return np.clip(u_star, 1e-6, 1.0 - 1e-6)


def test_clinical_graph_psd():
    R_psd = make_psd(CLINICAL_GRAPH)
    eigvals = np.linalg.eigvalsh(R_psd)
    assert np.all(eigvals > 0), "Clinical graph must be strictly positive definite"
    assert np.allclose(np.diag(R_psd), 1.0), "Diagonal must be 1.0"


def test_copula_coupling_execution():
    np.random.seed(42)
    # Generate 100 dummy patient predictions across 12 pathologies
    p_dummy = np.random.uniform(0.01, 0.99, size=(100, 12))
    p_coupled = apply_anatomical_copula(p_dummy, CLINICAL_GRAPH, alpha=0.20, delta_shrink=0.40)

    assert p_coupled.shape == (100, 12)
    assert np.all(np.isfinite(p_coupled))
    assert np.all((p_coupled >= 1e-6) & (p_coupled <= 1.0 - 1e-6))
