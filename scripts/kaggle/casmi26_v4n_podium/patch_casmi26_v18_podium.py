#!/usr/bin/env python3
"""Patch CASMI26 v4n notebook to v18 Podium SOTA:
- Calibrated Popularity Prior Scaling (POP_MU: 0.42)
- Adduct Surrogate Coverage (ICE_SURROGATE: 'gap')
- MetFrag Parsimony Rescoring (FRAG_LAM: 0.5, FRAG_MODE: 'gap')
- PubChem Injection Regularization (PC_JOIN_N: 50, PC_JOIN_MAX_LIB: 0.7, PC_POP_LAM: 0.0)
- Full 25-slot Candidate Filling (FILL_25: True)
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v17.bak")

def patch():
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Patch Cell 4
    c4 = nb["cells"][4]
    c4_src = "".join(c4["source"])

    old_update = "CFG.update({'VERSION': 'v12a-v4b-pcjoin50-lib07', 'POP_MU': 0.25, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7})"
    new_update = "CFG.update({'VERSION': 'v18-podium-pop42-surrogate', 'POP_MU': 0.42, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    if old_update not in c4_src:
        raise ValueError(f"Could not find target update line in Cell 4:\n{c4_src[-300:]}")

    c4_src = c4_src.replace(old_update, new_update)
    c4["source"] = [line + "\n" for line in c4_src.splitlines()]
    print("✓ Cell 4 updated with v18 Podium configuration")

    # Verify AST across all code cells
    for i, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            # strip IPython magic lines for AST verification
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
    print("✓ Saved updated notebook to", NB_PATH)

if __name__ == "__main__":
    patch()
