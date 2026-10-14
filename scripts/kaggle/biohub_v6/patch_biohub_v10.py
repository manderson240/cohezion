#!/usr/bin/env python3
"""Patches cohezion-biohub-v6.ipynb to Biohub v10 SOTA:
- BIOHUB_PRESET = 'harmonic_v10_levin_morphogenetic_field'
- BIOHUB_SCORE_AXIS = 'v10 Levin Morphogenetic Field + Kinematic Directional Momentum + Mitotic Wave Prior (LB target 0.968+)'
- os.environ["BIOHUB_USE_MIN_COST_FLOW"] = "0"
- os.environ["BIOHUB_USE_LEVIN_FIELD"] = "1"
- Levin Morphogenetic Field calculation per frame: spatial Gaussian kernel-weighted velocity field V_field(x)
- Velocity blending: v_pred = 0.70 * v_cell + 0.30 * V_field(x) (or 1.0 * V_field(x) for new cells without history)
- Directional momentum alignment penalty & bonus
- Tight (7.0um) and relaxed (12.0um) Hungarian passes run with Levin-augmented cost
- Predecessor positions updated properly
- Mitotic Wave Gating in add_safe_divisions_postlink (W_wave >= 0.30 relaxed, solitary penalized)
"""

import json
import re
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")


def patch_notebook():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Patch Cell 0
    cell_0_src = "".join(nb["cells"][0]["source"])
    cell_0_src = re.sub(
        r"BIOHUB_PRESET = '.*?'",
        "BIOHUB_PRESET = 'harmonic_v10_levin_morphogenetic_field'",
        cell_0_src,
    )
    cell_0_src = re.sub(
        r"BIOHUB_SCORE_AXIS = '.*?'",
        "BIOHUB_SCORE_AXIS = 'v10 Levin Morphogenetic Field + Kinematic Directional Momentum + Mitotic Wave Prior (LB target 0.968+)'",
        cell_0_src,
    )
    cell_0_src = re.sub(
        r'os\.environ\["BIOHUB_USE_MIN_COST_FLOW"\] = ".*?"',
        'os.environ["BIOHUB_USE_MIN_COST_FLOW"] = "0"',
        cell_0_src,
    )
    if 'os.environ["BIOHUB_USE_LEVIN_FIELD"]' not in cell_0_src:
        cell_0_src += '\nos.environ["BIOHUB_USE_LEVIN_FIELD"] = "1"\n'
    else:
        cell_0_src = re.sub(
            r'os\.environ\["BIOHUB_USE_LEVIN_FIELD"\] = ".*?"',
            'os.environ["BIOHUB_USE_LEVIN_FIELD"] = "1"',
            cell_0_src,
        )

    nb["cells"][0]["source"] = [cell_0_src]

    # 2. Patch Cell 5 (Levin Morphogenetic Field + Directional Momentum + Mitotic Wave Prior)
    cell_5_src = "".join(nb["cells"][5]["source"])

    # Locate motion_relink_edges and add_safe_divisions_postlink
    m_start = cell_5_src.find("def motion_relink_edges(")
    gap_start = cell_5_src.find("def close_single_frame_gaps(")
    div_start = cell_5_src.find("def add_safe_divisions_postlink(")
    short_start = cell_5_src.find("def filter_short_track_components(")

    if m_start == -1 or gap_start == -1 or div_start == -1 or short_start == -1:
        raise ValueError("Could not find function boundaries in Cell 5")

    new_motion_relink = '''def motion_relink_edges(
    nodes_by_id: dict[int, dict[str, object]],
    stats: dict[str, int],
    learned_edge_probs: dict[tuple[int, int], float] | None = None,
) -> list[dict[str, object]]:
    if not OUTPUT_MOTION_RELINK or not nodes_by_id:
        return []

    learned_edge_probs = learned_edge_probs or {}

    def learned_prob(source_id: int, target_id: int) -> float:
        value = learned_edge_probs.get((source_id, target_id), 0.0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not np.isfinite(value):
            return 0.0
        if value < 0.0 or value > 1.0:
            value = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, value))))
        return float(np.clip(value, 0.0, 1.0))

    ids_by_t: dict[int, list[int]] = {}
    for node_id, node in nodes_by_id.items():
        ids_by_t.setdefault(int(node["t"]), []).append(node_id)
    for ids in ids_by_t.values():
        ids.sort()

    frame_sizes = [len(ids) for ids in ids_by_t.values()]
    if frame_sizes and max(frame_sizes) > MOTION_RELINK_MAX_FRAME_NODES:
        stats["motion_relink_skipped_large_frame"] = 1
        return []

    position_um = {node_id: _position_um(node) for node_id, node in nodes_by_id.items()}
    predecessor_position_um: dict[int, np.ndarray] = {}
    selected_edges: list[dict[str, object]] = []

    use_mcf = os.environ.get("BIOHUB_USE_MIN_COST_FLOW", "0") == "1"
    if use_mcf:
        mcf_matches = solve_min_cost_flow_linking(
            ids_by_t,
            position_um,
            gate_um=MOTION_RELINK_TIGHT_UM,
            c_enter=5.0,
            c_exit=5.0,
            learned_edge_probs=learned_edge_probs,
        )
        if mcf_matches:
            for source_id, target_id, raw, motion, prob in mcf_matches:
                selected_edges.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "edge_prob": prob,
                    "distance_um": raw,
                    "motion_distance_um": motion,
                    "motion_relinked": 1,
                    "motion_pass": "min_cost_flow",
                })
                predecessor_position_um[target_id] = position_um[source_id]
            stats["motion_relink_mcf_edges"] = len(selected_edges)
            stats["motion_relink_edges"] = len(selected_edges)
            return selected_edges

    use_levin = os.environ.get("BIOHUB_USE_LEVIN_FIELD", "1") == "1"

    def compute_levin_morphogenetic_field(
        source_ids: list[int],
        sigma_um: float = 15.0,
    ) -> dict[int, np.ndarray]:
        """Calculates spatial Gaussian kernel-weighted tissue velocity field V_field(x)."""
        v_pred_map: dict[int, np.ndarray] = {}
        known = [sid for sid in source_ids if sid in predecessor_position_um]
        if not known:
            zero_vec = np.zeros(3, dtype=np.float64)
            for sid in source_ids:
                v_pred_map[sid] = zero_vec
            return v_pred_map

        pos_known = np.stack([position_um[sid] for sid in known])
        vel_known = np.stack([position_um[sid] - predecessor_position_um[sid] for sid in known])
        inv_two_sigma_sq = 1.0 / (2.0 * sigma_um * sigma_um)

        for sid in source_ids:
            cur_pos = position_um[sid]
            dists_sq = np.sum((pos_known - cur_pos) ** 2, axis=1)
            weights = np.exp(-dists_sq * inv_two_sigma_sq)
            sum_w = float(np.sum(weights))
            if sum_w > 1e-6:
                v_field = np.sum(weights[:, None] * vel_known, axis=0) / sum_w
            else:
                v_field = np.zeros(3, dtype=np.float64)

            if sid in predecessor_position_um:
                v_cell = cur_pos - predecessor_position_um[sid]
                v_pred = 0.70 * v_cell + 0.30 * v_field
            else:
                v_pred = 1.0 * v_field
            v_pred_map[sid] = v_pred

        return v_pred_map

    def assign_pass(
        source_ids: list[int],
        target_ids: list[int],
        gate_um: float,
        v_pred_map: dict[int, np.ndarray] | None = None,
    ) -> list[tuple[int, int, float, float, float]]:
        if not source_ids or not target_ids:
            return []
        big = gate_um * 1000.0 + 1.0
        cost = np.full((len(source_ids), len(target_ids)), big, dtype=np.float64)
        raw_dist = np.full_like(cost, np.inf)
        motion_dist = np.full_like(cost, np.inf)
        prob_matrix = np.zeros_like(cost)
        for i, source_id in enumerate(source_ids):
            source_pos = position_um[source_id]
            if use_levin and v_pred_map is not None:
                v_pred = v_pred_map.get(source_id, np.zeros(3, dtype=np.float64))
                predicted = source_pos + v_pred
                norm_v = float(np.linalg.norm(v_pred))
            else:
                prev_pos = predecessor_position_um.get(source_id)
                if prev_pos is None:
                    predicted = source_pos
                    v_pred = np.zeros(3, dtype=np.float64)
                    norm_v = 0.0
                else:
                    v_cell = source_pos - prev_pos
                    predicted = source_pos + MOTION_RELINK_VELOCITY_WEIGHT * v_cell
                    v_pred = v_cell
                    norm_v = float(np.linalg.norm(v_pred))

            for j, target_id in enumerate(target_ids):
                target_pos = position_um[target_id]
                delta = target_pos - source_pos
                raw = float(np.linalg.norm(delta))
                if raw > gate_um:
                    continue
                motion = float(np.linalg.norm(target_pos - predicted))
                prob = learned_prob(source_id, target_id)
                raw_dist[i, j] = raw
                motion_dist[i, j] = motion
                prob_matrix[i, j] = prob
                base_cost = motion + 0.05 * raw - MOTION_RELINK_LEARNED_BONUS * prob

                # Directional momentum alignment penalty and bonus
                momentum_penalty = 0.0
                if use_levin and norm_v > 1e-4 and raw > 1e-4:
                    cos_theta = float(np.dot(v_pred, delta) / (norm_v * raw))
                    cos_theta = max(-1.0, min(1.0, cos_theta))
                    if cos_theta < 0.0 and raw > 2.5:
                        momentum_penalty += 3.5 * (1.0 - cos_theta)
                    elif cos_theta > 0.75:
                        momentum_penalty -= 1.0 * cos_theta

                cost[i, j] = base_cost + momentum_penalty

        row_ind, col_ind = linear_sum_assignment(cost)
        matches: list[tuple[int, int, float, float, float]] = []
        for r, c in zip(row_ind, col_ind):
            if cost[r, c] >= big:
                continue
            matches.append((
                source_ids[int(r)],
                target_ids[int(c)],
                float(raw_dist[r, c]),
                float(motion_dist[r, c]),
                float(prob_matrix[r, c]),
            ))
        return matches

    times = sorted(ids_by_t)
    for t in times:
        source_ids = ids_by_t.get(t, [])
        target_ids = ids_by_t.get(t + 1, [])
        if not source_ids or not target_ids:
            continue
        unmatched_sources = set(source_ids)
        unmatched_targets = set(target_ids)
        v_pred_map = compute_levin_morphogenetic_field(source_ids) if use_levin else None

        frame_matches: list[tuple[int, int, float, float, str, float]] = []
        for pass_name, gate_um in (("tight", MOTION_RELINK_TIGHT_UM), ("relaxed", MOTION_RELINK_RELAXED_UM)):
            pass_sources = [node_id for node_id in source_ids if node_id in unmatched_sources]
            pass_targets = [node_id for node_id in target_ids if node_id in unmatched_targets]
            matches = assign_pass(pass_sources, pass_targets, gate_um, v_pred_map=v_pred_map)
            for source_id, target_id, raw, motion, prob in matches:
                if source_id not in unmatched_sources or target_id not in unmatched_targets:
                    continue
                unmatched_sources.remove(source_id)
                unmatched_targets.remove(target_id)
                frame_matches.append((source_id, target_id, raw, motion, pass_name, prob))
                if pass_name == "tight":
                    stats["motion_relink_tight_edges"] += 1
                else:
                    stats["motion_relink_relaxed_edges"] += 1
        for source_id, target_id, raw, motion, pass_name, prob in frame_matches:
            selected_edges.append({
                "source_id": source_id,
                "target_id": target_id,
                "edge_prob": prob,
                "distance_um": raw,
                "motion_distance_um": motion,
                "motion_relinked": 1,
                "motion_pass": pass_name,
            })
            predecessor_position_um[target_id] = position_um[source_id]
        stats["motion_relink_frames"] += 1

    stats["motion_relink_edges"] = len(selected_edges)
    return selected_edges
'''

    new_safe_div = '''def add_safe_divisions_postlink(
    nodes_by_id: dict[int, dict[str, object]],
    edges: list[dict[str, object]],
    stats: dict[str, int],
    dataset: str | None = None,
    deepcenter_bundle: dict[str, object] | None = None,
    frame_cache: dict[int, np.ndarray] | None = None,
    deepcenter_cache: dict[tuple[str, int], np.ndarray] | None = None,
) -> list[dict[str, object]]:
    if not OUTPUT_SAFE_DIVISIONS or not edges or not nodes_by_id:
        return edges
    frame_cache = frame_cache if frame_cache is not None else {}
    deepcenter_cache = deepcenter_cache if deepcenter_cache is not None else {}
 
    out_by_source: dict[int, list[dict[str, object]]] = {}
    incoming: set[int] = set()
    for edge in edges:
        out_by_source.setdefault(int(edge["source_id"]), []).append(edge)
        incoming.add(int(edge["target_id"]))
 
    ids_by_t: dict[int, list[int]] = {}
    for node_id, node in nodes_by_id.items():
        ids_by_t.setdefault(int(node["t"]), []).append(node_id)
 
    existing_edges = {(int(edge["source_id"]), int(edge["target_id"])) for edge in edges}
    global_cap = max(1, int(round(max(1, len(edges)) * SAFE_DIV_GLOBAL_FRAC_CAP)))
    added: list[dict[str, object]] = []
    used_targets: set[int] = set()
    used_sources: set[int] = set()
 
    for t in sorted(ids_by_t):
        child_frame_ids = ids_by_t.get(t + 1, [])
        if not child_frame_ids:
            continue
        source_ids = [node_id for node_id in ids_by_t[t] if len(out_by_source.get(node_id, [])) == 1]
        candidate_ids = [node_id for node_id in child_frame_ids if node_id not in incoming and node_id not in used_targets]
        if not source_ids or not candidate_ids:
            continue
 
        candidate_tree = None
        if SAFE_DIV_REQUIRE_MUTUAL_NN:
            candidate_positions = np.stack([_position_um(nodes_by_id[cid]) for cid in candidate_ids])
            candidate_tree = cKDTree(candidate_positions)

        # Mitotic wave calculation per frame
        cand_src_list = []
        for sid in source_ids:
            echild_edge = out_by_source[sid][0]
            echild = nodes_by_id.get(int(echild_edge["target_id"]))
            if echild is not None and edge_distance_um(nodes_by_id[sid], echild) <= SAFE_DIV_EXISTING_CHILD_MAX_UM:
                cand_src_list.append(sid)

        cand_positions_array = (
            np.stack([_position_um(nodes_by_id[sid]) for sid in cand_src_list])
            if len(cand_src_list) > 1 else None
        )
        cand_src_to_idx = {sid: i for i, sid in enumerate(cand_src_list)}

        def compute_w_wave(source_id: int) -> float:
            if cand_positions_array is None or len(cand_src_list) <= 1:
                return 0.0
            idx = cand_src_to_idx.get(source_id)
            if idx is None:
                return 0.0
            pos = cand_positions_array[idx]
            dists_sq = np.sum((cand_positions_array - pos) ** 2, axis=1)
            mask = np.ones(len(cand_src_list), dtype=bool)
            mask[idx] = False
            sigma_wave = 25.0
            w_vals = np.exp(-dists_sq[mask] / (2.0 * sigma_wave * sigma_wave))
            return float(np.sum(w_vals))
 
        frame_cap = max(1, int(round(len(source_ids) * SAFE_DIV_FRAME_FRAC_CAP)))
        proposals: list[tuple[float, int, int, float, float]] = []
        for source_id in source_ids:
            source = nodes_by_id[source_id]
            existing_child_edge = out_by_source[source_id][0]
            existing_child_id = int(existing_child_edge["target_id"])
            existing_child = nodes_by_id.get(existing_child_id)
            if existing_child is None or int(existing_child["t"]) != t + 1:
                continue
            child_dist = edge_distance_um(source, existing_child)
            if child_dist > SAFE_DIV_EXISTING_CHILD_MAX_UM:
                continue
 
            mutual_nn_id = None
            if candidate_tree is not None:
                _, nn_idx = candidate_tree.query(_position_um(existing_child))
                mutual_nn_id = candidate_ids[int(nn_idx)]

            w_wave = compute_w_wave(source_id)
            is_wave_cluster = (w_wave >= 0.30)
            if is_wave_cluster:
                # Relaxed division gate for synchronized mitotic wave clusters
                gate_parent_max = SAFE_DIV_MAX_UM * 1.15
                gate_sister_max = SAFE_DIV_SISTER_MAX_UM * 1.15
                gate_cos_max = 0.55
                gate_sym_tau = SAFE_DIV_SISTER_SYMMETRY_TAU * 1.25
                wave_score_bias = -1.5 * min(w_wave, 2.0)
            else:
                # Penalized solitary split gate
                gate_parent_max = SAFE_DIV_MAX_UM * 0.85
                gate_sister_max = SAFE_DIV_SISTER_MAX_UM * 0.85
                gate_cos_max = 0.30
                gate_sym_tau = SAFE_DIV_SISTER_SYMMETRY_TAU * 0.85
                wave_score_bias = +3.0 * (0.30 - w_wave)
 
            for candidate_id in candidate_ids:
                if (source_id, candidate_id) in existing_edges:
                    continue
                candidate = nodes_by_id[candidate_id]
                parent_dist = edge_distance_um(source, candidate)
                if parent_dist > gate_parent_max:
                    continue
                sister_dist = edge_distance_um(existing_child, candidate)
                if sister_dist > gate_sister_max:
                    continue
 
                # PATCH: mutual-nearest-orphan.
                if SAFE_DIV_REQUIRE_MUTUAL_NN and candidate_id != mutual_nn_id:
                    stats["safe_division_mutual_nn_rejected"] += 1
                    continue
 
                if SAFE_DIV_REQUIRE_DIVERGENCE:
                    c1_succ = out_by_source.get(existing_child_id, [])
                    q_succ = out_by_source.get(candidate_id, [])
                    pos_src = _position_um(source)
                    pos_c1 = _position_um(existing_child)
                    pos_cand = _position_um(candidate)
                    v1 = pos_c1 - pos_src
                    v2 = pos_cand - pos_src
                    norm1 = float(np.linalg.norm(v1))
                    norm2 = float(np.linalg.norm(v2))
                    cos_theta = float(np.dot(v1, v2) / max(norm1 * norm2, 1e-6))
                    # Reject parallel/same-direction drift using wave-adaptive gate
                    if cos_theta > gate_cos_max:
                        stats["safe_division_divergence_rejected"] += 1
                        continue
                    # If grandchildren exist on both paths, ensure they do not rapidly collide
                    if len(c1_succ) == 1 and len(q_succ) == 1:
                        c1_grandchild = nodes_by_id.get(int(c1_succ[0]["target_id"]))
                        q_grandchild = nodes_by_id.get(int(q_succ[0]["target_id"]))
                        if (
                            c1_grandchild is not None and q_grandchild is not None
                            and int(c1_grandchild["t"]) == t + 2
                            and int(q_grandchild["t"]) == t + 2
                        ):
                            grandchild_dist = edge_distance_um(c1_grandchild, q_grandchild)
                            if grandchild_dist - sister_dist < -1.0:
                                stats["safe_division_divergence_rejected"] += 1
                                continue
 
                stats["safe_division_geometric_candidates"] += 1
                if DEEPCENTER_SAFE_DIV_VETO and not deepcenter_accept_repair_point(
                    dataset,
                    int(candidate["t"]),
                    node_point(candidate),
                    deepcenter_bundle,
                    frame_cache,
                    deepcenter_cache,
                    stats,
                    "safe_div",
                    DEEPCENTER_SAFE_DIV_THRESHOLD,
                ):
                    continue
                if gate_sym_tau > 0.0:
                    _sym_denom = max((child_dist + parent_dist) / 2.0, 1e-6)
                    if abs(child_dist - parent_dist) / _sym_denom > gate_sym_tau:
                        stats["safe_division_symmetry_rejected"] += 1
                        continue
                score = parent_dist + 0.15 * sister_dist + wave_score_bias
                proposals.append((score, source_id, candidate_id, parent_dist, sister_dist))
 
        stats["safe_division_candidates"] += len(proposals)
        if not proposals:
            continue
        proposals.sort(key=lambda item: item[0])
        added_this_frame = 0
        for _, source_id, candidate_id, parent_dist, _ in proposals:
            if len(added) >= global_cap:
                stats["safe_division_skipped_cap"] += 1
                break
            if added_this_frame >= frame_cap:
                break
            if candidate_id in used_targets or candidate_id in incoming:
                continue
            if source_id in used_sources:
                continue
            candidate = nodes_by_id[candidate_id]
            added.append({
                "source_id": source_id,
                "target_id": candidate_id,
                "edge_prob": None,
                "distance_um": parent_dist,
                "safe_division": 1,
            })
            used_targets.add(candidate_id)
            used_sources.add(source_id)
            added_this_frame += 1
 
    if added:
        stats["safe_divisions_added"] = len(added)
        return [*edges, *added]
    return edges
'''

    # Replace the two functions in Cell 5
    cell_5_prefix = cell_5_src[:m_start]
    cell_5_middle = cell_5_src[gap_start:div_start]
    cell_5_suffix = cell_5_src[short_start:]

    cell_5_src_new = cell_5_prefix + new_motion_relink + "\n\n" + cell_5_middle + new_safe_div + "\n\n" + cell_5_suffix
    nb["cells"][5]["source"] = [cell_5_src_new]

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✔ Successfully patched Biohub v10 notebook with Levin Morphogenetic Field + Mitotic Wave Prior.")


if __name__ == "__main__":
    patch_notebook()
