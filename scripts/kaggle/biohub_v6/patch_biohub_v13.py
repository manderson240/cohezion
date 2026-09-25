#!/usr/bin/env python3
"""Patches cohezion-biohub-v6.ipynb to Biohub v13 SOTA:
- BIOHUB_PRESET = 'harmonic_v13_reciprocal_cycle_mass_conserving'
- BIOHUB_SCORE_AXIS = 'v13 Levin Field + Reciprocal Cycle Consistency + Mitotic COM Invariant (LB target 0.972+)'
- Bi-directional Reciprocal Hungarian Matching in motion_relink_edges:
    Computes forward and backward Hungarian assignments.
    Cycle-inconsistent links pruned unless high confidence.
- Mitotic Center-of-Mass Fission Invariant in add_safe_divisions_postlink:
    Midpoint of daughters cannot drift far from mother position (com_drift <= 3.8 um).
    Mitotic wave density weighting relaxes/tightens division gates.
- Bulletproof DefaultDict stats in run_clean_pipeline:
    Wraps stats in collections.defaultdict(int) so missing keys never trigger KeyError.
    Aligns safe_divisions_added with pipeline reporting.
"""

import ast
import json
import re
import subprocess
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")


def create_v13_patch():
    # Load clean base from git HEAD
    raw_head = subprocess.check_output(
        ["git", "show", "HEAD:scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb"],
        encoding="utf-8",
    )
    nb = json.loads(raw_head)

    # 1. Patch Cell 0 (Preset and Axis naming)
    cell_0_src = "".join(nb["cells"][0]["source"])
    cell_0_src = re.sub(
        r"BIOHUB_PRESET = '.*?'",
        "BIOHUB_PRESET = 'harmonic_v13_reciprocal_cycle_mass_conserving'",
        cell_0_src,
    )
    cell_0_src = re.sub(
        r"BIOHUB_SCORE_AXIS = '.*?'",
        "BIOHUB_SCORE_AXIS = 'v13 Levin Field + Reciprocal Cycle Consistency + Mitotic COM Invariant (LB target 0.972+)'",
        cell_0_src,
    )
    nb["cells"][0]["source"] = [cell_0_src]

    # 2. Patch Cell 5
    cell_5_src = "".join(nb["cells"][5]["source"])

    # Locate function boundaries
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

    ids_by_t: dict[int, list[int]] = {}
    position_um: dict[int, np.ndarray] = {}
    for node_id, node in nodes_by_id.items():
        t = int(node["t"])
        ids_by_t.setdefault(t, []).append(node_id)
        position_um[node_id] = _position_um(node)

    for t_nodes in ids_by_t.values():
        t_nodes.sort()

    predecessor_position_um: dict[int, np.ndarray] = {}
    selected_edges: list[dict[str, object]] = []

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
        require_reciprocity: bool = False,
    ) -> list[tuple[int, int, float, float, float]]:
        if not source_ids or not target_ids:
            return []

        big = 1e6
        cost = np.full((len(source_ids), len(target_ids)), big, dtype=np.float64)
        raw_dist = np.zeros_like(cost)
        motion_dist = np.zeros_like(cost)
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
                prob = learned_edge_probs.get((source_id, target_id), 0.0)
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

        # Backward Hungarian for Bidirectional Cycle Consistency
        rev_match: dict[int, int] = {}
        if require_reciprocity and len(source_ids) > 1 and len(target_ids) > 1:
            rev_row, rev_col = linear_sum_assignment(cost.T)
            for target_idx, source_idx in zip(rev_row, rev_col):
                if cost.T[target_idx, source_idx] < big:
                    rev_match[int(target_idx)] = int(source_idx)

        matches: list[tuple[int, int, float, float, float]] = []
        for r, c in zip(row_ind, col_ind):
            if cost[r, c] >= big:
                continue
            r_int, c_int = int(r), int(c)
            # Cycle consistency check
            if require_reciprocity and rev_match:
                if rev_match.get(c_int) != r_int:
                    if raw_dist[r, c] > 4.5 and prob_matrix[r, c] < 0.65:
                        stats["motion_relink_cycle_inconsistent_pruned"] = (
                            stats.get("motion_relink_cycle_inconsistent_pruned", 0) + 1
                        )
                        continue
            matches.append((
                source_ids[r_int],
                target_ids[c_int],
                float(raw_dist[r, c]),
                float(motion_dist[r, c]),
                float(prob_matrix[r, c]),
            ))
        return matches

    for t in sorted(ids_by_t):
        source_ids = ids_by_t.get(t, [])
        target_ids = ids_by_t.get(t + 1, [])
        if not source_ids or not target_ids:
            continue
        unmatched_sources = set(source_ids)
        unmatched_targets = set(target_ids)
        v_pred_map = compute_levin_morphogenetic_field(source_ids) if use_levin else None

        frame_matches: list[tuple[int, int, float, float, str, float]] = []
        for pass_name, gate_um, req_recip in (
            ("tight", MOTION_RELINK_TIGHT_UM, True),
            ("relaxed", MOTION_RELINK_RELAXED_UM, False),
        ):
            pass_sources = [node_id for node_id in source_ids if node_id in unmatched_sources]
            pass_targets = [node_id for node_id in target_ids if node_id in unmatched_targets]
            matches = assign_pass(
                pass_sources,
                pass_targets,
                gate_um,
                v_pred_map=v_pred_map,
                require_reciprocity=req_recip,
            )
            for source_id, target_id, raw, motion, prob in matches:
                unmatched_sources.discard(source_id)
                unmatched_targets.discard(target_id)
                frame_matches.append((source_id, target_id, raw, motion, pass_name, prob))

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

    stats["motion_relink_edges"] = len(selected_edges)
    return selected_edges
'''

    new_safe_divisions = '''def add_safe_divisions_postlink(
    nodes_by_id: dict[int, dict[str, object]],
    edges: list[dict[str, object]],
    stats: dict[str, int],
    dataset: str | None = None,
    deepcenter_bundle: dict[str, object] | None = None,
    frame_cache: dict[int, np.ndarray] | None = None,
    deepcenter_cache: dict[tuple[str, int], np.ndarray] | None = None,
    max_components_per_frame: int = 1400,
) -> list[dict[str, object]]:
    if not OUTPUT_SAFE_DIVISIONS or not edges:
        return edges
    frame_cache = frame_cache if frame_cache is not None else {}
    deepcenter_cache = deepcenter_cache if deepcenter_cache is not None else {}

    def edge_distance_um(source: dict[str, object], target: dict[str, object]) -> float:
        p0 = _position_um(source)
        p1 = _position_um(target)
        return float(np.linalg.norm(p0 - p1))

    existing_edges = {(int(e["source_id"]), int(e["target_id"])) for e in edges}
    out_by_source: dict[int, list[dict[str, object]]] = {}
    in_by_target: dict[int, list[dict[str, object]]] = {}
    for edge in edges:
        source_id = int(edge["source_id"])
        target_id = int(edge["target_id"])
        out_by_source.setdefault(source_id, []).append(edge)
        in_by_target.setdefault(target_id, []).append(edge)

    ids_by_t: dict[int, list[int]] = {}
    for node_id, node in nodes_by_id.items():
        ids_by_t.setdefault(int(node["t"]), []).append(node_id)
    for ids in ids_by_t.values():
        ids.sort()

    added_edges: list[dict[str, object]] = []

    for t in sorted(ids_by_t):
        frame_nodes = ids_by_t.get(t, [])
        next_nodes = ids_by_t.get(t + 1, [])
        if not frame_nodes or not next_nodes:
            continue
        source_ids = [node_id for node_id in frame_nodes if len(out_by_source.get(node_id, [])) == 1]
        candidate_ids = [node_id for node_id in next_nodes if node_id not in in_by_target]
        if not source_ids or not candidate_ids:
            continue
        if len(candidate_ids) > max_components_per_frame:
            stats["safe_division_skipped_dense_frame"] = (
                stats.get("safe_division_skipped_dense_frame", 0) + 1
            )
            continue

        candidate_positions = np.stack([_position_um(nodes_by_id[cid]) for cid in candidate_ids])
        candidate_tree = cKDTree(candidate_positions) if len(candidate_ids) >= 1 else None

        # Mitotic wave density calculation
        def compute_w_wave(src_id: int) -> float:
            pos_src = _position_um(nodes_by_id[src_id])
            nearby_mothers = 0
            for other_src in source_ids:
                if other_src != src_id:
                    d = float(np.linalg.norm(_position_um(nodes_by_id[other_src]) - pos_src))
                    if d <= 25.0:
                        nearby_mothers += 1
            return float(nearby_mothers / 6.0)

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
                gate_parent_max = SAFE_DIV_MAX_UM * 1.15
                gate_sister_max = SAFE_DIV_SISTER_MAX_UM * 1.15
                gate_cos_max = 0.55
                gate_sym_tau = SAFE_DIV_SISTER_SYMMETRY_TAU * 1.25
                wave_score_bias = -1.5 * min(w_wave, 2.0)
            else:
                gate_parent_max = SAFE_DIV_MAX_UM * 0.85
                gate_sister_max = SAFE_DIV_SISTER_MAX_UM * 0.85
                gate_cos_max = 0.30
                gate_sym_tau = SAFE_DIV_SISTER_SYMMETRY_TAU * 0.85
                wave_score_bias = +3.0 * (0.30 - w_wave)

            pos_src = _position_um(source)
            pos_c1 = _position_um(existing_child)

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

                # Mutual nearest orphan check
                if SAFE_DIV_REQUIRE_MUTUAL_NN and candidate_id != mutual_nn_id:
                    stats["safe_division_mutual_nn_rejected"] = (
                        stats.get("safe_division_mutual_nn_rejected", 0) + 1
                    )
                    continue

                pos_cand = _position_um(candidate)

                # Center-of-Mass / Momentum Conservation in Mitotic Fission
                daughter_midpoint = 0.5 * (pos_c1 + pos_cand)
                com_drift = float(np.linalg.norm(daughter_midpoint - pos_src))
                if com_drift > 3.8:
                    stats["safe_division_com_drift_rejected"] = (
                        stats.get("safe_division_com_drift_rejected", 0) + 1
                    )
                    continue

                if SAFE_DIV_REQUIRE_DIVERGENCE:
                    c1_succ = out_by_source.get(existing_child_id, [])
                    q_succ = out_by_source.get(candidate_id, [])
                    v1 = pos_c1 - pos_src
                    v2 = pos_cand - pos_src
                    norm1 = float(np.linalg.norm(v1))
                    norm2 = float(np.linalg.norm(v2))
                    cos_theta = float(np.dot(v1, v2) / max(norm1 * norm2, 1e-6))
                    if cos_theta > gate_cos_max:
                        stats["safe_division_divergence_rejected"] = (
                            stats.get("safe_division_divergence_rejected", 0) + 1
                        )
                        continue
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
                                stats["safe_division_divergence_rejected"] = (
                                    stats.get("safe_division_divergence_rejected", 0) + 1
                                )
                                continue

                stats["safe_division_geometric_candidates"] = (
                    stats.get("safe_division_geometric_candidates", 0) + 1
                )
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
                        stats["safe_division_symmetry_rejected"] = (
                            stats.get("safe_division_symmetry_rejected", 0) + 1
                        )
                        continue

                score = parent_dist + 0.15 * sister_dist + 0.5 * com_drift + wave_score_bias
                proposals.append((score, source_id, candidate_id, parent_dist, sister_dist))

        if not proposals:
            continue
        stats["safe_division_candidates"] = (
            stats.get("safe_division_candidates", 0) + len(proposals)
        )
        proposals.sort(key=lambda item: item[0])
        used_sources: set[int] = set()
        used_candidates: set[int] = set()
        for score, source_id, candidate_id, parent_dist, sister_dist in proposals:
            if len(used_sources) >= frame_cap:
                break
            if source_id in used_sources or candidate_id in used_candidates:
                continue
            used_sources.add(source_id)
            used_candidates.add(candidate_id)
            edge = {
                "source_id": source_id,
                "target_id": candidate_id,
                "distance_um": parent_dist,
                "sister_distance_um": sister_dist,
                "safe_division": 1,
                "safe_division_score": score,
            }
            added_edges.append(edge)
            out_by_source.setdefault(source_id, []).append(edge)
            in_by_target.setdefault(candidate_id, []).append(edge)
            existing_edges.add((source_id, candidate_id))

    stats["safe_divisions_added"] = (
        stats.get("safe_divisions_added", 0) + len(added_edges)
    )
    return edges + added_edges
'''

    tail_src = cell_5_src[short_start:]
    tail_src = tail_src.replace(
        "    stats = {",
        "    import collections\n    stats = collections.defaultdict(int, {",
        1,
    )
    # And close the defaultdict with extra safety keys
    tail_src = tail_src.replace(
        '        "linefit_skipped_nodes": 0,\n    }',
        '        "linefit_skipped_nodes": 0,\n        "safe_division_skipped_dense_frame": 0,\n        "safe_division_com_drift_rejected": 0,\n        "motion_relink_cycle_inconsistent_pruned": 0,\n    })',
        1,
    )

    # Assemble Cell 5
    new_cell_5 = (
        cell_5_src[:m_start]
        + new_motion_relink
        + "\n\n"
        + cell_5_src[gap_start:div_start]
        + new_safe_divisions
        + "\n\n"
        + tail_src
    )
    nb["cells"][5]["source"] = [new_cell_5]

    # Validate AST of all code cells
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            try:
                ast.parse(src)
            except SyntaxError as e:
                raise SyntaxError(f"AST validation failed in Cell {idx}: {e}")

    print("✔ All 10 cells successfully passed AST validation!")

    output_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"Successfully generated Biohub v13 SOTA notebook at: {output_path}")


if __name__ == "__main__":
    create_v13_patch()
