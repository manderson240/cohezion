#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v24: All-Adduct Surrogate Scoring (ICE_SURROGATE 'all') + Restored Parsimony (FRAG_LAM 0.20, PC_JOIN_N 50).

Empirical Learning from v21 (0.415), v22 (0.414), v23 (0.410):
1. Over-weighting fragmentation (FRAG_LAM=0.65) or over-expanding proposals (PC_JOIN_N=75)
   causes subtle rank distortion due to false-cleavages in complex natural product scaffolds.
2. The core signal boost stems from Dual Popularity (POP_MU=0.25 + PC_POP_LAM=0.25).
3. Switching ICE_SURROGATE from 'gap' to 'all' evaluates [M+NH4]+ and water-loss spectra across
   every candidate group, providing dense orthogonal confirmation for the top-25 rerank.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v23.bak")

def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v24-podium-pop25-pcpop25-surrogate-all-join50-frag20', 'POP_MU': 0.25, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 200, 'FRAG_LAM': 0.20, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'all', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    lines = c4_source.splitlines()
    updated_lines = []
    found = False
    for line in lines:
        if line.startswith("CFG.update("):
            updated_lines.append(new_update + "   # upgraded to v24 Surrogate All + Frag 0.20")
            found = True
        else:
            updated_lines.append(line)
    
    if not found:
        updated_lines.append(new_update + "   # appended v24 Surrogate All")

    nb["cells"][4]["source"] = [l + "\n" for l in updated_lines]

    # Validate AST across all code cells
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            cleaned = []
            for line in src.splitlines():
                if line.strip().startswith("!") or line.strip().startswith("%"):
                    cleaned.append(f"# {line}")
                else:
                    cleaned.append(line)
            try:
                ast.parse("\n".join(cleaned))
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in Cell {idx}: {e}")

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Cell 4 updated with v24 Podium configuration (ICE_SURROGATE='all', FRAG_LAM=0.20, PC_JOIN_N=50)")
    print(f"✓ Saved updated notebook to {NB_PATH}")

if __name__ == "__main__":
    main()
