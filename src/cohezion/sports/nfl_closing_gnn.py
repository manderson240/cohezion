#!/usr/bin/env python3
"""NFL Big Data Bowl 2027: Spatio-Temporal Closing Graph Neural Network
======================================================================
Constructs frame-level player-player and player-ball interaction graphs
from tracking data (`combine_tracking.csv` or `game_tracking_*.csv`) and
evaluates Time-to-Closest-Approach (TCA) and relative closing velocity.

Nodes:
    - Players: (x, y, vx, vy, s, a, o_sin, o_cos, dir_sin, dir_cos)
    - Ball: (x, y, vx, vy, 1.0)

Edges:
    - Directional closing vector: dx = x_j - x_i, dy = y_j - y_i
    - Distance: r_ij = sqrt(dx^2 + dy^2)
    - Relative closing velocity: v_rel = (vx_j - vx_i, vy_j - vy_i)
    - Closing rate (range rate): r_dot = (dx * dvx + dy * dvy) / max(r_ij, 1e-4)
    - Time-to-Closest-Approach (TCA):
          t_tca = - (dx * dvx + dy * dvy) / max(dvx^2 + dvy^2, 1e-4) (if r_dot < 0 else inf)
"""

import math
from typing import Dict, Any, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class PlayerInteractionGraphBuilder:
    """Builds spatial proximity and closing interaction graphs for a single play frame."""

    def __init__(self, proximity_threshold: float = 7.5, max_neighbors: int = 6):
        self.proximity_threshold = proximity_threshold
        self.max_neighbors = max_neighbors

    def build_frame_graph(
        self,
        positions: np.ndarray,      # (N, 2): x, y
        velocities: np.ndarray,     # (N, 2): vx, vy
        player_features: np.ndarray, # (N, F): e.g. speed, accel, orientation
        ball_idx: Optional[int] = None
    ) -> Dict[str, torch.Tensor]:
        N = positions.shape[0]
        nodes = np.hstack([positions, velocities, player_features])

        edge_indices = []
        edge_features = []

        for i in range(N):
            distances = []
            for j in range(N):
                if i == j:
                    continue
                dx = positions[j, 0] - positions[i, 0]
                dy = positions[j, 1] - positions[i, 1]
                dist = math.sqrt(dx * dx + dy * dy)
                dvx = velocities[j, 0] - velocities[i, 0]
                dvy = velocities[j, 1] - velocities[i, 1]

                # Range rate (closing speed if negative)
                r_dot = (dx * dvx + dy * dvy) / max(dist, 1e-4)

                # Time to Closest Approach
                v_rel_sq = dvx * dvx + dvy * dvy
                if r_dot < 0 and v_rel_sq > 1e-4:
                    tca = min(10.0, - (dx * dvx + dy * dvy) / v_rel_sq)
                else:
                    tca = 10.0

                # Connection condition: within threshold OR connects to ball
                is_ball_connection = (ball_idx is not None and (i == ball_idx or j == ball_idx))
                if dist <= self.proximity_threshold or is_ball_connection:
                    distances.append((dist, j, [dist, dx, dy, dvx, dvy, r_dot, tca]))

            # Keep top-K nearest neighbors plus ball
            distances.sort(key=lambda x: x[0])
            for dist, j, feats in distances[:self.max_neighbors]:
                edge_indices.append([i, j])
                edge_features.append(feats)

        if not edge_indices:
            # Fallback self-loop if no neighbors
            edge_indices = [[0, 0]]
            edge_features = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0]]

        return {
            "x": torch.tensor(nodes, dtype=torch.float32),
            "edge_index": torch.tensor(edge_indices, dtype=torch.long).t().contiguous(),
            "edge_attr": torch.tensor(edge_features, dtype=torch.float32),
        }


class SpatioTemporalClosingGNN(nn.Module):
    """Message passing graph network incorporating closing kinematics and TCA."""

    def __init__(self, in_node_dim: int = 6, in_edge_dim: int = 7, hidden_dim: int = 64):
        super().__init__()
        self.node_enc = nn.Linear(in_node_dim, hidden_dim)
        self.edge_enc = nn.Linear(in_edge_dim, hidden_dim)

        self.msg_fc = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.update_fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )

        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1) # Estimated closing probability / success rate
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        h_nodes = self.node_enc(x)
        h_edges = self.edge_enc(edge_attr)

        src, dst = edge_index[0], edge_index[1]
        msg_input = torch.cat([h_nodes[src], h_nodes[dst], h_edges], dim=-1)
        messages = self.msg_fc(msg_input)

        # Aggregate messages at destination nodes
        agg = torch.zeros_like(h_nodes)
        agg.index_add_(0, dst, messages)

        # Update node states
        updated = self.update_fc(torch.cat([h_nodes, agg], dim=-1))
        out = self.head(updated)
        return torch.sigmoid(out)


def test_synthetic_play():
    builder = PlayerInteractionGraphBuilder(proximity_threshold=10.0, max_neighbors=5)
    # 22 players + 1 football = 23 nodes
    N = 23
    positions = np.random.uniform(0, 100, size=(N, 2))
    velocities = np.random.uniform(-5, 5, size=(N, 2))
    player_features = np.random.uniform(0, 1, size=(N, 2))

    graph = builder.build_frame_graph(positions, velocities, player_features, ball_idx=22)
    model = SpatioTemporalClosingGNN(in_node_dim=6, in_edge_dim=7, hidden_dim=64)
    preds = model(graph["x"], graph["edge_index"], graph["edge_attr"])

    assert preds.shape == (23, 1), f"Expected shape (23, 1), got {preds.shape}"
    assert torch.all(preds >= 0.0) and torch.all(preds <= 1.0), "Probabilities must be bounded in [0, 1]"
    print(f"Synthetic frame test passed successfully! Nodes: {N}, Edges: {graph['edge_index'].shape[1]}")


if __name__ == "__main__":
    test_synthetic_play()
