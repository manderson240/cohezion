#!/usr/bin/env python3
"""
patch_biohub_v16.py

Cohezion Biohub V16 SOTA Optimization:
1. RESTORES verified 0.946 winning tracking parameters:
   - BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD = "0.28" (reverts harmful 0.18 setting that caused false divisions)
   - BIOHUB_OUTPUT_PRUNE_ISOLATED = "0" (PREVENTS CATASTROPHIC w_FN=10.0 CASCADES from deleting real nodes!)
   - BIOHUB_USE_MIN_COST_FLOW = "0"
   - BIOHUB_USE_LEVIN_FIELD = "0"
2. ALIGNS Cell 1 configuration drift guard:
   - Updates _EXPECTED_NUMERIC["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"] = 0.28
3. PRESERVES validated mitotic fission gates:
   - Strict t+2 Grandchild Divergence (SAFE_DIV_REQUIRE_DIVERGENCE = True)
   - Calibrated DeepCenter Veto (0.28)
   - Mutual Nearest-Neighbor and Sister Symmetry gates
4. INTEGRATES stem-adaptive detection sensitivity:
   - BIOHUB_ADAPTIVE_STEMS = "6bba"
   - BIOHUB_ADAPTIVE_LOW_THRESHOLD = "0.945"

Target Leaderboard: 0.966+ (Top 3 Podium, $8,000 - $18,000 winnable cash)
"""

import ast
import json
import re
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")


def apply_v16_patch():
    print(f"[Biohub V16] Loading {NOTEBOOK_PATH}...")
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # -------------------------------------------------------------
    # 1. Patch Cell 0: Presets, Score Axis, and Environment Config
    # -------------------------------------------------------------
    cell_0_src = "".join(nb["cells"][0]["source"])
    cell_0_src = re.sub(
        r"BIOHUB_PRESET = '.*?'",
        "BIOHUB_PRESET = 'harmonic_v16_restored_zero_prune_sota'",
        cell_0_src,
    )
    cell_0_src = re.sub(
        r"BIOHUB_SCORE_AXIS = '.*?'",
        "BIOHUB_SCORE_AXIS = 'v16 Restored SOTA Chassis + Zero Prune Isolated + DeepCenter 0.28 (LB target 0.966+)'",
        cell_0_src,
    )
    # Ensure min cost flow is disabled
    cell_0_src = re.sub(
        r'os\.environ\["BIOHUB_USE_MIN_COST_FLOW"\] = ".*?"',
        'os.environ["BIOHUB_USE_MIN_COST_FLOW"] = "0"',
        cell_0_src,
    )
    # Ensure Levin field momentum penalty is disabled
    if 'os.environ["BIOHUB_USE_LEVIN_FIELD"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_USE_LEVIN_FIELD"\] = ".*?"',
            'os.environ["BIOHUB_USE_LEVIN_FIELD"] = "0"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_USE_LEVIN_FIELD"] = "0"\n'

    # Calibrate DeepCenter Safe Div threshold to 0.28 (0.946 winning setting)
    if 'os.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"\] = ".*?"',
            'os.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"] = "0.28"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD"] = "0.28"\n'

    # CRITICAL INVARIANT: Disable isolated node pruning (saves hundreds of w_FN=10.0 penalties)
    if 'os.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"]' in cell_0_src:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_OUTPUT_PRUNE_ISOLATED"\] = ".*?"',
            'os.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"] = "0"',
            cell_0_src,
        )
    else:
        cell_0_src += '\nos.environ["BIOHUB_OUTPUT_PRUNE_ISOLATED"] = "0"\n'

    # Configure adaptive low threshold for faint stems (6bba)
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

    nb["cells"][0]["source"] = [cell_0_src]
    ast.parse(cell_0_src)
    print("✔ Cell 0 AST syntax validated successfully!")

    # -------------------------------------------------------------
    # 2. Patch Cell 1 (Drift Guard): align _EXPECTED_NUMERIC
    # -------------------------------------------------------------
    cell_1_src = "".join(nb["cells"][1]["source"])
    cell_1_src = re.sub(
        r'"BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD":\s*[0-9.]+',
        '"BIOHUB_DEEPCENTER_SAFE_DIV_THRESHOLD": 0.28',
        cell_1_src,
    )
    nb["cells"][1]["source"] = [cell_1_src]
    ast.parse(cell_1_src)
    print("✔ Cell 1 (Drift Guard) AST syntax validated successfully!")

    # Save patched notebook
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"✔ Successfully saved {NOTEBOOK_PATH} with Biohub V16 patch.")


if __name__ == "__main__":
    apply_v16_patch()
