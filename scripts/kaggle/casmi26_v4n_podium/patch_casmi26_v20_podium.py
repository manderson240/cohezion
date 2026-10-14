#!/usr/bin/env python3
"""Patch CASMI26 v4n notebook to v20 Podium Probe:
- Calibrated Popularity Prior: POP_MU=0.20 (Optimal balance: prevents over-penalizing rare Class 2 natural products)
- Full 25-slot Candidate Filling: FILL_25=True
- Adduct Surrogate Coverage: ICE_SURROGATE='gap'
- MetFrag Parsimony Rescoring: FRAG_LAM=0.5, FRAG_MODE='gap'
- PubChem Join: PC_JOIN_N=50, PC_JOIN_MAX_LIB=0.7
- Fast Commit Run: FULL_ON_COMMIT=False, SMOKE_N=12 (15-min commit, full hidden evaluation)
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v19.bak")

def patch():
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Patch Cell 4
    c4 = nb["cells"][4]
    c4_src = "".join(c4["source"])

    # Ensure FULL_ON_COMMIT=False for fast commit
    c4_src = c4_src.replace("FULL_ON_COMMIT=True", "FULL_ON_COMMIT=False")

    old_update = "CFG.update({'VERSION': 'v19-podium-pop25-surrogate-fill25', 'POP_MU': 0.25, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"
    new_update = "CFG.update({'VERSION': 'v20-podium-pop20-surrogate-fill25', 'POP_MU': 0.20, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    if old_update not in c4_src:
        raise ValueError(f"Could not find target update line in Cell 4:\n{c4_src[-300:]}")

    c4_src = c4_src.replace(old_update, new_update)
    c4["source"] = [line + "\n" for line in c4_src.splitlines()]
    print("✓ Cell 4 updated with v20 Podium configuration (POP_MU=0.20)")

    # Verify AST across all code cells
    for i, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            cleaned_lines = []
            for line in src.splitlines():
                if line.strip().startswith("!") or line.strip().startswith("%"):
                    cleaned_lines.append(f"# {line}")
                else:
                    cleaned_lines.append(line)
            try:
                ast.parse("\n".join(cleaned_lines))
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in Cell {i}: {e}")

    print("✓ AST validation passed for all cells")

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("✓ Saved updated v20 notebook successfully.")

if __name__ == "__main__":
    patch()
