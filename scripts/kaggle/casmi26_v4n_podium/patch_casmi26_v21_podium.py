#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v21: Dual Surrogate Coverage (GL_SURROGATE + ICE_SURROGATE) + Restored POP_MU 0.25.

Mathematical and Empirical Rationale:
- In v19 (Ref 57007704), POP_MU=0.25 scored 0.415 MRR (vs 0.407 at 0.42 and 0.409 at 0.20),
  confirming POP_MU=0.25 as the empirical sweet spot for natural product popularity weighting.
- In v19/v20, GL_SURROGATE was False, preventing GLACIER from scoring molecules whose only
  available spectra are [M+NH4]+ or [M-H2O+H]+ water-loss adducts.
- In v21, enabling GL_SURROGATE=True extends dual-engine reranking across both ICEBERG and GLACIER
  while preserving the 0.415 POP_MU=0.25 anchor and FILL_25 completeness.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v20.bak")

def main():
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")
    
    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    old_update = "CFG.update({'VERSION': 'v20-podium-pop20-surrogate-fill25', 'POP_MU': 0.20, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"
    new_update = "CFG.update({'VERSION': 'v21-podium-pop25-gl-surrogate-fill25', 'POP_MU': 0.25, 'FRAG_LAM': 0.5, 'FRAG_MODE': 'gap', 'ICE_SURROGATE': 'gap', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 50, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})"

    if old_update not in c4_source:
        # Fallback to replacing any trailing CFG.update
        lines = c4_source.splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith("CFG.update("):
                updated_lines.append(new_update + "   # upgraded to v21 Dual Surrogate")
            else:
                updated_lines.append(line)
        nb["cells"][4]["source"] = [l + "\n" for l in updated_lines]
    else:
        c4_source = c4_source.replace(old_update, new_update)
        nb["cells"][4]["source"] = [l + "\n" for l in c4_source.splitlines()]

    # Validate AST
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

    print("✓ Cell 4 updated with v21 Podium configuration (POP_MU=0.25 + GL_SURROGATE=True)")
    print(f"✓ Saved updated notebook to {NB_PATH}")

if __name__ == "__main__":
    main()
