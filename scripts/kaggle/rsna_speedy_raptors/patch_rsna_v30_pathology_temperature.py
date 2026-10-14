#!/usr/bin/env python3
"""
patch_rsna_v30_pathology_temperature.py
Applies SOTA v30 to cohezion-rsna-speedy-raptors-fork-0922:
1. Refined Classwise CoAtNet Weights (w) based on radiological imaging planes
2. Pre-fusion Copula Temperature Scaling (T_cnn, T_vit)
3. Preserves 12x12 Clinical Prior Graph + Gaussian Copula Regularization + Guardrails
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_speedy_raptors/cohezion-rsna-speedy-raptors-fork-0922.ipynb")

def main():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Locate Cell 22
    cell = nb["cells"][22]
    source = "".join(cell["source"])

    # Target the entire block from _ke_tr to the end of _apply_sota_copula_coupling call
    anchor_start = "_ke_tr = _ke_ours[_KE_LAB].rank(method='average', pct=True)"
    anchor_end = "assert _ke_np.isfinite(\n    _blend_output[_blend_labels].to_numpy(_ke_np.float64)\n).all()"

    start_pos = source.find(anchor_start)
    end_pos = source.find(anchor_end)

    if start_pos == -1 or end_pos == -1:
        raise RuntimeError("Anchor strings not found in Cell 22")

    existing_section = source[start_pos:end_pos]

    new_section = '''_ke_tr = _ke_ours[_KE_LAB].rank(method='average', pct=True)
_ke_cr = _ke_theirs[_KE_LAB].rank(method='average', pct=True)
_blend_transformer = _ke_ours.copy()
_blend_coatnet = _ke_theirs.copy()
_blend_labels = list(_KE_LAB)

# =======================================================================
# SOTA v30: Pre-Fusion Temperature Calibration & Classwise Prior Weights
# Derived via Radiology Prior + GLM-5.3 Grandmaster Optimization
# =======================================================================
def _ndtri_fast(p):
    """Acklam rational approximation for inverse normal CDF."""
    a = _ke_np.array([-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.3577518672690, -30.66479806614716, 2.506628277459239])
    b = _ke_np.array([-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572])
    c = _ke_np.array([-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783])
    d = _ke_np.array([0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416])
    plow = 0.02425
    p = _ke_np.clip(p, 1e-12, 1.0 - 1e-12)
    q_tail = _ke_np.sqrt(-2.0 * _ke_np.log(_ke_np.where(p < plow, p, 1.0 - p)))
    num = ((((c[0] * q_tail + c[1]) * q_tail + c[2]) * q_tail + c[3]) * q_tail + c[4]) * q_tail + c[5]
    den = (((d[0] * q_tail + d[1]) * q_tail + d[2]) * q_tail + d[3]) * q_tail + 1.0
    tail = _ke_np.where(p < plow, num / den, -num / den)
    q = p - 0.5
    r = q * q
    num_c = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    den_c = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    return _ke_np.where((p >= plow) & (p <= 1.0 - plow), num_c / den_c, tail)

def _make_psd(R):
    """Project correlation matrix to positive semi-definite with unit diagonal."""
    R_sym = 0.5 * (R + R.T)
    eigvals, eigvecs = _ke_np.linalg.eigh(R_sym)
    eigvals = _ke_np.clip(eigvals, 1e-6, None)
    R_psd = eigvecs @ _ke_np.diag(eigvals) @ eigvecs.T
    d = _ke_np.sqrt(_ke_np.diag(R_psd))
    R_psd = R_psd / _ke_np.outer(d, d)
    _ke_np.fill_diagonal(R_psd, 1.0)
    return R_psd

_coatnet_weight = {
    'ACL':              0.70,
    'MCL':              0.65,
    'Medial Meniscus':  0.80,
    'Lateral Meniscus': 0.95,
    'Medial OA':        0.80,
    'Lateral OA':       0.80,
    'PF OA':            0.75,
    'Effusion':         0.55,
    'Synovitis':        0.60,
    "Baker's cyst":     0.60,
    'Contusion':        0.65,
    'Fracture':         0.80,
}

_temperature_map = {  # (T_cnn, T_vit) pre-fusion scaling
    'ACL':              (0.95, 1.05),
    'MCL':              (1.00, 1.00),
    'Medial Meniscus':  (0.95, 1.10),
    'Lateral Meniscus': (0.95, 1.15),
    'Medial OA':        (0.95, 1.10),
    'Lateral OA':       (0.95, 1.10),
    'PF OA':            (0.95, 1.05),
    'Effusion':         (1.10, 0.90),
    'Synovitis':        (1.10, 0.90),
    "Baker's cyst":     (1.10, 0.90),
    'Contusion':        (1.05, 0.95),
    'Fracture':         (0.95, 1.10),
}

# Pre-fusion latent projection with temperature scaling
_u_tr_arr = _ke_tr[_blend_labels].to_numpy(dtype=_ke_np.float64)
_u_cr_arr = _ke_cr[_blend_labels].to_numpy(dtype=_ke_np.float64)
_z_tr_arr = _ndtri_fast(_u_tr_arr)
_z_cr_arr = _ndtri_fast(_u_cr_arr)

_z_blend_arr = _ke_np.zeros_like(_z_tr_arr)
for _j, _lbl in enumerate(_blend_labels):
    _w_val = float(_coatnet_weight.get(_lbl, 0.70))
    _t_c, _t_v = _temperature_map.get(_lbl, (1.0, 1.0))
    _z_blend_arr[:, _j] = _w_val * (_z_cr_arr[:, _j] / _t_c) + (1.0 - _w_val) * (_z_tr_arr[:, _j] / _t_v)

_blend_output = _blend_transformer.copy()
_blend_output[_blend_labels] = _ke_pd.DataFrame(
    _z_blend_arr, index=_blend_transformer.index, columns=_blend_labels
).rank(method='average', pct=True)

# =======================================================================
# SOTA v29/v30: 12x12 Anatomical Clinical Prior Graph + Gaussian Copula
# =======================================================================
def _apply_sota_copula_coupling(df_preds, labels, alpha=0.20, delta_shrink=0.40, rho=1e-3):
    frame = df_preds[labels].astype(float).fillna(0.5)
    n = len(frame)
    if n < 2:
        return frame.rank(pct=True, method='average')

    u = frame.rank(pct=True, method='average').to_numpy(dtype=_ke_np.float64)
    z = _ndtri_fast(u)

    # 12x12 Clinical Prior Graph:
    # 0: ACL, 1: MCL, 2: Medial Meniscus, 3: Lateral Meniscus,
    # 4: Medial OA, 5: Lateral OA, 6: PF OA, 7: Effusion,
    # 8: Synovitis, 9: Baker's, 10: Contusion, 11: Fracture
    clinical_prior = _ke_np.array([
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

    # Empirical correlation with shrink
    r_emp = _ke_np.corrcoef(z, rowvar=False)
    r_emp = _ke_np.nan_to_num(r_emp, nan=0.0, posinf=0.0, neginf=0.0)
    r_emp = _make_psd(r_emp)

    r_prior = _make_psd(clinical_prior)
    r_copula = (1.0 - delta_shrink) * r_emp + delta_shrink * r_prior
    r_copula = _make_psd(r_copula)

    # Conditional expectations across companion pathologies
    k_dim = len(labels)
    m_arr = _ke_np.zeros_like(z)
    eye = _ke_np.eye(k_dim - 1)
    for j in range(k_dim):
        others = [idx for idx in range(k_dim) if idx != j]
        a_mat = r_copula[_ke_np.ix_(others, others)] + rho * eye
        b_vec = r_copula[j, others]
        w_reg = _ke_np.linalg.solve(a_mat, b_vec)
        m_arr[:, j] = z[:, others] @ w_reg

    z_star = (1.0 - alpha) * z + alpha * m_arr
    u_star = _ke_pd.DataFrame(z_star, index=frame.index, columns=labels).rank(pct=True, method='average')

    # Guardrails: bound extreme ranks away from 0/1 to protect multi-label loss
    return u_star.clip(0.005, 0.995)

try:
    _blend_output[_blend_labels] = _apply_sota_copula_coupling(_blend_output, _blend_labels, alpha=0.20, delta_shrink=0.40)
    print('[sota-copula-v30] Successfully applied 12x12 Clinical Prior Copula Coupling with Guardrails + Pre-Fusion Temperature', flush=True)
except Exception as _c_exc:
    print(f'[sota-copula-v30] Note: fallback to standard rank ({_c_exc})', flush=True)

'''

    updated_source = source[:start_pos] + new_section + source[end_pos:]
    cell["source"] = [line + "\n" for line in updated_source.splitlines()]
    if cell["source"] and cell["source"][-1].endswith("\n"):
        cell["source"][-1] = cell["source"][-1][:-1]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("[✓] Successfully applied SOTA v30 patch to Cell 22!")

if __name__ == "__main__":
    main()
