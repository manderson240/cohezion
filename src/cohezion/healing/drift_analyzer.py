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


class PredictiveApertureForecaster:
    """Predictive trajectory forecaster for AMD Strix Halo 120GB UMA aperture.

    Uses an autoregressive moving-velocity estimator to forecast memory consumption
    15 minutes ahead, detecting aperture exhaustion before kernel GPU resets or OOM panics occur.
    """

    def __init__(
        self,
        max_aperture_gb: float = 120.0,
        warning_threshold_gb: float = 110.0,
        critical_threshold_gb: float = 115.0,
        history_window: int = 30,
    ) -> None:
        self.max_aperture_gb = max_aperture_gb
        self.warning_threshold_gb = warning_threshold_gb
        self.critical_threshold_gb = critical_threshold_gb
        self.history_window = history_window
        # Deque of (timestamp_sec, used_gb, swap_used_gb)
        self.history: list[tuple[float, float, float]] = []

    def record_observation(self, timestamp_sec: float, used_gb: float, swap_used_gb: float) -> None:
        """Records a point observation of host memory utilization."""
        self.history.append((timestamp_sec, used_gb, swap_used_gb))
        if len(self.history) > self.history_window:
            self.history.pop(0)

    def forecast_trajectory(self, horizon_minutes: float = 15.0) -> dict[str, Any]:
        """Calculates drift velocity and forecasts memory consumption at t + horizon.

        Returns a dictionary containing velocity (GB/min), projected_gb, and alert status.
        """
        if len(self.history) < 2:
            current = self.history[-1][1] if self.history else 0.0
            return {
                "status": "INSUFFICIENT_DATA",
                "current_gb": current,
                "projected_gb": current,
                "velocity_gb_per_min": 0.0,
                "recommendation": "COLLECT_MORE_TELEMETRY",
            }

        t_start, u_start, _ = self.history[0]
        t_end, u_end, swap_end = self.history[-1]
        dt_minutes = max(1e-4, (t_end - t_start) / 60.0)

        # Robust linear drift slope (least squares over recent window)
        t_rel = np.array([(t - t_start) / 60.0 for t, _, _ in self.history])
        u_arr = np.array([u for _, u, _ in self.history])

        if len(self.history) >= 3 and np.std(t_rel) > 1e-4:
            # y = m * x + c
            slope, intercept = np.polyfit(t_rel, u_arr, 1)
            velocity_gb_min = float(slope)
        else:
            velocity_gb_min = (u_end - u_start) / dt_minutes

        projected_gb = u_end + velocity_gb_min * horizon_minutes

        if projected_gb >= self.critical_threshold_gb and velocity_gb_min > 0.1:
            status = "CRITICAL_APERTURE_SPIKE"
            rec = "TRIGGER_PROACTIVE_EVICTION_AND_HOTSWAP"
        elif projected_gb >= self.warning_threshold_gb and velocity_gb_min > 0.05:
            status = "WARNING_DRIFT_DETECTED"
            rec = "THROTTLE_BACKGROUND_SWARMS"
        else:
            status = "NOMINAL_STABLE"
            rec = "MAINTAIN_CURRENT_CADENCE"

        return {
            "status": status,
            "current_gb": round(float(u_end), 2),
            "swap_used_gb": round(float(swap_end), 2),
            "velocity_gb_per_min": round(velocity_gb_min, 4),
            "projected_gb": round(float(projected_gb), 2),
            "horizon_minutes": horizon_minutes,
            "recommendation": rec,
        }


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
