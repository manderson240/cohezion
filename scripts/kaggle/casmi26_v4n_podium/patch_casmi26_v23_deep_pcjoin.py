#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v23: Deep Candidate Injection (PC_JOIN_N 75) + Parsimonious Fragment Rescoring (FRAG_LAM 0.65).

Hypothesis (Theorem E2 Candidate Headroom):
- Expanding PC_JOIN_N from 50 to 75 allows 25 additional popularity-gated natural product candidates
  into the ICEBERG/GLACIER evaluation list.
- Increasing FRAG_LAM from 0.5 to 0.65 increases the weight of MetFrag parsimony, penalizing complex
  synthetic rearrangements that require energetically implausible bond dissociations.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v22.bak")

def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v23-podium-pop25-pcpop25-join75-frag65', 'POP_MU': 0.25, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 200, 'FRAG_LAM': 0.65, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 75, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    lines = c4_source.splitlines()
    updated_lines = []
    found = False
    for line in lines:
        if line.startswith("CFG.update("):
            updated_lines.append(new_update + "   # upgraded to v23 Deep PC Join 75 + FRAG 0.65")
            found = True
        else:
            updated_lines.append(line)
    
    if not found:
        updated_lines.append(new_update + "   # appended v23 Deep PC Join 75")

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

    print("✓ Cell 4 updated with v23 Podium configuration (PC_JOIN_N=75, FRAG_LAM=0.65)")
    print(f"✓ Saved updated notebook to {NB_PATH}")

if __name__ == "__main__":
    main()
