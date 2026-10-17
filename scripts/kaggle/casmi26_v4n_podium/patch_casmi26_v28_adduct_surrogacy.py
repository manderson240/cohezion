#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v28: All-Adduct Surrogacy Calibration + Deep Candidate Expansion.
==================================================================================================
Slot 3 Invariant Hypothesis:
- All-adduct surrogacy calibration ([M+H]+, [M+Na]+, [M-H]- neutral loss matching).
- Candidate space expansion: PC_JOIN_N=85, PC_POP_UNION=275.
- Parsimony calibration: FRAG_LAM=0.20 with ICE_SURROGATE='all'.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")
BAK_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb.v27.bak")


def main() -> None:
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v28-adduct-surrogate-all-frag20-pop22-pcpop25-join85', 'FP_BANK': 'ens', 'POP_MU': 0.22, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 275, 'FRAG_LAM': 0.20, 'FRAG_MODE': 'all', 'ICE_SURROGATE': 'all', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 85, 'PC_JOIN_MAX_LIB': 0.7, 'FILL_25': True})   # upgraded to v28 All-Adduct Surrogacy Calibration"

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

    print("✓ Successfully patched CASMI26 notebook to SOTA v28.")


if __name__ == "__main__":
    main()
