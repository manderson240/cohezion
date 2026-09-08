"""Curvature-Adaptive Test-Time Training (CA-TTT) & Hyperbolic Consensus Engine.

Dynamically optimizes latent manifold curvature $c < 0$ and applies Search-Tree-Weighted
Self-Consistency (STWSC) over hyperbolic embeddings.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class CurvatureAdaptiveTTT:
    """Jointly adapts latent curvature and computes manifold-weighted consensus."""

    def __init__(self, initial_curvature: float = 1.0, embedding_dim: int = 16):
        self.curvature = max(1e-4, float(initial_curvature))
        self.embedding_dim = embedding_dim

    def compute_distance(self, u: np.ndarray, v: np.ndarray, eps: float = 1e-5) -> float:
        """Calculates Poincaré distance under current curvature: d_P^c(u, v)."""
        u_vec = np.array(u, dtype=np.float32)
        v_vec = np.array(v, dtype=np.float32)

        # Conformal ball radius bound: ||x|| < 1 / sqrt(c)
        r_max = (1.0 / np.sqrt(self.curvature)) - eps
        u_norm = np.linalg.norm(u_vec)
        v_norm = np.linalg.norm(v_vec)

        if u_norm >= r_max:
            u_vec = u_vec * (r_max / (u_norm + eps))
        if v_norm >= r_max:
            v_vec = v_vec * (r_max / (v_norm + eps))

        diff_sq = np.sum((u_vec - v_vec) ** 2)
        u_sq = np.sum(u_vec**2)
        v_sq = np.sum(v_vec**2)

        denom = (1.0 - self.curvature * u_sq) * (1.0 - self.curvature * v_sq)
        denom_f = max(1e-8, float(denom))

        delta = 1.0 + (2.0 * self.curvature * diff_sq) / denom_f
        delta = max(1.0 + eps, delta)

        return float((1.0 / np.sqrt(self.curvature)) * np.arccosh(delta))

    def adapt_curvature_from_entropy(
        self, candidate_embeddings: list[np.ndarray], target_density: float = 0.5
    ) -> float:
        """Test-Time Training step: tunes curvature c to match the intrinsic hierarchical depth."""
        if len(candidate_embeddings) < 2:
            return self.curvature

        # Compute pairwise distance matrix
        dists = []
        n = len(candidate_embeddings)
        for i in range(n):
            for j in range(i + 1, n):
                dists.append(
                    self.compute_distance(candidate_embeddings[i], candidate_embeddings[j])
                )

        mean_dist = float(np.mean(dists)) if dists else 1.0
        # If points are too clustered, increase negative curvature to expand hierarchical space
        if mean_dist < target_density:
            self.curvature = min(10.0, self.curvature * 1.2)
        elif mean_dist > (target_density * 3.0):
            self.curvature = max(0.01, self.curvature * 0.8)

        return self.curvature

    def search_tree_weighted_consensus(
        self, candidate_records: list[dict[str, Any]]
    ) -> tuple[Any, float]:
        """Performs Search-Tree-Weighted Self-Consistency (STWSC) over hyperbolic clusters."""
        if not candidate_records:
            return None, 0.0

        scores: dict[Any, float] = {}
        total_score = 0.0

        for cand in candidate_records:
            ans = cand.get("answer")
            visits = float(cand.get("visits", 1.0))
            emb = np.array(cand.get("embedding", np.zeros(self.embedding_dim)), dtype=np.float32)

            # Hyperbolic cluster density
            density = 0.0
            for other in candidate_records:
                other_emb = np.array(
                    other.get("embedding", np.zeros(self.embedding_dim)), dtype=np.float32
                )
                d = self.compute_distance(emb, other_emb)
                density += np.exp(-d)

            cand_weight = visits * density
            scores[ans] = scores.get(ans, 0.0) + cand_weight
            total_score += cand_weight

        best_ans = max(scores.items(), key=lambda x: x[1])[0]
        confidence = float(scores[best_ans] / max(1e-8, total_score))
        return best_ans, confidence
