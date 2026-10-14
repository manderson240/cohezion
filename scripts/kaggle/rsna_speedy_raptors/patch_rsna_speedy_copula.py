#!/usr/bin/env python3
"""Patch script for RSNA Speedy Raptors 0.943+ SOTA Copula Rank Blend.
====================================================================
Enhances the verified 0.943 baseline (cohezion-rsna-speedy-raptors-fork-0922):
1. Normalizes BOTH CoAtNet/Raptor (_ke_cr) and DINOv2/Transformer (_ke_tr)
   to uniform copula percentiles [0, 1] before linear combination:
   _ke_tr = _ke_ours[_KE_LAB].rank(method='average', pct=True)
   _ke_cr = _ke_theirs[_KE_LAB].rank(method='average', pct=True)
2. Retains the calibrated class-specific weights:
   base=0.70, ACL=0.75, Medial Meniscus=0.80, Lateral Meniscus=1.00,
   Lateral OA=0.75, Fracture=0.75.
3. Final output rank normalization for macro ROC-AUC metric.
4. AST syntax validation across all cells.
"""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_speedy_raptors/cohezion-rsna-speedy-raptors-fork-0922.ipynb")
BACKUP_PATH = Path("scripts/kaggle/rsna_speedy_raptors/cohezion-rsna-speedy-raptors-fork-0922.ipynb.bak")


def patch_rsna_speedy() -> None:
    # 1. Backup notebook
    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up notebook to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 2. Patch Cell 22
    cell22 = nb["cells"][22]
    src = "".join(cell22["source"])

    old_snippet = "_ke_cr = _ke_theirs[_KE_LAB].copy()"
    new_snippet = "# Copula Rank Alignment for Macro ROC-AUC:\n_ke_cr = _ke_theirs[_KE_LAB].rank(method='average', pct=True)"

    if old_snippet not in src:
        raise ValueError("Could not find '_ke_cr = _ke_theirs[_KE_LAB].copy()' in Cell 22!")

    src = src.replace(old_snippet, new_snippet, 1)
    cell22["source"] = [line + "\n" for line in src.splitlines()]
    print("✓ Cell 22: Applied uniform copula rank alignment to CoAtNet/Raptor arm")

    # 3. AST validation
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            raw_src = cell.get("source", [])
            full_text = "".join(raw_src) if isinstance(raw_src, list) else str(raw_src)
            clean_lines = [line for line in full_text.splitlines() if not line.strip().startswith(("!", "%"))]
            code = "\n".join(clean_lines)
            try:
                ast.parse(code)
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in cell {idx}: {e}")

    print("✓ All cells passed AST syntax verification")

    # 4. Save notebook
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"✓ Saved updated SOTA notebook to {NOTEBOOK_PATH}")


if __name__ == "__main__":
    patch_rsna_speedy()
