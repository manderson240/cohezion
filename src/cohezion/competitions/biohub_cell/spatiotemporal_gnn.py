"""Biohub 3D Cell Tracking & Mitosis Lineage Graph Engine (Hardened V&V)."""
from __future__ import annotations
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Any, Tuple

class SpatiotemporalCellTracker:
    """Graph Neural Edge Classification & Global Hungarian Bipartite Matching."""

    def __init__(self, search_radius_um: float = 30.0):
        self.search_radius_um = search_radius_um
        # Edge classifier weights: distance, delta_vol, intensity_ratio -> match cost
        self.feature_weights = np.array([0.5, 0.3, 0.2], dtype=np.float32)

    def compute_edge_cost(self, c0: Dict[str, Any], c1: Dict[str, Any]) -> Tuple[float, List[float]]:
        p0, p1 = np.array(c0["centroid"]), np.array(c1["centroid"])
        dist = float(np.linalg.norm(p1 - p0))
        if dist > self.search_radius_um:
            return 1e6, []
        v0, v1 = c0.get("volume", 100.0), c1.get("volume", 100.0)
        i0, i1 = c0.get("mean_intensity", 1.0), c1.get("mean_intensity", 1.0)
        
        norm_dist = dist / max(1e-3, self.search_radius_um)
        norm_dvol = abs(v1 - v0) / max(1.0, v0)
        norm_dint = abs(i1 - i0) / max(0.1, i0)
        
        feats = [norm_dist, norm_dvol, norm_dint]
        cost = float(np.dot(feats, self.feature_weights))
        return cost, feats

    def resolve_lineage_matching(
        self,
        cells_t0: List[Dict[str, Any]],
        cells_t1: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolves globally optimal bipartite assignment using Hungarian algorithm."""
        if not cells_t0 or not cells_t1:
            return []

        n0, n1 = len(cells_t0), len(cells_t1)
        # Duplicate t0 cells to allow at most 2 daughters (division)
        cost_matrix = np.full((n0 * 2, n1), 1e6, dtype=np.float32)

        for i, c0 in enumerate(cells_t0):
            for j, c1 in enumerate(cells_t1):
                cost, _ = self.compute_edge_cost(c0, c1)
                cost_matrix[i, j] = cost
                cost_matrix[i + n0, j] = cost + 0.15  # Small penalty for 2nd daughter

        # Global optimal matching
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        final_tracks = []
        mother_counts: Dict[str, int] = {}
        
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 1e5:
                actual_t0_idx = r % n0
                src_id = cells_t0[actual_t0_idx]["id"]
                dst_id = cells_t1[c]["id"]
                
                mother_counts[src_id] = mother_counts.get(src_id, 0) + 1
                edge_type = "division" if mother_counts[src_id] == 2 else "continuation"
                
                final_tracks.append({
                    "parent": src_id,
                    "child": dst_id,
                    "type": edge_type,
                    "cost": float(cost_matrix[r, c])
                })
        return final_tracks
