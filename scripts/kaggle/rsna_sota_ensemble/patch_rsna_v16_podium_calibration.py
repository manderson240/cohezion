#!/usr/bin/env python3
"""Patches cohezion-rsna-knee-sota-ensemble.ipynb to v16 SOTA Podium Calibration.

Root Cause Analysis from Adversarial Review & Leaderboard Feedback:
- v15 dropped from 0.943 to 0.941 because greedy Kolmogorov max on Abnormal
  P(Abnormal) = max(P_Abnormal, max_k P_k) injected false positive condition noise
  into normal healthy knees, degrading the per-label ROC-AUC of Abnormal!
- In v16:
  1. Restores dedicated calibrated ensemble head for 'Abnormal' (removes greedy max).
  2. Preserves finding-specific CoAtNet-vs-Transformer weighting (Fracture=0.85, Meniscus=1.00, etc.).
  3. Uses conservative anatomical covariance shrinkage (alpha=0.035).
  4. Removes rank-normalization; preserves calibrated continuous probabilities.
  5. Enforces class-conditional margin clipping [0.005, 0.965] on rare conditions.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")

V16_REPLACEMENT = """# --- Cohezion v16 SOTA: Finding-Specific Optimal Calibration (Greedy Max Removed) ---
# 1. Finding-specific CoAtNet-vs-Transformer weighting based on spatial scale:
_coatnet_weight = {label: 0.60 for label in _blend_labels}
_coatnet_weight.update({
    'Lateral Meniscus': 1.00,
    'Medial Meniscus': 0.85,
    'ACL': 0.75,
    'MCL': 0.70,
    'Fracture': 0.85,
    'Medial OA': 0.80,
    'Lateral OA': 0.80,
    'PF OA': 0.80,
    'Contusion': 0.75,
    'Effusion': 0.40,
    'Synovitis': 0.40,
    'Baker\\'s': 0.40,
    'Abnormal': 0.65,
})

_blend_output = _blend_transformer.copy()
for _blend_label in _blend_labels:
    _blend_w = float(_coatnet_weight.get(_blend_label, 0.60))
    z_tr = _to_logit(_blend_tr[_blend_label].to_numpy(_ke_np.float64))
    z_cr = _to_logit(_blend_cr[_blend_label].to_numpy(_ke_np.float64))
    _blend_output[_blend_label] = _from_logit((1.0 - _blend_w) * z_tr + _blend_w * z_cr)

# 2. Conservative Anatomical Covariance Shrinkage (alpha=0.035, greedy max removed)
# Preserves dedicated Abnormal classifier integrity while sharing mild clinical cross-evidence
def _apply_conservative_covariance(df, labels, alpha=0.035):
    probs = _ke_np.clip(df[labels].to_numpy(_ke_np.float64), 1e-4, 1.0 - 1e-4)
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
    return df_cal

_blend_output = _apply_conservative_covariance(_blend_output, _blend_labels, alpha=0.035)

# 3. Class-conditional prevalence margin clipping (tight on rare conditions)
_prevalences = {
    'ACL': 0.20, 'MCL': 0.15, 'Medial Meniscus': 0.40, 'Lateral Meniscus': 0.25,
    'Medial OA': 0.35, 'Lateral OA': 0.25, 'PF OA': 0.30,
    'Effusion': 0.50, 'Synovitis': 0.20, 'Baker\\'s': 0.15,
    'Contusion': 0.25, 'Fracture': 0.05, 'Abnormal': 0.78
}
for col in _blend_labels:
    pi = _prevalences.get(col, 0.25)
    eps_low = max(1e-4, pi / 8.0)
    eps_high = 1.0 - (0.025 if col in ('Fracture', 'Tendon') else 0.005)
    _blend_output[col] = _blend_output[col].clip(eps_low, eps_high)

assert _ke_np.isfinite(_blend_output[_blend_labels].to_numpy(_ke_np.float64)).all(), "non-finite outputs"
print(f"[v16-podium-calibration] generated calibrated blend on {_blend_labels} without greedy max", flush=True)
_blend_output.to_csv(_ke_primary, index=False)
"""


def patch_rsna_v16() -> None:
    print(f"[RSNA V16] Loading {NOTEBOOK_PATH}...")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    patched = False
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "_coatnet_weight = {label: 0.60 for label in _blend_labels}" in src:
            pre_code = src.split("_coatnet_weight = {label: 0.60 for label in _blend_labels}")[0]
            new_source = pre_code.rstrip() + "\n\n" + V16_REPLACEMENT
            cell["source"] = [line + "\n" for line in new_source.splitlines()]
            patched = True
            break

    if not patched:
        raise ValueError("Could not find blend cell in RSNA notebook!")

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"[RSNA V16] Successfully patched {NOTEBOOK_PATH} with v16 SOTA Podium Calibration!")


if __name__ == "__main__":
    patch_rsna_v16()
