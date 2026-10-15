#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v27: Deep PubChem Candidate Expansion (PC_JOIN_N 75, PC_POP_UNION 250) + Calibrated Parsimony (FRAG_LAM 0.18).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v26.bak")


def main() -> None:
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v27-podium-ens-frag18-pop25-pcpop25-surrogate-all-join75', 'FP_BANK': 'ens', 'POP_MU': 0.25, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 250, 'FRAG_LAM': 0.18, 'FRAG_MODE': 'all', 'ICE_SURROGATE': 'all', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 75, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})   # upgraded to v27 Deep PubChem Expansion + Calibrated Parsimony"

    lines = c4_source.splitlines()
    updated_lines = []
    found = False
    for line in lines:
        if line.startswith("CFG.update("):
            updated_lines.append(new_update)
            found = True
        else:
            updated_lines.append(line)

    if not found:
        updated_lines.append(new_update)

    nb["cells"][4]["source"] = [l + "\n" for l in updated_lines]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched CASMI26 notebook to SOTA v27.")


if __name__ == "__main__":
    main()
