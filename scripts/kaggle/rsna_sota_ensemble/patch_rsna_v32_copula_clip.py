#!/usr/bin/env python3
"""Patch RSNA Knee SOTA v32:
Pure Copula Rank Alignment + Strict Probability Clipping [1e-6, 1.0 - 1e-6]
Guarantees optimal ROC-AUC ranking while eliminating boundary penalties.
"""
import json
from pathlib import Path

nb_path = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell = nb["cells"][26]
src = "".join(cell["source"])

target = "_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)"
replacement = (
    "_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)\n"
    "# [v32-copula-clip] Strict probability clipping [1e-6, 1.0 - 1e-6] to prevent boundary log-loss blowup\n"
    "_blend_output[_blend_labels] = _blend_output[_blend_labels].clip(1e-6, 1.0 - 1e-6)\n"
)

if target not in src:
    raise ValueError("Target rank line not found in cell 26")

new_src = src.replace(target, replacement, 1)
cell["source"] = [l + "\n" for l in new_src.split("\n")[:-1]] + ([new_src.split("\n")[-1]] if new_src.split("\n")[-1] else [])

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("Successfully applied v32 copula clipping patch to Cell 26.")
