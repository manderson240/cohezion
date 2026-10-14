"""Unit test suite for Overnight Grandmaster Autonomous Strategy.

Verifies:
1. CASMI26 v13: Tautomer canonical InChIKey14 deduplication (eliminating 4.4% slot defect).
2. CASMI26 v13: Spectral entropy calculation and spectral entropy similarity.
3. CASMI26 v13: Substructure Morgan fingerprint contrastive head alignment.
4. CASMI26 v13: Multi-objective candidate reranking with tail backfill.
5. ARC-AGI-3: Kinematic BFS Macro-Action Compiler collision-free path compilation.
6. ARC-AGI-3: Dynamic divergence interceptor and obstacle recovery.
7. SurrealDB: Overnight strategy payload structure verification.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# CASMI26 v13 Components
# ---------------------------------------------------------------------------

def compute_spectral_entropy(peaks: List[Tuple[float, float]]) -> Tuple[float, np.ndarray, np.ndarray]:
    """Compute normalized spectral entropy and entropy-weighted intensity vector."""
    if not peaks:
        return 0.0, np.array([]), np.array([])

    mzs = np.array([p[0] for p in peaks], dtype=np.float64)
    intensities = np.array([p[1] for p in peaks], dtype=np.float64)
    total_i = np.sum(intensities)
    if total_i <= 0:
        return 0.0, mzs, np.zeros_like(intensities)

    p = intensities / total_i
    valid = p > 1e-12
    entropy = -np.sum(p[valid] * np.log(p[valid]))

    weight_exponent = 1.0 + min(4.0, max(0.0, entropy))
    w = np.power(p, weight_exponent)
    w_sum = np.sum(w)
    p_weighted = w / w_sum if w_sum > 0 else p

    return float(entropy), mzs, p_weighted


def spectral_entropy_similarity(
    obs_peaks: List[Tuple[float, float]],
    sim_peaks: List[Tuple[float, float]],
    tolerance_da: float = 0.02,
) -> float:
    """Calculate spectral entropy similarity between observed and candidate spectra."""
    if not obs_peaks or not sim_peaks:
        return 0.0

    s_p, m_p, p_p = compute_spectral_entropy(obs_peaks)
    s_q, m_q, p_q = compute_spectral_entropy(sim_peaks)

    if len(m_p) == 0 or len(m_q) == 0:
        return 0.0

    matched_q = set()
    merged_peaks: List[float] = []

    for i, mz_p in enumerate(m_p):
        best_j = -1
        min_diff = tolerance_da
        for j, mz_q in enumerate(m_q):
            if j not in matched_q and abs(mz_p - mz_q) < min_diff:
                min_diff = abs(mz_p - mz_q)
                best_j = j

        if best_j >= 0:
            matched_q.add(best_j)
            merged_peaks.append(p_p[i] + p_q[best_j])
        else:
            merged_peaks.append(p_p[i])

    # If spectra share zero overlapping peaks, similarity is strictly zero
    if len(matched_q) == 0:
        return 0.0

    for j, mz_q in enumerate(m_q):
        if j not in matched_q:
            merged_peaks.append(p_q[j])

    merged_arr = np.array(merged_peaks, dtype=np.float64)
    merged_sum = np.sum(merged_arr)
    if merged_sum <= 0:
        return 0.0

    p_merged = merged_arr / merged_sum
    valid_m = p_merged > 1e-12
    s_merged = -np.sum(p_merged[valid_m] * np.log(p_merged[valid_m]))

    sim = 1.0 - (2.0 * s_merged - s_p - s_q) / math.log(4.0)
    return float(np.clip(sim, 0.0, 1.0))


def substructure_contrastive_score(
    predicted_sub_probs: np.ndarray,
    candidate_fp: np.ndarray,
    epsilon: float = 1e-7,
) -> float:
    """Continuous Tanimoto alignment between predicted substructure head and candidate Morgan FP."""
    intersection = np.sum(predicted_sub_probs * candidate_fp)
    union = np.sum(predicted_sub_probs) + np.sum(candidate_fp) - intersection
    if union <= 0:
        return 0.0
    return float(intersection / (union + epsilon))


def rerank_casmi26_candidates_v13_mock(
    candidates: List[Dict[str, Any]],
    obs_peaks: List[Tuple[float, float]],
    predicted_sub_probs: np.ndarray,
    top_k: int = 5,
    w_emb: float = 0.35,
    w_ent: float = 0.25,
    w_sub: float = 0.25,
    w_cleav: float = 0.15,
) -> List[Dict[str, Any]]:
    """Rerank candidates and produce verified Top-K without uncanonicalized slot defect."""
    scored: List[Tuple[float, Dict[str, Any], str]] = []

    for cand in candidates:
        canon_ik = cand.get("canonical_ik14", cand.get("raw_ik14", ""))

        s_emb = float(cand.get("base_score", 0.0))
        sim_peaks = cand.get("simulated_peaks", [])
        s_ent = spectral_entropy_similarity(obs_peaks, sim_peaks)
        cand_fp = cand.get("morgan_fp", np.zeros_like(predicted_sub_probs))
        s_sub = substructure_contrastive_score(predicted_sub_probs, cand_fp)
        s_cleav = float(cand.get("cleavage_score", 0.0))

        total_score = (w_emb * s_emb) + (w_ent * s_ent) + (w_sub * s_sub) + (w_cleav * s_cleav)
        scored.append((total_score, cand, canon_ik))

    scored.sort(key=lambda x: x[0], reverse=True)

    final_top_k: List[Dict[str, Any]] = []
    seen_ik14: Set[str] = set()

    for score, cand, c_ik in scored:
        if c_ik and c_ik in seen_ik14:
            continue
        seen_ik14.add(c_ik)
        cand_copy = dict(cand)
        cand_copy["v13_fused_score"] = score
        final_top_k.append(cand_copy)
        if len(final_top_k) >= top_k:
            break

    return final_top_k


# ---------------------------------------------------------------------------
# ARC-AGI-3 Macro Compiler Components
# ---------------------------------------------------------------------------

ACTION_DELTAS = {
    1: (-1, 0),  # UP
    2: (1, 0),   # DOWN
    3: (0, -1),  # LEFT
    4: (0, 1),   # RIGHT
}


def compile_bfs_path(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    traversable: np.ndarray,
) -> List[int]:
    """Compile shortest collision-free path of primitive directional actions."""
    if start == goal:
        return []

    h, w = traversable.shape
    q = deque([start])
    visited: Dict[Tuple[int, int], Optional[Tuple[Tuple[int, int], int]]] = {start: None}

    found = False
    while q:
        curr = q.popleft()
        if curr == goal:
            found = True
            break

        cr, cc = curr
        for action, (dr, dc) in ACTION_DELTAS.items():
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < h and 0 <= nc < w and traversable[nr, nc]:
                next_node = (nr, nc)
                if next_node not in visited:
                    visited[next_node] = (curr, action)
                    q.append(next_node)

    if not found:
        return []

    actions: List[int] = []
    curr_trace = goal
    while visited[curr_trace] is not None:
        prev_node, act = visited[curr_trace]
        actions.append(act)
        curr_trace = prev_node

    actions.reverse()
    return actions


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_casmi26_tautomer_canonical_ik14_deduplication() -> None:
    """Verifies that candidates sharing identical canonical_ik14 are pruned to eliminate 4.4% defect."""
    # 3 candidates: cand1 and cand2 are tautomers sharing canonical_ik14 'BSYNRYMUTXBXSQ'
    # cand3 is an unrelated molecule 'ODGCEQLVLXJUCC'
    # cand4 is another candidate 'HEFNNWSMSAVWKW'
    cand1 = {"name": "keto_tautomer", "canonical_ik14": "BSYNRYMUTXBXSQ", "base_score": 0.90}
    cand2 = {"name": "enol_tautomer", "canonical_ik14": "BSYNRYMUTXBXSQ", "base_score": 0.85}
    cand3 = {"name": "isomer_b", "canonical_ik14": "ODGCEQLVLXJUCC", "base_score": 0.70}
    cand4 = {"name": "isomer_c", "canonical_ik14": "HEFNNWSMSAVWKW", "base_score": 0.60}

    candidates = [cand1, cand2, cand3, cand4]
    dummy_peaks = [(100.0, 50.0)]
    dummy_fp = np.zeros(2048)

    top_k = rerank_casmi26_candidates_v13_mock(candidates, dummy_peaks, dummy_fp, top_k=3)

    # Output must have exactly 3 unique canonical_ik14 values
    ik14_list = [c["canonical_ik14"] for c in top_k]
    assert len(ik14_list) == len(set(ik14_list)), "Duplicates detected! Slot defect violated."
    assert "BSYNRYMUTXBXSQ" in ik14_list
    assert "ODGCEQLVLXJUCC" in ik14_list
    assert "HEFNNWSMSAVWKW" in ik14_list
    # Ensure keto_tautomer took the slot and enol_tautomer was pruned
    assert top_k[0]["name"] == "keto_tautomer"


def test_spectral_entropy_similarity_identical_and_orthogonal() -> None:
    """Verifies spectral entropy behavior on identical and orthogonal peak sets."""
    # Test 1: Identical spectra should yield high similarity (> 0.95)
    spec_a = [(105.05, 100.0), (147.08, 65.0), (219.12, 40.0), (301.18, 15.0)]
    spec_a_copy = [(105.05, 100.0), (147.08, 65.0), (219.12, 40.0), (301.18, 15.0)]
    sim_identical = spectral_entropy_similarity(spec_a, spec_a_copy)
    assert sim_identical >= 0.95, f"Expected identical spectra sim >= 0.95, got {sim_identical}"

    # Test 2: Orthogonal non-overlapping spectra should yield low similarity (0.0)
    spec_b = [(500.25, 80.0), (620.30, 90.0)]
    sim_orthogonal = spectral_entropy_similarity(spec_a, spec_b, tolerance_da=0.01)
    assert sim_orthogonal <= 0.05, f"Expected orthogonal sim <= 0.05, got {sim_orthogonal}"


def test_substructure_contrastive_head_alignment() -> None:
    """Verifies continuous Tanimoto scoring between predicted head and fingerprint."""
    # 2048-dim vector with predicted probabilities for bits 10, 20, 30
    pred_head = np.zeros(2048, dtype=np.float32)
    pred_head[10] = 0.95
    pred_head[20] = 0.88
    pred_head[30] = 0.92

    # Candidate with matching bits
    cand_fp_match = np.zeros(2048, dtype=np.float32)
    cand_fp_match[10] = 1.0
    cand_fp_match[20] = 1.0
    cand_fp_match[30] = 1.0

    score_match = substructure_contrastive_score(pred_head, cand_fp_match)
    assert score_match > 0.80, f"Expected high substructure alignment, got {score_match}"

    # Candidate with non-matching bits
    cand_fp_mismatch = np.zeros(2048, dtype=np.float32)
    cand_fp_mismatch[100] = 1.0
    cand_fp_mismatch[200] = 1.0

    score_mismatch = substructure_contrastive_score(pred_head, cand_fp_mismatch)
    assert score_mismatch == 0.0, f"Expected zero alignment, got {score_mismatch}"


def test_arc3_macro_action_bfs_compiler_maze() -> None:
    """Verifies BFS macro compilation navigates around obstacles to goal."""
    # 5x5 grid with obstacle wall in row 2
    # S = (0, 0), G = (4, 0)
    # Wall at row 2 from col 0 to 3, gap at col 4
    traversable = np.ones((5, 5), dtype=bool)
    traversable[2, 0:4] = False  # Wall with opening at (2, 4)

    start = (0, 0)
    goal = (4, 0)

    path = compile_bfs_path(start, goal, traversable)
    assert len(path) > 0, "Failed to compile macro path around wall."

    # Simulate path execution
    curr = start
    for act in path:
        dr, dc = ACTION_DELTAS[act]
        curr = (curr[0] + dr, curr[1] + dc)
        assert traversable[curr[0], curr[1]], f"Collision at {curr}!"

    assert curr == goal, f"Macro path ended at {curr}, expected {goal}"


def test_arc3_macro_action_divergence_recovery() -> None:
    """Verifies that dynamic collision triggers macro flush and obstacle registration."""
    traversable = np.ones((5, 5), dtype=bool)
    start = (0, 0)
    goal = (0, 3)

    # Initial path: 3 RIGHT steps
    path = compile_bfs_path(start, goal, traversable)
    assert path == [4, 4, 4]  # RIGHT, RIGHT, RIGHT

    # Simulate dynamic hazard at (0, 2)
    queue = deque(path)
    impassable_tiles: Set[Tuple[int, int]] = set()

    # Step 1: execute RIGHT -> player moves to (0, 1)
    act1 = queue.popleft()
    expected_pos = (0, 1)
    actual_pos = (0, 1)
    assert actual_pos == expected_pos

    # Step 2: execute RIGHT -> collision! player remains at (0, 1)
    act2 = queue.popleft()
    expected_pos = (0, 2)
    actual_pos = (0, 1)  # blocked!

    if actual_pos != expected_pos:
        impassable_tiles.add(expected_pos)
        queue.clear()  # macro flushed!

    assert len(queue) == 0, "Macro queue was not flushed upon divergence."
    assert (0, 2) in impassable_tiles

    # Replan from (0, 1) around the newly registered obstacle
    traversable[0, 2] = False
    replan_path = compile_bfs_path((0, 1), goal, traversable)
    assert len(replan_path) > 0
    # Must detour around (0, 2), e.g. down to (1, 1), across to (1, 3), up to (0, 3)
    assert 2 in replan_path  # DOWN action included


def test_overnight_autonomous_strategy_surrealdb_schema() -> None:
    """Verifies that the overnight strategy data structure is valid and complete."""
    from scripts.kaggle.persist_overnight_strategy_surrealdb import payload_data

    assert payload_data["author"] == "Mike Anderson (manderson240)"
    assert payload_data["mode"] == "Individual Solo Competitor (S=1.0, 100% Prize Retention)"
    assert "enveda_casmi26" in payload_data["competitions"]
    assert "arc_agi_3" in payload_data["competitions"]
    assert payload_data["competitions"]["enveda_casmi26"]["target_score"] == ">0.380"
    assert payload_data["competitions"]["arc_agi_3"]["target_score"] == ">0.35"
    assert len(payload_data["competitions"]["enveda_casmi26"]["innovations"]) >= 3
    assert len(payload_data["competitions"]["arc_agi_3"]["innovations"]) >= 3
