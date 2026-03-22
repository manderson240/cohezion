from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np

from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


class DriftAnalyzer:
    """Analyzes 12D manifold trajectories for drift signatures."""

    def __init__(self, db: SurrealClient | None = None):
        self.db = db or SurrealClient()
        self.coherence_threshold = 0.5
        self.drift_threshold = 0.15  # KL Divergence trigger

    async def fetch_trajectory(self, limit: int = 1000) -> list[np.ndarray]:
        """Fetches points from universe_nodes and converts to numpy vectors."""
        # Security: Use parameterized query instead of f-string to prevent injection
        query = "SELECT physics_state FROM universe_nodes LIMIT $limit"
        res = await self.db.query(query, {"limit": limit})

        vectors = []
        for row in res:
            ps = row.get("physics_state", {})
            # Extract 12 dimensions
            vec = [
                ps.get("dim_1_x", 0),
                ps.get("dim_2_y", 0),
                ps.get("dim_3_z", 0),
                ps.get("dim_4_time", 0),
                ps.get("dim_5_physics", 0),
                ps.get("dim_6_biology", 0),
                ps.get("dim_7_logic", 0),
                ps.get("dim_8_quantum", 0),
                ps.get("dim_9_field", 0),
                ps.get("dim_10_control", 0),
                ps.get("dim_11_novelty", 0),
                ps.get("dim_12_precipitation", 0),
            ]
            vectors.append(np.array(vec))
        return vectors

    def calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Simple KL Divergence approximation between two 12D states."""
        # Ensure non-zero for log
        p = np.clip(p, 1e-10, 1.0)
        q = np.clip(q, 1e-10, 1.0)
        # Normalize to probability distributions
        p = p / np.sum(p)
        q = q / np.sum(q)
        return np.sum(p * np.log(p / q))

    async def detect_knots(self, sample_size: int = 1000) -> list[dict[str, Any]]:
        """Identifies regions of high divergence (Topological Knots)."""
        vectors = await self.fetch_trajectory(sample_size)
        if len(vectors) < 2:
            return []

        knots = []
        # Compare sequential points for velocity/drift spikes
        for i in range(1, len(vectors)):
            div = self.calculate_kl_divergence(vectors[i - 1], vectors[i])
            if div > self.drift_threshold:
                knots.append(
                    {
                        "index": i,
                        "divergence": div,
                        "vector": vectors[i].tolist(),
                        "severity": "high" if div > 0.3 else "medium",
                    }
                )

        logger.info(f"Analysis complete. Found {len(knots)} knots in {sample_size} points.")
        return knots

    async def classify_stability(self, vector: np.ndarray) -> str:
        """Classifies a single state using the 0.5 HIHO rule."""
        # Primary indicators: Control (dim 10) and Precipitation (dim 12)
        control = vector[9]
        precipitation = vector[11]
        stability = (control + precipitation) / 2

        if abs(stability - self.coherence_threshold) < 0.05:
            return "STABLE (0.5 HIHO)"
        if stability < self.coherence_threshold:
            return "DEGRADING (UNDER-STABLE)"
        return "VOLATILE (OVER-STABLE)"


if __name__ == "__main__":

    async def test():
        analyzer = DriftAnalyzer()
        await analyzer.db.connect()
        knots = await analyzer.detect_knots(100)
        for knot in knots[:5]:
            print(f"Knot at {knot['index']}: Div={knot['divergence']:.4f}")
        await analyzer.db.close()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test())
