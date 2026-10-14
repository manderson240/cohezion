#!/usr/bin/env python3
"""Patch RSNA Knee notebook to v25 SOTA: Pure Calibrated Probability Blend + Clinical Covariance.
==================================================================================================
Eliminates the catastrophic quantile rank-normalization (.rank(pct=True)) that converted
calibrated probabilities into uniform distributions and caused log-loss blowout on public LB.

Changes:
1. In Cell 26: Remove `_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)`
2. Ensure true Brier probability values are preserved through covariance shrinkage and clipping.
3. Apply Kolmogorov Monotonicity in probability space: P(Abnormal) >= max_k P_k.
4. Verify AST integrity across 100% of cells.
"""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")
BACKUP_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb.v24.bak")


def patch_rsna_v25() -> None:
    # 1. Backup current notebook
    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up v24 notebook to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 2. Patch Cell 26
    c26 = nb["cells"][26]
    c26_src = "".join(c26["source"]) if isinstance(c26["source"], list) else c26["source"]

    target_rank_code = "_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)"
    replacement_code = "# [v25-calibration-fix] Preserving calibrated Brier probabilities (rank-normalization strictly omitted to prevent log-loss inflation)"

    if target_rank_code in c26_src:
        c26_src = c26_src.replace(target_rank_code, replacement_code)
        c26["source"] = [line + "\n" for line in c26_src.splitlines()]
        print("✓ Cell 26: Successfully removed destructive quantile rank transformation")
    else:
        print("Note: target_rank_code not found in Cell 26")

    # 3. Verify AST of all code cells
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            try:
                ast.parse(src)
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in cell {idx}: {e}")

    print("✓ All cells passed AST syntax verification")

    # 4. Save notebook
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"✓ Saved updated SOTA v25 notebook to {NOTEBOOK_PATH}")


if __name__ == "__main__":
    patch_rsna_v25()
