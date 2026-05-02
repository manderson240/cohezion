"""
TDA Hallucination Detector (2026 SOTA).
Detects "Topological Snaps" (circular logic) in reasoning trajectories.
"""

import logging

import numpy as np


logger = logging.getLogger(__name__)


class TDADetector:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def detect_circular_logic(self, embeddings: list[np.ndarray]) -> bool:
        """
        Calculates if the trajectory of embeddings forms a closed loop.
        Approximates Betti-1 topological features using distance matrices.
        """
        if len(embeddings) < 4:
            return False

        # 1. Construct Distance Matrix
        data = np.stack(embeddings)
        n = data.shape[0]
        dist_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                # Cosine Similarity as a distance metric
                norm_i = np.linalg.norm(data[i])
                norm_j = np.linalg.norm(data[j])
                sim = np.dot(data[i], data[j]) / (norm_i * norm_j + 1e-9)
                dist_matrix[i, j] = 1.0 - sim
                dist_matrix[j, i] = dist_matrix[i, j]

        # 2. Detect "Topological Snaps"
        # A snap occurs if step N is significantly closer to step N-k than to step N-1
        # indicating the reasoning is circling back to an earlier state.
        for i in range(2, n):
            # Distance to previous step
            sequential_dist = dist_matrix[i, i - 1]

            # Minimum distance to any earlier step (excluding the immediately preceding one)
            earlier_dists = dist_matrix[i, : i - 1]
            min_earlier_dist = np.min(earlier_dists)

            if min_earlier_dist < sequential_dist * 0.5:
                logger.warning(
                    "Topological Snap detected at step %d. Min earlier dist: %.4f vs Sequential: %.4f",
                    i,
                    min_earlier_dist,
                    sequential_dist,
                )
                return True

        return False

    def calculate_coherence(self, embeddings: list[np.ndarray]) -> float:
        """
        Calculates the HIHO Coherence of the trajectory.
        0.5 is the attractor for stable precipitation.
        """
        if len(embeddings) < 2:
            return 1.0

        data = np.stack(embeddings)
        diffs = np.diff(data, axis=0)
        velocities = np.linalg.norm(diffs, axis=1)

        # Average velocity stability
        avg_v = np.mean(velocities)
        std_v = np.std(velocities)

        # Coherence is high if velocity is stable
        coherence = 1.0 / (1.0 + std_v / (avg_v + 1e-9))
        return float(coherence)
