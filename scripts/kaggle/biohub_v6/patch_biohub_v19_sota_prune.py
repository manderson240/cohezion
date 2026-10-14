#!/usr/bin/env python3
"""
patch_biohub_v19_sota_prune.py

Cohezion Biohub V19 SOTA Optimization:
1. Fixes the P0 Critical Root Cause identified in Adversarial Audit & Leaderboard validation:
   - Sets BIOHUB_OUTPUT_PRUNE_ISOLATED = "1"
   - Pruning unlinked optical debris vertices stops AOGM numerator inflation (recovering +0.0197 TRA).
2. Preserves verified winning parameters:
   - BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD = "0.28"
   - BIOHUB_ADAPTIVE_STEMS = "6bba"
   - BIOHUB_ADAPTIVE_LOW_THRESHOLD = "0.945"
   - BIOHUB_USE_MIN_COST_FLOW = "0"
   - BIOHUB_USE_LEVIN_FIELD = "0"
3. Updates Cell 0 score axis and presets to v19 SOTA.
Target Leaderboard: 0.966+ (Top 3 Podium)
"""

import json
import re
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")


def apply_v19_patch():
    print(f"[Biohub V19] Loading {NOTEBOOK_PATH}...")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Patch Cell 0
    cell_0_src = "".join(nb["cells"][0]["source"])
    cell_0_src = re.sub(
        r"BIOHUB_PRESET = '.*?'",
        "BIOHUB_PRESET = 'harmonic_v19_sota_prune_adaptive'",
        cell_0_src,
    )
    cell_0_src = re.sub(
        r"BIOHUB_SCORE_AXIS = '.*?'",
        "BIOHUB_SCORE_AXIS = 'v19 SOTA Chassis + Isolated Debris Pruning + DeepCenter 0.28 + Adaptive Stem 6bba (LB target 0.966+)'",
        cell_0_src,
    )

    # Enable isolated node pruning (crucial fix)
    if 'os.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_OUTPUT_PRUNE_ISOLATED"\] = ".*?"',
            'os.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"] = "1"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"] = "1"\n'

    # DeepCenter threshold
    if 'os.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"\] = ".*?"',
            'os.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"] = "0.28"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"] = "0.28"\n'

    # Adaptive stem config
    if 'os.environ["BIOHUB_ADAPTIVE_STEMS"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_ADAPTIVE_STEMS"\] = ".*?"',
            'os.environ["BIOHUB_ADAPTIVE_STEMS"] = "6bba"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_ADAPTIVE_STEMS"] = "6bba"\n'

    if 'os.environ["BIOHUB_ADAPTIVE_LOW_THRESHOLD"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_ADAPTIVE_LOW_THRESHOLD"\] = ".*?"',
            'os.environ["BIOHUB_ADAPTIVE_LOW_THRESHOLD"] = "0.945"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_ADAPTIVE_LOW_THRESHOLD"] = "0.945"\n'

    nb["cells"][0]["source"] = [line + "\n" for line in cell_0_src.splitlines()]

    # 2. Patch Cell 1 Guard if present
    cell_1_src = "".join(nb["cells"][1]["source"])
    if '"BIOHUB_OUTPUT_PRUNE_ISOLATED": "0"' in cell_1_src:
        cell_1_src = cell_1_src.replace(
            '"BIOHUB_OUTPUT_PRUNE_ISOLATED": "0"',
            '"BIOHUB_OUTPUT_PRUNE_ISOLATED": "1"'
        )
        nb["cells"][1]["source"] = [line + "\n" for line in cell_1_src.splitlines()]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"[Biohub V19] Successfully patched {NOTEBOOK_PATH} with isolated debris pruning enabled.")


if __name__ == "__main__":
    apply_v19_patch()
