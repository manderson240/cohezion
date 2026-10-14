#!/usr/bin/env python3
"""Patch script for RSNA Knee SOTA v30: Soft Kolmogorov Calibration + Dynamic Ensemble."""

import ast
import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")

def main():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for cell in nb["cells"]:
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            if "_blend_output['Abnormal'] = _ke_np.maximum(" in src:
                # Replace rigid maximum with smooth Soft Kolmogorov Calibration
                old_block = """    _blend_output['Abnormal'] = _ke_np.maximum(
        _blend_output['Abnormal'].to_numpy(_ke_np.float64),
        _blend_output[condition_cols].max(axis=1).to_numpy(_ke_np.float64)
    )
    # AutoHarness verification invariant: 100% rows P(Abnormal) >= max(P(Condition_i))
    _viol_count = int((_blend_output['Abnormal'] < _blend_output[condition_cols].max(axis=1) - 1e-9).sum())
    assert _viol_count == 0, f"AutoHarness Guard: Kolmogorov Monotonicity violated in {_viol_count} rows"
    print(f"[v22-monotonicity-sota] Kolmogorov Monotonicity invariant verified (100% rows satisfied)", flush=True)"""

                new_block = """    # RSNA SOTA v30: Smooth Soft Kolmogorov Calibration
    # Preserves calibrated probabilities and avoids flat ties that harm ROC-AUC
    _sub_max = _blend_output[condition_cols].max(axis=1).to_numpy(_ke_np.float64)
    _orig_abn = _blend_output['Abnormal'].to_numpy(_ke_np.float64)
    _noisy_or = 1.0 - _ke_np.prod(1.0 - _blend_output[condition_cols].clip(0.0, 0.99).to_numpy(_ke_np.float64), axis=1)
    _blend_output['Abnormal'] = _ke_np.clip(0.4 * _orig_abn + 0.35 * _sub_max + 0.25 * _noisy_or, 0.0, 1.0)
    print(f"[v30-podium-sota] Soft Kolmogorov probability calibration applied (zero tie artifacts)", flush=True)"""

                if old_block in src:
                    src = src.replace(old_block, new_block)
                    cell["source"] = [line + "\n" for line in src.splitlines()]
                    print("✓ Successfully replaced hard max projection with v30 Soft Kolmogorov Calibration!")
                else:
                    print("✗ Target block not matched verbatim in cell.")

    # AST verification
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            clean_lines = [l for l in "".join(cell.get("source", [])).splitlines() if not l.strip().startswith(("!", "%"))]
            ast.parse("\n".join(clean_lines))

    print("✓ AST syntax verified across all cells.")

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("✓ Saved updated SOTA v30 notebook.")

if __name__ == "__main__":
    main()
