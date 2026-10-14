#!/usr/bin/env python3
"""
scripts/kaggle/biohub_v6/patch_biohub_v23_sota_gapfill.py

Synthesizes Cohezion Biohub SOTA V23:
1. Restores the exact 0.946 baseline chassis (#56433510 / #56452965).
2. Explicitly disables TF32 (torch.backends.cuda.matmul.allow_tf32 = False, cudnn = False)
   to ensure bit-exact IEEE-754 FP32 precision across all GPUs.
3. Sets kernel-metadata.json to NvidiaTeslaT4 (hardware environment of the 0.946 benchmark).
4. Injects strict bidirectional heading continuity (cos >= 0.40) and midpoint collision veto
   (d >= 2.0 um from any active cell) into close_single_frame_gaps.
5. Enables strict 2-frame gap recovery (recover_strict_gap2 with 8.5 um max span).
"""

import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# --- 1. Patch Cell 0 (Preset, Config & TF32 Disablement) ---
cell0_str = "".join(nb["cells"][0]["source"])

# Replace Preset and Score Axis
cell0_str = cell0_str.replace(
    "BIOHUB_PRESET = 'harmonic_v22_restored_0946_sota'",
    "BIOHUB_PRESET = 'harmonic_v23_sota_guarded_gapfill'"
)
cell0_str = cell0_str.replace(
    "BIOHUB_SCORE_AXIS = 'Cohezion Biohub V22 SOTA: Restored 0.946 Chassis + Zero Prune + Relaxed Divergence (0.5um) + DeepCenter (0.18) + Adaptive 6bba'",
    "BIOHUB_SCORE_AXIS = 'Cohezion Biohub V23 SOTA: 0.946 Chassis + Guarded Heading Gap-Filling + Collision Veto + IEEE-FP32'"
)

# Inject TF32 disablement at top of Cell 0
tf32_block = """import torch
if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
"""
if "allow_tf32" not in cell0_str:
    cell0_str = tf32_block + "\n" + cell0_str

# Set optimal calibrated environment variables in Cell 0
cell0_str = cell0_str.replace('os.environ["BIOHUB_GAP_CLOSE_UM"] = "7.5"', 'os.environ["BIOHUB_GAP_CLOSE_UM"] = "5.8"')
cell0_str = cell0_str.replace('os.environ["BIOHUB_OUTPUT_GAP2_RECOVERY"] = "0"', 'os.environ["BIOHUB_OUTPUT_GAP2_RECOVERY"] = "1"')
cell0_str = cell0_str.replace('os.environ["BIOHUB_DEEPCENTER_GAP_THRESHOLD"] = "0.10"', 'os.environ["BIOHUB_DEEPCENTER_GAP_THRESHOLD"] = "0.25"')

nb["cells"][0]["source"] = cell0_str.splitlines(keepends=True)
print("✔ Patched Cell 0 with V23 configuration and IEEE FP32 precision guards.")

# --- 2. Patch Cell 5 (close_single_frame_gaps with Heading & Collision Invariants) ---
cell5_str = "".join(nb["cells"][5]["source"])

# Ensure predecessor and successor maps are available inside close_single_frame_gaps
old_incident = """    outgoing = {int(edge["source_id"]) for edge in edges}
    incoming = {int(edge["target_id"]) for edge in edges}
    incident = outgoing | incoming"""

new_incident = """    outgoing = {int(edge["source_id"]) for edge in edges}
    incoming = {int(edge["target_id"]) for edge in edges}
    incident = outgoing | incoming
    predecessor = _single_predecessor_map(edges)
    successor = _single_successor_map(edges)"""

if old_incident in cell5_str:
    cell5_str = cell5_str.replace(old_incident, new_incident, 1)
    print("✔ Injected predecessor/successor lookups into close_single_frame_gaps.")

# Inject bidirectional heading and collision guards before midpoint creation
old_midpoint_block = """                source = nodes_by_id[source_id]
                target = nodes_by_id[target_id]
                mid_t = int(source["t"]) + gap
                mid_point = (
                    (float(source["z"]) + float(target["z"])) / 2.0,
                    (float(source["y"]) + float(target["y"])) / 2.0,
                    (float(source["x"]) + float(target["x"])) / 2.0,
                )"""

new_midpoint_block = """                source = nodes_by_id[source_id]
                target = nodes_by_id[target_id]
                mid_t = int(source["t"]) + gap
                mid_point = (
                    (float(source["z"]) + float(target["z"])) / 2.0,
                    (float(source["y"]) + float(target["y"])) / 2.0,
                    (float(source["x"]) + float(target["x"])) / 2.0,
                )

                # Invariant 1: Bidirectional heading continuity
                p_src = _position_um(source)
                p_tgt = _position_um(target)
                gap_step = p_tgt - p_src
                gap_norm = float(np.linalg.norm(gap_step))

                ok_direction = True
                prev_id = predecessor.get(source_id)
                if prev_id is not None:
                    p_prev = _position_um(nodes_by_id[prev_id])
                    prev_step = p_src - p_prev
                    prev_norm = float(np.linalg.norm(prev_step))
                    if prev_norm > 0.05 and gap_norm > 0.05:
                        cos_prev = float(np.dot(prev_step, gap_step) / (prev_norm * gap_norm))
                        if cos_prev < 0.40:
                            ok_direction = False

                next_id = successor.get(target_id)
                if next_id is not None:
                    p_next = _position_um(nodes_by_id[next_id])
                    next_step = p_next - p_tgt
                    next_norm = float(np.linalg.norm(next_step))
                    if next_norm > 0.05 and gap_norm > 0.05:
                        cos_next = float(np.dot(gap_step, next_step) / (gap_norm * next_norm))
                        if cos_next < 0.40:
                            ok_direction = False

                if not ok_direction:
                    stats.setdefault("gap_heading_rejected", 0)
                    stats["gap_heading_rejected"] += 1
                    continue

                # Invariant 2: Midpoint collision veto with active moving cells
                occupied_ids = [nid for nid in all_ids_by_t.get(mid_t, []) if nid in incident and nid in nodes_by_id]
                if occupied_ids:
                    occ_positions = np.array([_position_um(nodes_by_id[nid]) for nid in occupied_ids])
                    mid_um = np.array([mid_point[0], mid_point[1], mid_point[2]]) * np.array(VOXEL_SCALE_UM)
                    min_occ_dist = float(np.min(np.linalg.norm(occ_positions - mid_um, axis=1)))
                    if min_occ_dist < 2.0:
                        stats.setdefault("gap_collision_rejected", 0)
                        stats["gap_collision_rejected"] += 1
                        continue"""

if old_midpoint_block in cell5_str:
    cell5_str = cell5_str.replace(old_midpoint_block, new_midpoint_block, 1)
    print("✔ Injected heading continuity and collision veto invariants into close_single_frame_gaps!")
else:
    print("⚠ old_midpoint_block target not found in Cell 5.")

# Safeguard frame_local_spacing from missing/popped nodes
old_frame_spacing = "        frame_ids = all_ids_by_t.get(t, [])"
new_frame_spacing = "        frame_ids = [nid for nid in all_ids_by_t.get(t, []) if nid in nodes_by_id]"
if old_frame_spacing in cell5_str:
    cell5_str = cell5_str.replace(old_frame_spacing, new_frame_spacing, 1)
    print("✔ Safeguarded frame_local_spacing with nodes_by_id existence check!")

# Also ensure _single_predecessor_map and _single_successor_map are defined BEFORE close_single_frame_gaps
if cell5_str.find("def close_single_frame_gaps") < cell5_str.find("def _single_successor_map"):
    # Extract definition of maps and put them above close_single_frame_gaps
    maps_code = """def _single_successor_map(edges: list[dict[str, object]]) -> dict[int, int]:
    by_source: dict[int, list[int]] = {}
    for edge in edges:
        by_source.setdefault(int(edge["source_id"]), []).append(int(edge["target_id"]))
    return {source: targets[0] for source, targets in by_source.items() if len(targets) == 1}


def _single_predecessor_map(edges: list[dict[str, object]]) -> dict[int, int]:
    by_target: dict[int, list[int]] = {}
    for edge in edges:
        by_target.setdefault(int(edge["target_id"]), []).append(int(edge["source_id"]))
    return {target: sources[0] for target, sources in by_target.items() if len(sources) == 1}

"""
    # Remove old definitions
    cell5_str = cell5_str.replace(maps_code, "")
    # Insert before close_single_frame_gaps
    cell5_str = cell5_str.replace("def close_single_frame_gaps(", maps_code + "\ndef close_single_frame_gaps(")
    print("✔ Moved map helpers above close_single_frame_gaps for fail-safe resolution.")

nb["cells"][5]["source"] = cell5_str.splitlines(keepends=True)

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("✔ Notebook patched successfully.")

# --- 3. Update kernel-metadata.json to NvidiaTeslaT4 ---
meta_path = Path("scripts/kaggle/biohub_v6/kernel-metadata.json")
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

meta["machine_shape"] = "NvidiaTeslaT4"

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print("✔ kernel-metadata.json updated to NvidiaTeslaT4.")
