#!/usr/bin/env python3
"""Assemble Cohezion RSNA Knee SOTA v35: Calibrated Tri-Model Blend.
Restores optimal Raptor-384 / Raptor-224 / R7 ConvNeXt balance:
- A224 = 0.38 (fine-tuned 224-crop share)
- Calibrated per-pathology weights restoring balanced R7 diversity:
  Medial OA: 0.72, Lateral OA: 0.58, ACL: 0.68, Lateral Meniscus: 0.62, Effusion: 0.60.
- Strict [1e-6, 1 - 1e-6] probability boundary clipping.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb")
BAK_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb.v34.bak")


def main() -> None:
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up notebook to {BAK_PATH}")

    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cell_idx = len(nb["cells"]) - 1
    cell_source = "".join(nb["cells"][cell_idx]["source"])

    old_target = """W_RAPTOR, W_OURS = 0.5, 0.5
# Per-pathology noise-insulated calibrated weights (First Principles / SOTA v34 Podium Edition):
# 1. Medial OA exhibited -0.50 Spearman correlation between Raptor and R7; weighting Raptor at 0.85 eliminates destructive rank interference.
# 2. Cruciate ligaments (ACL), Lateral Meniscus, and Effusion suffered from extreme R7 baseline probability collapse (~10^-6),
#    causing rank(ours) to order floating-point noise. Weighting Raptor at 0.80 - 0.85 insulates against noise injection.
# 3. High-consensus findings (MCL, Medial Meniscus, Synovitis, Baker's, Contusion, Fracture) with rho=1.0 retain 0.50/0.50 for variance reduction.
W_RAPTOR_C = {
    'Medial OA': 0.85,
    'Lateral OA': 0.70,
    'PF OA': 0.50,
    'ACL': 0.85,
    'Lateral Meniscus': 0.85,
    'Effusion': 0.80,
}"""

    new_weights = """W_RAPTOR, W_OURS = 0.5, 0.5
# Per-pathology noise-insulated calibrated weights (First Principles / SOTA v35 Equilibrium Edition):
# Calibrated balance between Raptor-384, Raptor-224 (A224=0.38), and R7 ConvNeXt-small:
# Preserves R7 structural diversity while suppressing rank noise on low-probability findings.
W_RAPTOR_C = {
    'Medial OA': 0.72,
    'Lateral OA': 0.58,
    'PF OA': 0.50,
    'ACL': 0.68,
    'Lateral Meniscus': 0.62,
    'Effusion': 0.60,
}"""

    if old_target not in cell_source:
        raise ValueError("Could not find v34 blend weights in blending cell!")

    cell_source = cell_source.replace(old_target, new_weights)
    cell_source = cell_source.replace("v34 Podium Calibrated Tri-Model", "v35 Equilibrium Calibrated Tri-Model")
    cell_source = cell_source.replace("A224 = 0.50", "A224 = 0.38")

    nb["cells"][cell_idx]["source"] = [l + "\n" for l in cell_source.splitlines()]

    # Header update
    h_source = "".join(nb["cells"][0]["source"])
    h_source = h_source.replace("SOTA v34: Podium", "SOTA v35: Equilibrium")
    nb["cells"][0]["source"] = [l + "\n" for l in h_source.splitlines()]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully upgraded RSNA Knee notebook to SOTA v35 (Equilibrium Calibrated Tri-Model).")


if __name__ == "__main__":
    main()
