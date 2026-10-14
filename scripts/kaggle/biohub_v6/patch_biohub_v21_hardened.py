#!/usr/bin/env python3
"""
scripts/kaggle/biohub_v6/patch_biohub_v21_hardened.py
Applies SOTA hardened tracking invariants to cohezion-biohub-v6.ipynb:
1. Re-packs Cell 2 characters into clean lines.
2. Injects intensity-weighted COM conservation: ||(i1*d1 + i2*d2)/(i1+i2) - parent|| <= 3.5 um.
3. Injects daughter divergence repulsion: ||d1 - d2|| >= 3.5 um.
4. Enforces dual-stage temporal persistence filter (prunes track length < 2 frames).
"""

import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Normalize Cell 2 lines
cell2_src = nb["cells"][2]["source"]
if isinstance(cell2_src, list) and len(cell2_src) > 1000:
    full_text = "".join(cell2_src)
    nb["cells"][2]["source"] = full_text.splitlines(keepends=True)
    print("✔ Cleaned Cell 2 character explosion.")

# 2. Patch Cell 5 (Tracking logic)
cell5_str = "".join(nb["cells"][5]["source"])

# Patch 2a: Hardened COM + Divergence Repulsion in add_safe_divisions_postlink
old_com_block = """                sister_dist = edge_distance_um(existing_child, candidate)
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

new_com_block = """                sister_dist = edge_distance_um(existing_child, candidate)
                # Daughter divergence repulsion invariant: ||d1 - d2|| >= 3.5 um
                if sister_dist < SAFE_DIV_DIVERGE_UM or sister_dist > SAFE_DIV_SISTER_MAX_UM:
                    stats.setdefault("safe_division_repulsion_rejected", 0)
                    stats["safe_division_repulsion_rejected"] += 1
                    continue

                # Intensity-weighted COM conservation invariant: ||(i1*d1 + i2*d2)/(i1+i2) - parent|| <= 3.5 um
                p_src = _position_um(source)
                p_c1 = _position_um(existing_child)
                p_cand = _position_um(candidate)
                i1 = float(existing_child.get("intensity", 1.0))
                i2 = float(candidate.get("intensity", 1.0))
                i_sum = i1 + i2
                com = (i1 * p_c1 + i2 * p_cand) / i_sum if i_sum > 0 else 0.5 * (p_c1 + p_cand)
                com_dist = float(np.linalg.norm(com - p_src))
                if com_dist > SAFE_DIV_COM_MAX_UM:
                    stats.setdefault("safe_division_com_rejected", 0)
                    stats["safe_division_com_rejected"] += 1
                    continue"""

if old_com_block in cell5_str:
    cell5_str = cell5_str.replace(old_com_block, new_com_block, 1)
    print("✔ Hardened COM and daughter repulsion injected into add_safe_divisions_postlink!")
else:
    print("⚠ Target code for add_safe_divisions_postlink not matched; verify prior patch state.")

# Patch 2b: COM and Repulsion check in OUTPUT_DIVISION_GEOMETRY_FILTER
old_geom_block = """            d1 = float(top1["distance_um"])
            d2 = float(top2["distance_um"])
            sister = edge_distance_um(nodes_by_id[int(top1["target_id"])], nodes_by_id[int(top2["target_id"])])
            valid_division = (
                max(d1, d2) <= DIV_PARENT_MAX_UM
                and sister <= DIV_SISTER_MAX_UM
                and int(nodes_by_id[int(top1["target_id"])] ["t"]) == int(source["t"]) + 1
                and int(nodes_by_id[int(top2["target_id"])] ["t"]) == int(source["t"]) + 1
            )"""

new_geom_block = """            d1 = float(top1["distance_um"])
            d2 = float(top2["distance_um"])
            child1 = nodes_by_id[int(top1["target_id"])]
            child2 = nodes_by_id[int(top2["target_id"])]
            sister = edge_distance_um(child1, child2)

            p_src = _position_um(source)
            p_d1 = _position_um(child1)
            p_d2 = _position_um(child2)
            i1 = float(child1.get("intensity", 1.0))
            i2 = float(child2.get("intensity", 1.0))
            i_sum = i1 + i2
            com = (i1 * p_d1 + i2 * p_d2) / i_sum if i_sum > 0 else 0.5 * (p_d1 + p_d2)
            com_dist = float(np.linalg.norm(com - p_src))

            valid_division = (
                max(d1, d2) <= DIV_PARENT_MAX_UM
                and sister <= DIV_SISTER_MAX_UM
                and sister >= SAFE_DIV_DIVERGE_UM
                and com_dist <= SAFE_DIV_COM_MAX_UM
                and int(child1["t"]) == int(source["t"]) + 1
                and int(child2["t"]) == int(source["t"]) + 1
            )"""

if old_geom_block in cell5_str:
    cell5_str = cell5_str.replace(old_geom_block, new_geom_block, 1)
    print("✔ Hardened COM and divergence repulsion injected into OUTPUT_DIVISION_GEOMETRY_FILTER!")
else:
    print("⚠ Target code for OUTPUT_DIVISION_GEOMETRY_FILTER not matched.")

# Patch 2c: Post-component persistence sweep (track length < 2 frames pruning)
old_post_sweep = """    nodes_by_id, edges = filter_short_track_components(nodes_by_id, edges, stats)
    print(f"  [{dataset}] after short-track filtering: {len(nodes_by_id)} nodes, {len(edges)} edges"
          f" (components_removed={stats['short_track_components_removed']})")
    nodes_by_id = linefit_smooth_output_graph(nodes_by_id, edges, stats)"""

new_post_sweep = """    nodes_by_id, edges = filter_short_track_components(nodes_by_id, edges, stats)
    print(f"  [{dataset}] after short-track filtering: {len(nodes_by_id)} nodes, {len(edges)} edges"
          f" (components_removed={stats['short_track_components_removed']})")

    # Post-filtering temporal persistence sweep: prune any orphaned singleton nodes (track len < 2)
    if OUTPUT_PRUNE_ISOLATED:
        incident = {int(e["source_id"]) for e in edges} | {int(e["target_id"]) for e in edges}
        kept_nodes = {nid: node for nid, node in nodes_by_id.items() if nid in incident}
        stats["pruned_isolated_nodes"] += len(nodes_by_id) - len(kept_nodes)
        nodes_by_id = kept_nodes
        edges = [e for e in edges if int(e["source_id"]) in nodes_by_id and int(e["target_id"]) in nodes_by_id]

    nodes_by_id = linefit_smooth_output_graph(nodes_by_id, edges, stats)"""

if old_post_sweep in cell5_str:
    cell5_str = cell5_str.replace(old_post_sweep, new_post_sweep, 1)
    print("✔ Post-component persistence sweep injected!")
else:
    print("⚠ Target code for post-component persistence sweep not matched.")

nb["cells"][5]["source"] = cell5_str.splitlines(keepends=True)

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("✔ Notebook patched and saved successfully!")
