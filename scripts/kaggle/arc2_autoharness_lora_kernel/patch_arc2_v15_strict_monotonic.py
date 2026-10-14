#!/usr/bin/env python3
"""Patch script for ARC-AGI-2 SOTA v15: Strict Monotonic Attempt-2 Invariant.
=============================================================================
Enforces true mathematical monotonicity for ARC competition scoring:
1. Preserves attempt_1 (neural model's top hypothesis).
2. ONLY injects verified DSL synthesis into attempt_2 if:
   a) attempt_2 is dummy or invalid, OR
   b) attempt_2 is identical to attempt_1 (meaning the neural model produced
      a duplicate guess, so attempt_2 had ZERO marginal value).
3. If the neural model produced two distinct valid guesses (attempt_1 != attempt_2),
   BOTH are strictly preserved. This mathematically guarantees that the score
   CANNOT drop below the 31.81% neural baseline.
4. Validates AST syntax across all cells.
"""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb")
BACKUP_PATH = Path("scripts/kaggle/arc2_autoharness_lora_kernel/arc-agi-2-fork-lb33-89-20260903.ipynb.v14.bak")


def patch_arc2_v15() -> None:
    # 1. Backup notebook
    shutil.copyfile(NOTEBOOK_PATH, BACKUP_PATH)
    print(f"Backed up notebook to {BACKUP_PATH}")

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 2. Patch Cell 9
    cell9 = nb["cells"][9]
    src = "".join(cell9["source"])

    old_snippet = """                    cur_attempt_1 = target_pred.get('attempt_1')
                    if is_dummy_or_invalid(cur_attempt_1):
                        target_pred['attempt_1'] = dsl_solution
                        dsl_solved_count += 1
                    else:
                        # Non-destructive injection into attempt_2
                        if dsl_solution != cur_attempt_1:
                            target_pred['attempt_2'] = dsl_solution
                            dsl_solved_count += 1"""

    new_snippet = """                    cur_attempt_1 = target_pred.get('attempt_1')
                    cur_attempt_2 = target_pred.get('attempt_2')
                    if is_dummy_or_invalid(cur_attempt_1):
                        target_pred['attempt_1'] = dsl_solution
                        dsl_solved_count += 1
                    # Strict Monotonic Invariant: Only inject into attempt_2 if attempt_2 is
                    # invalid OR identical to attempt_1 (zero loss of distinct neural hypotheses)
                    elif is_dummy_or_invalid(cur_attempt_2) or (cur_attempt_2 == cur_attempt_1):
                        if dsl_solution != cur_attempt_1:
                            target_pred['attempt_2'] = dsl_solution
                            dsl_solved_count += 1"""

    if old_snippet not in src:
        raise ValueError("Could not find old injection snippet in Cell 9!")

    src = src.replace(old_snippet, new_snippet)
    src = src.replace("AutoHarness SOTA v14", "AutoHarness SOTA v15")

    cell9["source"] = [line + "\n" for line in src.splitlines()]
    print("✓ Cell 9: Applied strict monotonic invariant preserving distinct neural hypotheses")

    # 3. Verify AST syntax for all cells
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            raw_src = cell.get("source", [])
            full_text = "".join(raw_src) if isinstance(raw_src, list) else str(raw_src)
            clean_lines = [line for line in full_text.splitlines() if not line.strip().startswith(("!", "%"))]
            code = "\n".join(clean_lines)
            try:
                ast.parse(code)
            except SyntaxError as e:
                raise RuntimeError(f"Syntax error in cell {idx}: {e}")

    print("✓ All cells passed AST syntax verification")

    # 4. Save updated notebook
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"✓ Saved updated SOTA v15 notebook to {NOTEBOOK_PATH}")


if __name__ == "__main__":
    patch_arc2_v15()
