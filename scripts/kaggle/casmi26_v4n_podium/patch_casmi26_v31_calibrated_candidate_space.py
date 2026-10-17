#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v31: Calibrated Candidate Space Parsimony.
================================================================================
Slot 2 Invariant Hypothesis:
- Calibrated equilibrium between retrieval proposal coverage and parsimony penalty:
  PC_JOIN_N = 90 (expanded candidate pool), PC_POP_UNION = 280, FRAG_LAM = 0.19.
- Prevents over-penalization of true natural product structures while dampening isobaric decoys.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.canonical_base.ipynb")
NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")


def main() -> None:
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"{BASE_PATH} does not exist")

    with open(BASE_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v31-calibrated-parsimony-frag19-pop22-pcpop25-join90', 'FP_BANK': 'ens', 'POP_MU': 0.22, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 280, 'FRAG_LAM': 0.19, 'FRAG_MODE': 'all', 'ICE_SURROGATE': 'all', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 90, 'PC_JOIN_MAX_LIB': 0.75, 'FILL_25': True})   # upgraded to v31 Calibrated Candidate Space Parsimony"

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
        raise RuntimeError("CFG.update line not found in cell 4 of canonical base notebook!")

    nb["cells"][4]["source"] = [l + "\n" for l in updated_lines]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched CASMI26 notebook to SOTA v31.")


if __name__ == "__main__":
    main()
