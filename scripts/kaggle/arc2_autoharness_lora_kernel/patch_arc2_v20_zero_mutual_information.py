#!/usr/bin/env python3
"""Patch script for ARC-AGI-2 SOTA v20: Zero-Mutual-Information Attempt-2 Protocol.
====================================================================================
Maximizes Top-2 Union Pass Rate P(A1 U A2) = P(A1) + P(~A1)*P(A2 | ~A1).
1. Unconditional Symbolic DSL Priority for Attempt-2.
2. Strict Hash & Hamming Barrier: Rejects attempt_2 if identical or < 8% pixel diff from attempt_1.
3. D4 Dihedral Orbit & Topological Fill Fallback when neural beam collapses.
4. AST Syntax verified across all cells.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
from pathlib import Path


NOTEBOOK_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb")
BACKUP_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb.v19.bak")


def main() -> None:
    if not NOTEBOOK_PATH.exists():
        raise FileNotFoundError(f"{NOTEBOOK_PATH} does not exist")

    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up {NOTEBOOK_PATH} -> {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    # Patch Cell 9 (post-processing & formatting)
    cell9 = nb["cells"][9]
    src = "".join(cell9["source"])

    # Update version header
    src = re.sub(
        r"\[AutoHarness SOTA v[0-9]+[^\]]*\]",
        "[AutoHarness SOTA v20 (Zero-MI Attempt-2)]",
        src,
    )

    # Add Zero-Mutual-Information Attempt-2 Helper if not present
    zero_mi_helper = """
def enforce_zero_mutual_information_attempt2(a1, a2, test_in, dsl_sol=None, fixed_shape=None, mode_color=0):
    \"\"\"Enforces strict non-duplication and >=8% Hamming barrier on attempt_2 (SOTA v20).\"\"\"
    import numpy as np

    def grid_hash(g):
        return tuple(tuple(r) for r in g) if isinstance(g, list) and g and isinstance(g[0], list) else None

    def hamming_dist(g1, g2):
        if not isinstance(g1, list) or not isinstance(g2, list):
            return 1.0
        if len(g1) != len(g2) or not g1 or not g2 or len(g1[0]) != len(g2[0]):
            return 1.0
        h, w = len(g1), len(g1[0])
        diffs = sum(1 for r in range(h) for c in range(w) if g1[r][c] != g2[r][c])
        return diffs / float(h * w)

    # 1. If DSL solution exists and differs from a1, prioritize it
    if dsl_sol is not None and grid_hash(dsl_sol) != grid_hash(a1):
        return dsl_sol

    # 2. If a2 is valid, distinct, and satisfies the 8% Hamming barrier, keep it
    if a2 is not None and grid_hash(a2) != grid_hash(a1) and hamming_dist(a1, a2) >= 0.08:
        return a2

    # 3. Fallback: Search D4 Dihedral Symmetry Orbit of test_in
    if isinstance(test_in, list) and test_in and isinstance(test_in[0], list):
        t_np = np.array(test_in)
        d4_cands = [
            np.rot90(t_np, 1).tolist(),
            np.rot90(t_np, 2).tolist(),
            np.fliplr(t_np).tolist(),
            np.flipud(t_np).tolist(),
        ]
        for cand in d4_cands:
            if grid_hash(cand) != grid_hash(a1):
                return cand

    # 4. Final shape-conforming fallback
    if fixed_shape is not None and len(fixed_shape) == 2:
        return [[mode_color for _ in range(fixed_shape[1])] for _ in range(fixed_shape[0])]
    return [r[::-1] for r in test_in] if isinstance(test_in, list) else a1
"""

    if "def enforce_zero_mutual_information_attempt2" not in src:
        src += "\n" + zero_mi_helper.strip() + "\n"

    cell9["source"] = [line + "\n" for line in src.splitlines()]

    # Verify AST syntax
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            raw_src = cell.get("source", [])
            code = "\n".join([line for line in ("".join(raw_src)).splitlines() if not line.strip().startswith(("!", "%"))])
            try:
                ast.parse(code)
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in cell {idx}: {e}") from e

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully patched ARC-AGI-2 notebook to SOTA v20 with Zero-Mutual-Information Attempt-2 Protocol.")


if __name__ == "__main__":
    main()
