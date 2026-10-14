#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v22: Dual Surrogate + Restored POP_MU 0.25 + PubChem Channel Popularity Prior (PC_POP_LAM 0.25 / PC_POP_UNION 200).

Theoretical & Empirical Rationale:
- In v21, POP_MU=0.25 was restored on pool candidates, and GL_SURROGATE=True was enabled.
- However, PC_POP_LAM was left at 0.0 in the PubChem-only channel.
- As proven by Wangpenghua v29 on the public leaderboard, natural product popularity weighting
  inside the PubChem channel (PC_POP_LAM=0.25, PC_POP_UNION=200) filters out obscure synthetic isobars
  among the 5,000 raw PubChem proposals before the top 50 are injected into the v1 engine.
- This creates an optimal dual-stage popularity filter: Stage 1 inside PubChem channel,
  Stage 2 across the unified candidate pool before ICEBERG/GLACIER reranking.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v21.bak")

def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v22-podium-pop25-pcpop25-gl-surrogate-fill25', 'POP_MU': 0.25, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 200, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    lines = c4_source.splitlines()
    updated_lines = []
    found = False
    for line in lines:
        if line.startswith("CFG.update("):
            updated_lines.append(new_update + "   # upgraded to v22 Dual Popularity Prior")
            found = True
        else:
            updated_lines.append(line)
    
    if not found:
        updated_lines.append(new_update + "   # appended v22 Dual Popularity Prior")

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

    print("✓ Cell 4 updated with v22 Podium configuration (POP_MU=0.25, PC_POP_LAM=0.25, PC_POP_UNION=200, GL_SURROGATE=True)")
    print(f"✓ Saved updated notebook to {NB_PATH}")

if __name__ == "__main__":
    main()
