"""Generic Spatiotemporal Tracking-by-Detection Engine.

Implements the abstracted principles from the Biohub 1st Place solution:
1. Frame-to-frame bipartite association via Hungarian linear assignment.
2. Distance gating and trajectory forecasting.
3. Mitotic lineage branching detection via Center-of-Mass (COM) conservation.
4. Noise persistence filtering (pruning transient spurious tracks).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    from scipy.optimize import linear_sum_assignment  # type: ignore
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from cohezion.tracking.protocols import AssociationPolicy, Detection
from cohezion.tracking.swarm_state import SwarmState, Track

logger = logging.getLogger(__name__)


class EuclideanAssociationPolicy(AssociationPolicy):
    """Euclidean distance bipartite matching with distance threshold gating."""

    def compute_cost_matrix(
        self,
        predicted_positions: np.ndarray,
        detection_positions: np.ndarray,
    ) -> np.ndarray:
        if len(predicted_positions) == 0 or len(detection_positions) == 0:
            return np.empty((len(predicted_positions), len(detection_positions)))
        diff = predicted_positions[:, np.newaxis, :] - detection_positions[np.newaxis, :, :]
        return np.linalg.norm(diff, axis=-1)

    def associate(
        self,
        cost_matrix: np.ndarray,
        max_distance: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        N, M = cost_matrix.shape
        if N == 0:
            return [], [], list(range(M))
        if M == 0:
            return [], list(range(N)), []

        if HAS_SCIPY:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
        else:
            # Greedy nearest neighbor fallback
            row_ind, col_ind = self._greedy_assignment(cost_matrix)

        matches: List[Tuple[int, int]] = []
        unmatched_tracks = set(range(N))
        unmatched_detections = set(range(M))

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] <= max_distance:
                matches.append((int(r), int(c)))
                unmatched_tracks.discard(int(r))
                unmatched_detections.discard(int(c))

        return matches, sorted(list(unmatched_tracks)), sorted(list(unmatched_detections))

    def _greedy_assignment(self, cost_matrix: np.ndarray) -> Tuple[List[int], List[int]]:
        cost_copy = cost_matrix.copy()
        N, M = cost_copy.shape
        row_ind, col_ind = [], []
        used_rows, used_cols = set(), set()

        for _ in range(min(N, M)):
            min_val = np.inf
            best_r, best_c = -1, -1
            for r in range(N):
                if r in used_rows:
                    continue
                for c in range(M):
                    if c in used_cols:
                        continue
                    if cost_copy[r, c] < min_val:
                        min_val = cost_copy[r, c]
                        best_r, best_c = r, c
            if best_r != -1 and best_c != -1:
                row_ind.append(best_r)
                col_ind.append(best_c)
                used_rows.add(best_r)
                used_cols.add(best_c)
        return row_ind, col_ind


class TrackingByDetectionEngine:
    """Orchestrates persistent multi-entity tracking over time."""

    def __init__(
        self,
        max_distance: float = 10.0,
        max_misses: int = 3,
        min_hits: int = 2,
        mitosis_epsilon: float = 3.5,
        mitosis_daughter_separation: float = 3.5,
        association_policy: Optional[AssociationPolicy] = None,
    ) -> None:
        self.max_distance = max_distance
        self.max_misses = max_misses
        self.min_hits = min_hits
        self.mitosis_epsilon = mitosis_epsilon
        self.mitosis_daughter_separation = mitosis_daughter_separation
        self.association_policy = association_policy or EuclideanAssociationPolicy()

        self.tracks: Dict[str, Track] = {}
        self.pruned_noise_tracks: List[str] = []
        self.current_state: Optional[SwarmState] = None

    def step(self, detections: List[Detection], timestamp: float) -> SwarmState:
        """Processes detections at timestamp t and updates swarm tracks."""
        active_track_ids = [
            tid for tid, trk in self.tracks.items() if trk.is_active
        ]
        
        # 1. State Prediction
        predicted_positions = []
        for tid in active_track_ids:
            trk = self.tracks[tid]
            dt = max(1e-6, timestamp - trk.current_timestamp)
            pred = trk.position + trk.velocity * dt
            predicted_positions.append(pred)

        pred_arr = (
            np.stack(predicted_positions, axis=0)
            if predicted_positions
            else np.empty((0, 3 if detections else 0))
        )
        det_arr = (
            np.stack([d.position for d in detections], axis=0)
            if detections
            else np.empty((0, pred_arr.shape[1] if pred_arr.size else 0))
        )

        # 2. Association
        if len(pred_arr) > 0 and len(det_arr) > 0:
            cost_mat = self.association_policy.compute_cost_matrix(pred_arr, det_arr)
            matches, unmatched_t_idx, unmatched_d_idx = self.association_policy.associate(
                cost_mat, self.max_distance
            )
        else:
            matches = []
            unmatched_t_idx = list(range(len(active_track_ids)))
            unmatched_d_idx = list(range(len(detections)))

        # 3. Update Matched Tracks
        for t_idx, d_idx in matches:
            track_id = active_track_ids[t_idx]
            det = detections[d_idx]
            self.tracks[track_id].update(
                det.position,
                timestamp,
                metadata={"confidence": det.confidence, "entity_type": det.entity_type, **det.metadata},
            )

        # 4. Handle Unmatched Tracks (Misses)
        newly_terminated_tracks = []
        for t_idx in unmatched_t_idx:
            track_id = active_track_ids[t_idx]
            trk = self.tracks[track_id]
            trk.mark_missed(timestamp)
            if trk.consecutive_misses > self.max_misses:
                trk.is_active = False
                newly_terminated_tracks.append(track_id)
                # Filter out short noise tracks
                if trk.total_hits < self.min_hits:
                    self.pruned_noise_tracks.append(track_id)

        # 5. Check for Mitotic Split / Lineage Branching
        # When a track goes missing or terminates and 2 unmatched detections appear that satisfy COM conservation
        candidate_parents = [self.tracks[tid] for tid in newly_terminated_tracks]
        lineage_events = []
        assigned_daughter_indices = set()

        if len(unmatched_d_idx) >= 2 and candidate_parents:
            for parent in candidate_parents:
                parent_pos = parent.position
                best_pair = None
                best_com_dist = float("inf")

                for i in range(len(unmatched_d_idx)):
                    if i in assigned_daughter_indices:
                        continue
                    d1_idx = unmatched_d_idx[i]
                    d1 = detections[d1_idx]

                    for j in range(i + 1, len(unmatched_d_idx)):
                        if j in assigned_daughter_indices:
                            continue
                        d2_idx = unmatched_d_idx[j]
                        d2 = detections[d2_idx]

                        # Check daughter repulsion
                        separation = np.linalg.norm(d1.position - d2.position)
                        if separation < self.mitosis_daughter_separation:
                            continue

                        # Check center of mass conservation
                        m1 = max(1e-3, d1.intensity_or_mass)
                        m2 = max(1e-3, d2.intensity_or_mass)
                        com = (m1 * d1.position + m2 * d2.position) / (m1 + m2)
                        com_dist = float(np.linalg.norm(com - parent_pos))

                        if com_dist <= self.mitosis_epsilon and com_dist < best_com_dist:
                            best_com_dist = com_dist
                            best_pair = (i, j, d1_idx, d2_idx)

                if best_pair is not None:
                    i, j, d1_idx, d2_idx = best_pair
                    assigned_daughter_indices.add(i)
                    assigned_daughter_indices.add(j)

                    # Spawn daughter tracks linked to parent
                    d1 = detections[d1_idx]
                    d2 = detections[d2_idx]
                    t1_id = f"trk_{uuid.uuid4().hex[:8]}"
                    t2_id = f"trk_{uuid.uuid4().hex[:8]}"

                    parent.children_track_ids.extend([t1_id, t2_id])

                    t1 = Track(
                        track_id=t1_id,
                        initial_timestamp=timestamp,
                        current_timestamp=timestamp,
                        position=d1.position.copy(),
                        velocity=np.zeros_like(d1.position),
                        history=[d1.position.copy()],
                        timestamps=[timestamp],
                        parent_track_id=parent.track_id,
                        metadata=d1.metadata,
                    )
                    t2 = Track(
                        track_id=t2_id,
                        initial_timestamp=timestamp,
                        current_timestamp=timestamp,
                        position=d2.position.copy(),
                        velocity=np.zeros_like(d2.position),
                        history=[d2.position.copy()],
                        timestamps=[timestamp],
                        parent_track_id=parent.track_id,
                        metadata=d2.metadata,
                    )
                    self.tracks[t1_id] = t1
                    self.tracks[t2_id] = t2

                    lineage_events.append({
                        "event_type": "mitosis",
                        "parent_track_id": parent.track_id,
                        "children_track_ids": [t1_id, t2_id],
                        "timestamp": timestamp,
                        "com_error": best_com_dist,
                    })

        # 6. Spawn New Tracks for remaining unmatched detections
        for idx_pos, d_idx in enumerate(unmatched_d_idx):
            if idx_pos in assigned_daughter_indices:
                continue
            det = detections[d_idx]
            new_id = f"trk_{uuid.uuid4().hex[:8]}"
            new_track = Track(
                track_id=new_id,
                initial_timestamp=timestamp,
                current_timestamp=timestamp,
                position=det.position.copy(),
                velocity=np.zeros_like(det.position),
                history=[det.position.copy()],
                timestamps=[timestamp],
                metadata={"confidence": det.confidence, "entity_type": det.entity_type, **det.metadata},
            )
            self.tracks[new_id] = new_track

        # 7. Formulate Current SwarmState
        state = SwarmState(
            timestamp=timestamp,
            tracks=self.tracks,
            lineage_events=lineage_events,
        )
        self.current_state = state
        return state
