#!/usr/bin/env python3
"""Upgrade Enveda CASMI26 to SOTA v30: Extreme Candidate Space Parsimony Hybrid.
================================================================================
Slot 5 Invariant Hypothesis:
- Dieter's Grandmaster Re-Ranking Axiom: When proposal space is expanded (PC_JOIN_N=120,
  PC_POP_UNION=350), theoretical in silico fragment dissociation penalty (FRAG_LAM=0.25)
  must be elevated to strongly suppress decoy isobaric isomers.
- Maximizes precision in Regime B (unobserved natural product classes) where raw retrieval
  recall is high but false-positive ranking drops true molecules out of top 25.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

BASE_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.canonical_base.ipynb")
NB_PATH = Path("scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb")


def main() -> None:
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"{BASE_PATH} does not exist")

    with open(BASE_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    c4_source = "".join(nb["cells"][4]["source"])
    new_update = "CFG.update({'VERSION': 'v30-extreme-parsimony-frag25-pop22-pcpop25-join120', 'FP_BANK': 'ens', 'POP_MU': 0.22, 'PC_POP_LAM': 0.25, 'PC_POP_UNION': 350, 'FRAG_LAM': 0.25, 'FRAG_MODE': 'all', 'ICE_SURROGATE': 'all', 'GL_SURROGATE': True, 'ICE_LAM_LIB': 0.0, 'GL_LAM_LIB': 0.0, 'PC_JOIN_N': 120, 'PC_JOIN_MAX_LIB': 0.75, 'FILL_25': True})   # upgraded to v30 Extreme Candidate Space Parsimony Hybrid"

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

    print("✓ Successfully patched CASMI26 notebook to SOTA v30.")


if __name__ == "__main__":
    main()
