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

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from cohezion.compound.executor import ExecutionResult


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Supported operation types with specific modulation profiles."""

    GENERATE = "generate"
    ANALYZE = "analyze"
    SEARCH = "search"
    TRANSFORM = "transform"
    PERSIST = "persist"


@dataclass
class TrajectoryPoint:
    """Single point in a 12D FLUME trajectory."""

    dimensions: np.ndarray
    timestamp: float
    coherence: float
    efficiency: float
    operation_type: str
    task_description: str
    metadata: dict[str, Any] | None = None


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
    phi_score: float


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

    AXIOMATIC_DIMS = 12

    HASH_DIMS = 2048
    CHUNK_SIZE = 128

    TRAJECTORY_WINDOW = 20

    MAX_CACHE_SIZE = 1000

    def __init__(self, seed: int = 42):
        """Initialize journey tracker.

        Args:
            seed: Random seed for deterministic projections
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        self._projection_cache: dict[str, np.ndarray] = {}

        self._recent_points: list[TrajectoryPoint] = []

        self._modulation_profiles = self._create_modulation_profiles()

        logger.debug("Initialized JourneyTracker with seed=%d", seed)

    def _create_modulation_profiles(self) -> dict[str, np.ndarray]:
        """Create operation-specific modulation profiles.

        Each operation type has a different 12D modulation vector
        that emphasizes different dimensions.

        Returns:
            Dictionary mapping operation type to 12D modulation vector
        """
        profiles = {}

        profiles[OperationType.GENERATE.value] = np.array(
            [
                0.9,
                0.8,
                0.4,
                0.3,
                0.5,
                0.5,
                0.6,
                0.5,
                0.4,
                0.3,
                0.5,
                0.4,
            ]
        )

        profiles[OperationType.ANALYZE.value] = np.array(
            [
                0.5,
                0.9,
                0.8,
                0.4,
                0.3,
                0.4,
                0.7,
                0.6,
                0.5,
                0.4,
                0.6,
                0.5,
            ]
        )

        profiles[OperationType.SEARCH.value] = np.array(
            [
                0.6,
                0.5,
                0.4,
                0.9,
                0.4,
                0.3,
                0.6,
                0.8,
                0.4,
                0.5,
                0.5,
                0.4,
            ]
        )

        profiles[OperationType.TRANSFORM.value] = np.array(
            [
                0.6,
                0.6,
                0.6,
                0.6,
                0.6,
                0.6,
                0.6,
                0.6,
                0.5,
                0.5,
                0.6,
                0.6,
            ]
        )

        profiles[OperationType.PERSIST.value] = np.array(
            [
                0.3,
                0.4,
                0.5,
                0.4,
                0.9,
                0.8,
                0.7,
                0.5,
                0.6,
                0.4,
                0.5,
                0.5,
            ]
        )

        return profiles

    def _text_to_latent(self, text: str) -> np.ndarray:
        """Generate deterministic 2048D embedding from text.

        Uses SHA-256 hash expanded to 2048D with sine wave modulation.

        Args:
            text: Input text to embed

        Returns:
            2048D numpy array with normalized values
        """
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        latent = np.zeros(self.HASH_DIMS)
        for i in range(self.HASH_DIMS):
            byte_idx = i % len(hash_bytes)
            phase = (2.0 * np.pi * i) / self.HASH_DIMS
            latent[i] = (
                (hash_bytes[byte_idx] / 255.0) * 0.5
                + 0.25 * np.sin(phase)
                + 0.25 * np.cos(phase * 2)
            )

        latent = (
            2.0 * (latent - np.min(latent)) / (np.max(latent) - np.min(latent) + 1e-8)
            - 1.0
        )

        return latent

    def _holographic_project(self, latent_2048d: np.ndarray) -> np.ndarray:
        """Project 2048D embedding to 12D using holographic method.

        Uses chunk-mean averaging: divide 2048D into 128-element segments
        and take mean of each segment. Then interpolate to 12D.

        Args:
            latent_2048d: 2048D embedding vector

        Returns:
            12D normalized vector
        """
        latent_hash = hashlib.sha256(latent_2048d.tobytes()).hexdigest()[:8]
        if latent_hash in self._projection_cache:
            return self._projection_cache[latent_hash]

        num_chunks = self.HASH_DIMS // self.CHUNK_SIZE
        chunk_means = np.array(
            [
                np.mean(latent_2048d[i * self.CHUNK_SIZE : (i + 1) * self.CHUNK_SIZE])
                for i in range(num_chunks)
            ]
        )

        if len(chunk_means) > self.AXIOMATIC_DIMS:
            indices = np.linspace(0, len(chunk_means) - 1, self.AXIOMATIC_DIMS)
            result_12d = np.interp(indices, np.arange(len(chunk_means)), chunk_means)
        else:
            indices = np.linspace(0, len(chunk_means) - 1, self.AXIOMATIC_DIMS)
            result_12d = np.interp(indices, np.arange(len(chunk_means)), chunk_means)

        result_12d = (result_12d - np.min(result_12d)) / (
            np.max(result_12d) - np.min(result_12d) + 1e-8
        )

        if len(self._projection_cache) >= self.MAX_CACHE_SIZE:
            oldest_key = next(iter(self._projection_cache))
            del self._projection_cache[oldest_key]
        self._projection_cache[latent_hash] = result_12d

        return result_12d

    def _step_to_axiomatic(
        self,
        projection_12d: np.ndarray,
        operation_type: str,
        coherence: float,
        efficiency: float,
    ) -> np.ndarray:
        """Apply operation-specific modulation to 12D projection.

        Combines base projection with operation modulation and
        execution quality metrics.

        Args:
            projection_12d: 12D base projection
            operation_type: Type of operation
            coherence: Quality metric (0.0-1.0)
            efficiency: Token efficiency (0.0-1.0)

        Returns:
            12D axiomatic vector
        """
        operation_str = (
            operation_type if isinstance(operation_type, str) else operation_type.value
        )
        modulation = self._modulation_profiles.get(
            operation_str,
            self._modulation_profiles[OperationType.TRANSFORM.value],
        )

        quality_weight = 0.5 * coherence + 0.5 * efficiency
        axiomatic = (
            projection_12d * (1.0 - quality_weight) + modulation * quality_weight
        )

        axiomatic = np.clip(axiomatic, 0.0, 1.0)

        return axiomatic

    def _compute_phi_score(
        self,
        coherence: float,
        smoothness: float = 0.5,
        convergence: float = 0.5,
    ) -> float:
        """Compute trajectory quality score (phi score).

        Combines coherence (execution quality) with trajectory smoothness
        and convergence (stability indicators).

        Args:
            coherence: Execution coherence metric
            smoothness: Trajectory smoothness (0.0-1.0)
            convergence: Convergence to stable state (0.0-1.0)

        Returns:
            Phi score (0.0-1.0)
        """
        phi = coherence * 0.5 + smoothness * 0.3 + convergence * 0.2
        return np.clip(phi, 0.0, 1.0)

    def track_execution(
        self,
        execution_result: ExecutionResult,
        task_description: str,
        operation_type: str,
    ) -> TrajectoryPoint:
        """Track a compound execution as a trajectory point.

        Args:
            execution_result: ExecutionResult from compound executor
            task_description: Description of the task
            operation_type: Type of operation

        Returns:
            TrajectoryPoint with 12D trajectory coordinates
        """
        coherence = execution_result.metrics.get("coherence", 0.5)
        efficiency = (
            execution_result.token_metrics.get("cache_hit_rate", 0.5)
            if execution_result.token_metrics
            else 0.5
        )

        latent_2048d = self._text_to_latent(task_description)
        projection_12d = self._holographic_project(latent_2048d)

        axiomatic_12d = self._step_to_axiomatic(
            projection_12d, operation_type, coherence, efficiency
        )

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
            "Tracked execution: %s (phi=%.2f, coherence=%.2f, "
            "smoothness=%.2f, convergence=%.2f, buffer=%d)",
            task_description[:50],
            phi_score,
            coherence,
            smoothness,
            convergence,
            len(self._recent_points),
        )

        return point

    def get_last_point(self) -> TrajectoryPoint | None:
        """Return the most recent trajectory point, or None if no points tracked."""
        return self._recent_points[-1] if self._recent_points else None

    def get_recent_point_count(self) -> int:
        """Return the number of points in the recent trajectory buffer."""
        return len(self._recent_points)

    def compute_trajectory_quality(
        self,
        points: list[TrajectoryPoint],
    ) -> dict[str, float]:
        """Compute comprehensive trajectory quality metrics.

        Args:
            points: List of trajectory points

        Returns:
            Dictionary with quality metrics
        """
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
        phi_scores = np.array(
            [(p.metadata or {}).get("phi_score", 0.0) for p in points]
        )

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


class JourneyTrackerFactory:
    """Factory for creating journey trackers."""

    @staticmethod
    def create(seed: int = 42) -> JourneyTracker:
        """Create a journey tracker.

        Args:
            seed: Random seed for deterministic behavior

        Returns:
            JourneyTracker instance
        """
        return JourneyTracker(seed=seed)


_tracker: JourneyTracker | None = None


def get_journey_tracker() -> JourneyTracker:
    """Get or create the global journey tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = JourneyTrackerFactory.create()
    return _tracker
