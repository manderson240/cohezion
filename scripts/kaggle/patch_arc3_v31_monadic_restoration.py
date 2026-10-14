#!/usr/bin/env python3
"""Restores ARC-AGI-3 to v31 Monadic Markov Engine.

Root-cause fix:
- Replaces broken v30 global BFS with impassable_colors (which banned floor/wall colors globally)
- Restores proven v27 Directed Rarity Agent with SplitMix64 Zobrist state hashing and 1-cycle/2-cycle/3-6 cycle anti-cycle penalties.
- Keeps local coordinate-delta steering without global constraint pollution.
"""

import ast
import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")
BAK_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb.v30.bak")

import sys
sys.path.insert(0, ".")
from scripts.kaggle.arc3_autoharness_kernel.upgrade_arc3_v27_monadic_sota import generate_cell1_code

def main():
    if NB_PATH.exists():
        shutil.copyfile(NB_PATH, BAK_PATH)
        print(f"Backed up {NB_PATH} to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Replace Cell 1 with v27/v31 Monadic Markov code
    cell1_code = generate_cell1_code()
    nb["cells"][1]["source"] = [l + "\n" for l in cell1_code.splitlines()]

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

    print(f"✓ Successfully restored ARC-AGI-3 to Monadic Markov Engine in {NB_PATH}")

if __name__ == "__main__":
    main()
