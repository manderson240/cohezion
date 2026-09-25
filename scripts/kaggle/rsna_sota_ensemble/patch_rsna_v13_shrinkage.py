#!/usr/bin/env python3
"""Patches cohezion-rsna-knee-sota-ensemble.ipynb to v13 with Calibrated Anatomical Covariance Shrinkage.

Key improvements over v12:
1. Shrinks anatomical covariance weight from aggressive alpha=0.15 down to conservative alpha=0.035.
2. Removes destructive rank(method='average', pct=True) which destroyed probability calibration in v12.
3. Preserves the clean multi-view CoAtNet + Raptor + Global96 SWA3 ensemble that scored 0.943.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")

OLD_SNIPPET = """def _apply_anatomical_covariance(df, labels, alpha=0.15):
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

_blend_output = _apply_anatomical_covariance(_blend_output, _blend_labels, alpha=0.15)"""

NEW_SNIPPET = """def _apply_anatomical_covariance(df, labels, alpha=0.035):
    # Cohezion v13: Calibrated Covariance Shrinkage (alpha=0.035, rank-normalization removed)
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
    # Preserves calibrated probabilities directly without destructive rank-averaging
    return df_cal

_blend_output = _apply_anatomical_covariance(_blend_output, _blend_labels, alpha=0.035)"""


def patch_rsna_v13() -> None:
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Patch Cell 26
    cell_26_src = "".join(nb["cells"][26]["source"])
    if OLD_SNIPPET not in cell_26_src:
        raise ValueError("Could not find OLD_SNIPPET in Cell 26")

    patched_src = cell_26_src.replace(OLD_SNIPPET, NEW_SNIPPET)
    nb["cells"][26]["source"] = [patched_src]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("Successfully patched RSNA notebook to v13 with Calibrated Covariance Shrinkage!")


if __name__ == "__main__":
    patch_rsna_v13()
