#!/usr/bin/env python3
"""Patch Biohub v6 to v20:
1. BIOHUB_PRESET = 'harmonic_v20_sota_strict_mitosis_l4'
2. BIOHUB_SAFE_DIV_DIVERGE_UM = '3.5' (was 0.5)
3. BIOHUB_SAFE_DIV_COM_MAX_UM = '3.5'
4. Mitotic daughter Center-of-Mass conservation check in add_safe_divisions_postlink
5. Update kernel-metadata.json to NvidiaL4
"""

import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
nb = json.load(open(nb_path))

# 1. Update Cell 0
cell0_src = nb["cells"][0]["source"]
new_cell0 = []
for line in cell0_src:
    if "BIOHUB_PRESET = " in line:
        new_cell0.append("BIOHUB_PRESET = 'harmonic_v20_sota_strict_mitosis_l4'\n")
    elif "BIOHUB_SCORE_AXIS = " in line:
        new_cell0.append("BIOHUB_SCORE_AXIS = 'v20 SOTA Chassis + Strict Mitosis COM & Divergence + Debris Pruning + L4 Speed (LB target 0.966+)'\n")
    elif 'os.environ["BIOHUB_SAFE_DIV_DIVERGE_UM"]' in line:
        new_cell0.append('os.environ["BIOHUB_SAFE_DIV_DIVERGE_UM"] = "3.5"  # Strict forward-divergence gate (>=3.5um repulsion between daughters at t+2)\n')
        new_cell0.append('os.environ["BIOHUB_SAFE_DIV_COM_MAX_UM"] = "3.5"  # Center-of-mass conservation: daughter midpoint within 3.5um of parent\n')
    else:
        new_cell0.append(line)
nb["cells"][0]["source"] = new_cell0

# 2. Update Cell 2 to parse BIOHUB_SAFE_DIV_COM_MAX_UM
cell2_src = nb["cells"][2]["source"]
new_cell2 = []
for line in cell2_src:
    new_cell2.append(line)
    if 'SAFE_DIV_DIVERGE_UM = float(' in line:
        new_cell2.append('SAFE_DIV_COM_MAX_UM = float(os.environ.get("BIOHUB_SAFE_DIV_COM_MAX_UM", "3.5"))\n')
nb["cells"][2]["source"] = new_cell2

# 3. Update Cell 5 to enforce COM check in add_safe_divisions_postlink
cell5_str = "".join(nb["cells"][5]["source"])
target_code = """                sister_dist = edge_distance_um(existing_child, candidate)
                if sister_dist > SAFE_DIV_SISTER_MAX_UM:
                    continue"""

replacement_code = """                sister_dist = edge_distance_um(existing_child, candidate)
                if sister_dist > SAFE_DIV_SISTER_MAX_UM:
                    continue

                # Mathematical COM conservation: daughter midpoint must closely match parent position at t
                p_src = _position_um(source)
                p_c1 = _position_um(existing_child)
                p_cand = _position_um(candidate)
                com_dist = float(np.linalg.norm(0.5 * (p_c1 + p_cand) - p_src))
                if com_dist > SAFE_DIV_COM_MAX_UM:
                    stats.setdefault("safe_division_com_rejected", 0)
                    stats["safe_division_com_rejected"] += 1
                    continue"""

if target_code in cell5_str:
    cell5_str = cell5_str.replace(target_code, replacement_code, 1)
    nb["cells"][5]["source"] = [cell5_str]
    print("✔ Successfully inserted COM conservation check into Cell 5!")
else:
    print("⚠ Target code for Cell 5 not found!")

with open(nb_path, "w") as f:
    json.dump(nb, f, indent=1)

print("✔ Notebook updated successfully!")

# 4. Update kernel-metadata.json to NvidiaL4
meta_path = Path("scripts/kaggle/biohub_v6/kernel-metadata.json")
meta = json.load(open(meta_path))
meta["machine_shape"] = "NvidiaL4"
with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)

print("✔ Metadata updated to machine_shape: NvidiaL4!")
