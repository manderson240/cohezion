#!/usr/bin/env python3
"""Patches cohezion-rsna-knee-sota-ensemble.ipynb to v12 with Anatomical Covariance Prior.

Incorporates:
1. Clinical Co-occurrence Covariance Matrix C_ij (Acute Trauma Triad, Degenerative Cascade, Fluid Triad)
2. Logit-domain message passing: excess evidence above baseline prevalence propagates supportive belief.
3. Ranks the anatomically calibrated probabilities before writing submission.csv.
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")
OUTPUT_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble-v12.ipynb")

ANATOMICAL_CALIBRATION_SNIPPET = '''
# --- Cohezion v12: Anatomical Co-occurrence Covariance Calibrator ---
_CLINICAL_COVARIANCE = _ke_np.array([
    # ACL  MCL  MMen LMen MOA  LOA  PFOA Eff  Syn  Bak  Cont Frac
    [1.00, 0.42, 0.38, 0.58, 0.12, 0.15, 0.10, 0.65, 0.35, 0.15, 0.62, 0.18],  # ACL
    [0.42, 1.00, 0.35, 0.25, 0.15, 0.10, 0.08, 0.55, 0.30, 0.12, 0.45, 0.22],  # MCL
    [0.38, 0.35, 1.00, 0.20, 0.55, 0.18, 0.30, 0.50, 0.32, 0.38, 0.35, 0.12],  # Medial Meniscus
    [0.58, 0.25, 0.20, 1.00, 0.18, 0.48, 0.22, 0.52, 0.28, 0.20, 0.52, 0.15],  # Lateral Meniscus
    [0.12, 0.15, 0.55, 0.18, 1.00, 0.32, 0.52, 0.60, 0.42, 0.45, 0.28, 0.10],  # Medial OA
    [0.15, 0.10, 0.18, 0.48, 0.32, 1.00, 0.45, 0.55, 0.38, 0.32, 0.25, 0.10],  # Lateral OA
    [0.10, 0.08, 0.30, 0.22, 0.52, 0.45, 1.00, 0.58, 0.40, 0.35, 0.20, 0.08],  # PF OA
    [0.65, 0.55, 0.50, 0.52, 0.60, 0.55, 0.58, 1.00, 0.68, 0.58, 0.55, 0.35],  # Effusion
    [0.35, 0.30, 0.32, 0.28, 0.42, 0.38, 0.40, 0.68, 1.00, 0.42, 0.30, 0.15],  # Synovitis
    [0.15, 0.12, 0.38, 0.20, 0.45, 0.32, 0.35, 0.58, 0.42, 1.00, 0.18, 0.05],  # Baker's
    [0.62, 0.45, 0.35, 0.52, 0.28, 0.25, 0.20, 0.55, 0.30, 0.18, 1.00, 0.40],  # Contusion
    [0.18, 0.22, 0.12, 0.15, 0.10, 0.10, 0.08, 0.35, 0.15, 0.05, 0.40, 1.00],  # Fracture
], dtype=_ke_np.float64)

def _apply_anatomical_covariance(df, labels, alpha=0.15):
    probs = _ke_np.clip(df[labels].to_numpy(_ke_np.float64), 1e-5, 1.0 - 1e-5)
    logits = _ke_np.log(probs / (1.0 - probs))
    W = _CLINICAL_COVARIANCE.copy()
    _ke_np.fill_diagonal(W, 0.0)
    row_sums = W.sum(axis=1, keepdims=True)
    W_norm = W / _ke_np.maximum(row_sums, 1e-6)
    
    baseline_logit = _ke_np.log(0.15 / 0.85)
    excess_evidence = _ke_np.maximum(0.0, logits - baseline_logit)
    prior_boost = _ke_np.dot(excess_evidence, W_norm.T)
    calibrated_logits = logits + alpha * prior_boost
    calibrated_probs = 1.0 / (1.0 + _ke_np.exp(-calibrated_logits))
    df_cal = df.copy()
    df_cal[labels] = calibrated_probs
    df_cal[labels] = df_cal[labels].rank(method='average', pct=True)
    return df_cal

_blend_output = _apply_anatomical_covariance(_blend_output, _blend_labels, alpha=0.15)
'''


def patch_rsna():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Patch Cell 26
    cell_26_src = "".join(nb["cells"][26]["source"])
    target_needle = "_blend_output.to_csv(_ke_primary, index=False)"
    if target_needle not in cell_26_src:
        raise ValueError("Could not find target line in Cell 26")

    patched_src = cell_26_src.replace(
        target_needle,
        ANATOMICAL_CALIBRATION_SNIPPET + "\n" + target_needle
    )
    nb["cells"][26]["source"] = [patched_src]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"Successfully generated RSNA v12 SOTA notebook at: {OUTPUT_PATH}")


if __name__ == "__main__":
    patch_rsna()
