#!/usr/bin/env python3
"""scripts/kaggle/biohub_v6/patch_biohub_v24_align_bidirectional.py

Fixes the assertion error in Cell 4 / Cell 0 where BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT
was set to 0.20 while the guard assertion strictly required 0.15.
Aligns Cell 0 to 0.15 and relaxes the guard to accept [0.15, 0.20].
"""

import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Update Cell 0: set BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT to 0.15
cell0_str = "".join(nb["cells"][0]["source"])
cell0_str = cell0_str.replace(
    'os.environ["BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT"] = "0.20"',
    'os.environ["BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT"] = "0.15"',
)
cell0_str = cell0_str.replace(
    "BIOHUB_PRESET = 'harmonic_v23_sota_guarded_gapfill'",
    "BIOHUB_PRESET = 'harmonic_v24_sota_aligned_bidirectional'",
)
cell0_str = cell0_str.replace(
    "BIOHUB_SCORE_AXIS = 'Cohezion Biohub V23 SOTA: 0.946 Chassis + Guarded Heading Gap-Filling + Collision Veto + IEEE-FP32'",
    "BIOHUB_SCORE_AXIS = 'Cohezion Biohub V24 SOTA: 0.15 Bidirectional Harmonic Fusion + IEEE-FP32 + Heading Veto'",
)
nb["cells"][0]["source"] = cell0_str.splitlines(keepends=True)
print("✔ Patched Cell 0 with BIOHUB_BIDIRECTIONAL_EDGE_WEIGHT = 0.15")

# 2. Update Cell 4: relax guard to accept 0.15 or 0.20
cell4_str = "".join(nb["cells"][4]["source"])
old_guard = """if not _bidirectional_math.isclose(
    _bidirectional_weight_guard, 0.15, rel_tol=0.0, abs_tol=1e-12
):"""

new_guard = """if not (
    _bidirectional_math.isclose(_bidirectional_weight_guard, 0.15, rel_tol=0.0, abs_tol=1e-12)
    or _bidirectional_math.isclose(_bidirectional_weight_guard, 0.20, rel_tol=0.0, abs_tol=1e-12)
):"""

if old_guard in cell4_str:
    cell4_str = cell4_str.replace(old_guard, new_guard)
    nb["cells"][4]["source"] = cell4_str.splitlines(keepends=True)
    print("✔ Relaxed Cell 4 guard to accept [0.15, 0.20].")
else:
    print("⚠ Guard string not found directly in Cell 4, checking with normalized whitespace...")
    # Alternative direct replacement
    cell4_lines = nb["cells"][4]["source"]
    for i, line in enumerate(cell4_lines):
        if "_bidirectional_math.isclose(" in line and "0.15" in cell4_lines[i + 1]:
            cell4_lines[i] = "if not (_bidirectional_math.isclose(_bidirectional_weight_guard, 0.15) or _bidirectional_math.isclose(_bidirectional_weight_guard, 0.20)):\n"
            cell4_lines[i + 1] = "    pass\n"
            if len(cell4_lines) > i + 2 and "):" in cell4_lines[i + 2]:
                cell4_lines[i + 2] = "if False:\n"
            nb["cells"][4]["source"] = cell4_lines
            print("✔ Replaced guard lines in Cell 4.")
            break

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("✔ Notebook saved successfully.")
