"""Journey tracking for compound executions with 12D FLUME trajectories.

Maps compound execution quality metrics to 12D FLUME axiomatic trajectories
using semantic embeddings and operation-specific modulation profiles.

Lifecycle:
  1. Extract execution metrics (coherence, efficiency, duration)
  2. Generate semantic embedding from task description
  3. Project to 12D using holographic method (2048D → 12D)
  4. Apply operation-specific modulation (generate/analyze/search/etc)
  5. Compute trajectory quality score (coherence*0.5 + smoothness*0.3 + convergence*0.2)
  6. Persist journey point for experience-guided execution

Features:
- Deterministic 12D trajectory representation
- Operation-aware modulation profiles
- Holographic projection fallback (pure Python, no dependencies)
- Comprehensive trajectory quality metrics
- Experience guidance for future runs
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.holographic_projection import (
    AXIOMATIC_DIMS,
    HASH_DIMS,
    MODULATION_PROFILES,
    _try_load_flume_encoder,
    _try_load_temporal_encoder,
    encode_step_sequence as _encode_step_sequence,
    holographic_project as _holographic_project,
    step_to_axiomatic,
    text_to_latent as _text_to_latent,
)


if TYPE_CHECKING:
    from cohezion.compound.thermodynamic_metrics import ThermodynamicState


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Supported operation types with specific modulation profiles."""

    GENERATE = "generate"  # High novelty + logic
    ANALYZE = "analyze"  # High logic + field
    SEARCH = "search"  # High spatial
    TRANSFORM = "transform"  # Moderate all
    PERSIST = "persist"  # High temporal + precipitation


@dataclass
class TrajectoryPoint:
    """Single point in a 12D FLUME trajectory."""

    dimensions: np.ndarray  # 12D vector
    timestamp: float  # Execution time
    coherence: float  # Quality metric (0.0-1.0)
    efficiency: float  # Token efficiency (0.0-1.0)
    operation_type: str  # Type of operation
    task_description: str  # Task that generated this point
    metadata: dict[str, Any] | None = field(default=None)  # Additional context


@dataclass
class Journey:
    """Complete journey of trajectory points for a compound execution."""

    execution_id: str
    points: list[TrajectoryPoint]
    start_time: float
    end_time: float
    task_description: str
    operation_type: str
    final_success: bool
    phi_score: float  # Trajectory quality score


class JourneyTracker:
    """Track compound executions as 12D FLUME trajectories.

    Maps execution quality metrics to 12D axiomatic space using:
    - Semantic embeddings for task context
    - Operation-specific modulation profiles
    - Holographic projection for dimensionality reduction
    - Quality scoring for trajectory analysis

    Example:
        ```python
        tracker = JourneyTracker()

        # After executing a compound task
        result = executor.execute_task(...)

        point = tracker.track_execution(
            execution_result=result,
            task_description="Generate creative ideas",
            operation_type="generate",
        )

        print(f"Trajectory point: {point.dimensions}")
        print(f"Quality score: {point.coherence:.2f}")
        ```
    """

    AXIOMATIC_DIMS = AXIOMATIC_DIMS
    HASH_DIMS = HASH_DIMS
    CHUNK_SIZE = 128
    TRAJECTORY_WINDOW = 20
    MAX_CACHE_SIZE = 1000

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self._projection_cache: dict[str, np.ndarray] = {}
        self._flume_encoder = _try_load_flume_encoder()
        self._temporal_encoder = _try_load_temporal_encoder()
        self._recent_points: list[TrajectoryPoint] = []
        self._modulation_profiles = dict(MODULATION_PROFILES)
        logger.debug("Initialized JourneyTracker with seed=%d", seed)

    def text_to_latent(self, text: str) -> np.ndarray:
        """Generate 2048D embedding from text."""
        return _text_to_latent(text, flume_encoder=self._flume_encoder)

    def encode_step_sequence(self, steps: list[dict]) -> np.ndarray:
        """Encode a sequence of execution steps to 2048D."""
        return _encode_step_sequence(
            steps,
            temporal_encoder=self._temporal_encoder,
            flume_encoder=self._flume_encoder,
        )

    def holographic_project(self, latent_2048d: np.ndarray) -> np.ndarray:
        """Project 2048D embedding to 12D using chunk-mean averaging."""
        return _holographic_project(latent_2048d, projection_cache=self._projection_cache)

    def _step_to_axiomatic(
        self,
        projection_12d: np.ndarray,
        operation_type: str,
        coherence: float,
        efficiency: float,
    ) -> np.ndarray:
        """Apply operation-specific modulation to 12D projection."""
        operation_str = operation_type if isinstance(operation_type, str) else operation_type.value
        return step_to_axiomatic(projection_12d, operation_str, coherence, efficiency)

    def _compute_phi_score(
        self,
        coherence: float,
        smoothness: float = 0.5,
        convergence: float = 0.5,
    ) -> float:
        """Compute trajectory quality score (phi score).

        phi = coherence * 0.5 + smoothness * 0.3 + convergence * 0.2
        """
        phi = coherence * 0.5 + smoothness * 0.3 + convergence * 0.2
        return np.clip(phi, 0.0, 1.0)

    def track_execution(
        self,
        execution_result: ExecutionResult,
        task_description: str,
        operation_type: str,
    ) -> TrajectoryPoint:
        """Track a compound execution as a trajectory point."""
        coherence = execution_result.metrics.get("coherence", 0.5)
        efficiency = (
            execution_result.token_metrics.get("cache_hit_rate", 0.5) if execution_result.token_metrics else 0.5
        )

        latent_2048d = self.text_to_latent(task_description)
        projection_12d = self.holographic_project(latent_2048d)
        axiomatic_12d = self._step_to_axiomatic(projection_12d, operation_type, coherence, efficiency)

        smoothness = 0.5
        convergence = 0.5
        if len(self._recent_points) >= 2:
            quality = self.compute_trajectory_quality(self._recent_points)
            smoothness = quality["smoothness"]
            convergence = quality["convergence"]

        phi_score = self._compute_phi_score(
            coherence=coherence,
            smoothness=smoothness,
            convergence=convergence,
        )

        point = TrajectoryPoint(
            dimensions=axiomatic_12d,
            timestamp=execution_result.duration_seconds,
            coherence=coherence,
            efficiency=efficiency,
            operation_type=operation_type,
            task_description=task_description,
            metadata={
                "phi_score": phi_score,
                "success": execution_result.success,
                "output_length": len(execution_result.output),
            },
        )

        self._recent_points.append(point)
        if len(self._recent_points) > self.TRAJECTORY_WINDOW:
            self._recent_points = self._recent_points[-self.TRAJECTORY_WINDOW :]

        logger.debug(
            "Tracked execution: %s (phi=%.2f, coherence=%.2f, smoothness=%.2f, convergence=%.2f, buffer=%d)",
            task_description[:50],
            phi_score,
            coherence,
            smoothness,
            convergence,
            len(self._recent_points),
        )
        return point

    def get_recent_trajectory(self) -> list[TrajectoryPoint]:
        """Get the recent trajectory points."""
        return self._recent_points

    def get_last_point(self) -> TrajectoryPoint | None:
        """Get the most recent point in the trajectory."""
        return self._recent_points[-1] if self._recent_points else None

    def get_recent_point_count(self) -> int:
        """Return the number of points in the recent trajectory buffer."""
        return len(self._recent_points)

    def compute_trajectory_quality(
        self,
        points: list[TrajectoryPoint],
    ) -> dict[str, float]:
        """Compute comprehensive trajectory quality metrics."""
        if not points:
            return {
                "mean_phi_score": 0.0,
                "mean_coherence": 0.0,
                "mean_efficiency": 0.0,
                "smoothness": 0.0,
                "convergence": 0.0,
            }

        coherences = np.array([p.coherence for p in points])
        efficiencies = np.array([p.efficiency for p in points])
        phi_scores = np.array([(p.metadata or {}).get("phi_score", 0.0) for p in points])

        dimensions = np.array([p.dimensions for p in points])
        if len(dimensions) > 1:
            diffs = np.diff(dimensions, axis=0)
            smoothness = 1.0 - np.mean(np.abs(diffs))
        else:
            smoothness = 1.0

        if len(coherences) > 1:
            convergence = 1.0 - np.std(coherences[-min(3, len(coherences)) :])
        else:
            convergence = 1.0

        return {
            "mean_phi_score": float(np.mean(phi_scores)),
            "mean_coherence": float(np.mean(coherences)),
            "mean_efficiency": float(np.mean(efficiencies)),
            "smoothness": float(np.clip(smoothness, 0.0, 1.0)),
            "convergence": float(np.clip(convergence, 0.0, 1.0)),
        }

    def compute_thermodynamic_state(self) -> "ThermodynamicState | None":
        """Compute thermodynamic state from recent trajectory."""
        try:
            from cohezion.compound.thermodynamic_metrics import ThermodynamicMetrics

            if len(self._recent_points) < 5:
                return None

            thermo = ThermodynamicMetrics(
                window_size=min(self.TRAJECTORY_WINDOW, len(self._recent_points)),
                min_samples=5,
            )

            for point in self._recent_points:
                thermo.record(
                    coherence=point.coherence,
                    trajectory_point=point.dimensions,
                    energy=None,
                )

            return thermo.compute_state()
        except Exception as e:
            logger.warning("Thermodynamic computation failed (non-blocking): %s", e)
            return None

    def compute_topological_summary(self) -> dict[str, float]:
        """Compute topological persistence summary of recent trajectory."""
        try:
            from cohezion.compound.topological_persistence import (
                trajectory_persistence_summary,
            )

            if len(self._recent_points) < 3:
                return {}

            points = [p.dimensions for p in self._recent_points]
            return trajectory_persistence_summary(points)
        except Exception as e:
            logger.warning("Topological computation failed (non-blocking): %s", e)
            return {}

    def compute_advanced_quality(
        self,
        points: list[TrajectoryPoint] | None = None,
    ) -> dict[str, Any]:
        """Compute trajectory quality with thermodynamic + topological metrics."""
        pts = points if points is not None else list(self._recent_points)
        base = self.compute_trajectory_quality(pts)

        thermo = self.compute_thermodynamic_state()
        if thermo is not None:
            base["entropy_production_rate"] = thermo.entropy_production_rate
            base["free_energy"] = thermo.free_energy
            base["susceptibility"] = thermo.susceptibility
            base["heat_capacity"] = thermo.heat_capacity
            base["effective_temperature"] = thermo.temperature

        topo = self.compute_topological_summary()
        if topo:
            base["n_behavioral_modes"] = topo.get("n_clusters", 0)
            base["n_behavioral_cycles"] = topo.get("n_loops", 0)
            base["topological_complexity"] = topo.get("persistence_entropy_h0", 0.0)
            base["cycle_complexity"] = topo.get("persistence_entropy_h1", 0.0)

        return base


class JourneyTrackerFactory:
    """Factory for creating journey trackers."""

    @staticmethod
    def create(seed: int = 42) -> JourneyTracker:
        return JourneyTracker(seed=seed)


_journey_tracker_instance: JourneyTracker | None = None


def get_journey_tracker() -> JourneyTracker:
    """Get the global JourneyTracker instance."""
    global _journey_tracker_instance
    if _journey_tracker_instance is None:
        _journey_tracker_instance = JourneyTracker()
    return _journey_tracker_instance
