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


if TYPE_CHECKING:
    from cohezion.compound.thermodynamic_metrics import ThermodynamicState

import numpy as np


if TYPE_CHECKING:
    from cohezion.compound.thermodynamic_metrics import ThermodynamicState

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.holographic_projection import (
    AXIOMATIC_DIMS,
    HASH_DIMS,
    MODULATION_PROFILES,
    _try_load_flume_encoder,
    _try_load_temporal_encoder,
)
from cohezion.compound.holographic_projection import (
    encode_step_sequence as _encode_step_sequence,
)
from cohezion.compound.holographic_projection import (
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

        # ANALYZE: High logic (1) + field (2)
        profiles[OperationType.ANALYZE.value] = np.array(
            [
                0.5,  # novelty
                0.9,  # logic
                0.8,  # field
                0.4,  # spatial
                0.3,  # temporal
                0.4,  # precipitation
                0.7,  # coherence
                0.6,  # efficiency
                0.5,  # convergence
                0.4,  # smoothness
                0.6,  # resonance
                0.5,  # harmony
            ]
        )

        # SEARCH: High spatial (3)
        profiles[OperationType.SEARCH.value] = np.array(
            [
                0.6,  # novelty
                0.5,  # logic
                0.4,  # field
                0.9,  # spatial
                0.4,  # temporal
                0.3,  # precipitation
                0.6,  # coherence
                0.8,  # efficiency
                0.4,  # convergence
                0.5,  # smoothness
                0.5,  # resonance
                0.4,  # harmony
            ]
        )

        # TRANSFORM: Moderate all
        profiles[OperationType.TRANSFORM.value] = np.array(
            [
                0.6,  # novelty
                0.6,  # logic
                0.6,  # field
                0.6,  # spatial
                0.6,  # temporal
                0.6,  # precipitation
                0.6,  # coherence
                0.6,  # efficiency
                0.5,  # convergence
                0.5,  # smoothness
                0.6,  # resonance
                0.6,  # harmony
            ]
        )

        # PERSIST: High temporal (4) + precipitation (5)
        profiles[OperationType.PERSIST.value] = np.array(
            [
                0.3,  # novelty
                0.4,  # logic
                0.5,  # field
                0.4,  # spatial
                0.9,  # temporal
                0.8,  # precipitation
                0.7,  # coherence
                0.5,  # efficiency
                0.6,  # convergence
                0.4,  # smoothness
                0.5,  # resonance
                0.5,  # harmony
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
        # Generate hash
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Expand to 2048 dimensions using deterministic method
        latent = np.zeros(self.HASH_DIMS)
        for i in range(self.HASH_DIMS):
            # Cycle through hash bytes
            byte_idx = i % len(hash_bytes)
            # Use sine wave modulation for smooth variation
            phase = (2.0 * np.pi * i) / self.HASH_DIMS
            latent[i] = (hash_bytes[byte_idx] / 255.0) * 0.5 + 0.25 * np.sin(phase) + 0.25 * np.cos(phase * 2)

        # Normalize to [-1, 1]
        latent = 2.0 * (latent - np.min(latent)) / (np.max(latent) - np.min(latent) + 1e-8) - 1.0

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
        # Check cache
        latent_hash = hashlib.sha256(latent_2048d.tobytes()).hexdigest()[:8]
        if latent_hash in self._projection_cache:
            return self._projection_cache[latent_hash]

        # Chunk-mean projection: 2048 → 16 dimensions (128-element chunks)
        num_chunks = self.HASH_DIMS // self.CHUNK_SIZE
        chunk_means = np.array(
            [np.mean(latent_2048d[i * self.CHUNK_SIZE : (i + 1) * self.CHUNK_SIZE]) for i in range(num_chunks)]
        )

        # Interpolate 16D → 12D
        if len(chunk_means) > self.AXIOMATIC_DIMS:
            # Downsample using linear interpolation
            indices = np.linspace(0, len(chunk_means) - 1, self.AXIOMATIC_DIMS)
            result_12d = np.interp(indices, np.arange(len(chunk_means)), chunk_means)
        else:
            # Upsample if needed
            indices = np.linspace(0, len(chunk_means) - 1, self.AXIOMATIC_DIMS)
            result_12d = np.interp(indices, np.arange(len(chunk_means)), chunk_means)

        # Normalize to [0, 1]
        result_12d = (result_12d - np.min(result_12d)) / (np.max(result_12d) - np.min(result_12d) + 1e-8)

        # Cache result (evict oldest if at capacity)
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
        # Get modulation profile
        operation_str = operation_type if isinstance(operation_type, str) else operation_type.value
        modulation = self._modulation_profiles.get(
            operation_str,
            self._modulation_profiles[OperationType.TRANSFORM.value],
        )

        # Combine projection with modulation
        # Weight modulation by execution quality
        quality_weight = 0.5 * coherence + 0.5 * efficiency
        axiomatic = projection_12d * (1.0 - quality_weight) + modulation * quality_weight

        # Normalize
        axiomatic = np.clip(axiomatic, 0.0, 1.0)

        return axiomatic

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

        # Apply operation modulation
        axiomatic_12d = self._step_to_axiomatic(projection_12d, operation_type, coherence, efficiency)

        # Compute quality score using real trajectory history
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
