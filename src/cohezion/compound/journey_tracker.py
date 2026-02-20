"""Journey tracking for compound executions with unified FLUME trajectories.

Consolidates:
- 12D FLUME axiomatic trajectories (physics visualization)
- 256D FLUME VAE latent (VAE operations)
- 2048D semantic embeddings (vector similarity search)

Lifecycle:
  1. Extract execution metrics (coherence, efficiency, duration)
  2. Generate semantic embedding (2048D)
  3. Project to 256D using FLUME VAE encoder
  4. Project to 12D using holographic method
  5. Apply operation-specific modulation
  6. Compute trajectory quality score
  7. Persist to SurrealDB with full trajectory chain

Features:
- Deterministic 12D trajectory representation
- 256D FLUME VAE encoding
- 2048D semantic embedding for similarity search
- Full execution metadata (decisions, actions, outcomes)
- Vector similarity queries via MTREE indexes
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

from cohezion.compound.executor_types import ExecutionResult
from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.flume.vae_encoder import get_encoder


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

    journey_id: str | None = None
    execution_id: str = ""
    session_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_description: str = ""
    operation_type: str = ""
    journey_type: str = "compound"
    coherence_at_start: float = 0.0
    coherence_at_end: float = 0.0
    phi_score: float = 0.0
    final_success: bool = False
    embedding_2048d: list[float] | None = None
    flume_latent_256d: list[float] | None = None
    trajectory_12d: list[float] | None = None
    points: list["TrajectoryPoint"] = field(default_factory=list)
    decisions_made: list[dict[str, Any]] = field(default_factory=list)
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


UNIFIED_SCHEMA = """
-- Unified journey tracking with full trajectory chain
DEFINE TABLE agent_journeys SCHEMAFULL;

-- Core identifiers
DEFINE FIELD journey_id ON agent_journeys TYPE string;
DEFINE FIELD execution_id ON agent_journeys TYPE string;
DEFINE FIELD session_id ON agent_journeys TYPE string;

-- Temporal fields
DEFINE FIELD started_at ON agent_journeys TYPE datetime;
DEFINE FIELD completed_at ON agent_journeys TYPE datetime;
DEFINE FIELD duration_ms ON agent_journeys TYPE int DEFAULT 0;

-- Task context
DEFINE FIELD task_description ON agent_journeys TYPE string;
DEFINE FIELD operation_type ON agent_journeys TYPE string;
DEFINE FIELD journey_type ON agent_journeys TYPE string DEFAULT 'compound';

-- Quality metrics
DEFINE FIELD coherence_at_start ON agent_journeys TYPE float DEFAULT 0.0;
DEFINE FIELD coherence_at_end ON agent_journeys TYPE float DEFAULT 0.0;
DEFINE FIELD phi_score ON agent_journeys TYPE float DEFAULT 0.0;
DEFINE FIELD final_success ON agent_journeys TYPE bool DEFAULT false;

-- Full trajectory: 2048D semantic embedding (for similarity search)
DEFINE FIELD embedding_2048d ON agent_journeys TYPE array;

-- Full trajectory: 256D FLUME VAE latent (for VAE operations)
DEFINE FIELD flume_latent_256d ON agent_journeys TYPE array;

-- Full trajectory: 12D axiomatic trajectory points (physics visualization)
DEFINE FIELD trajectory_12d ON agent_journeys TYPE array;

-- Decision chain
DEFINE FIELD decisions_made ON agent_journeys TYPE array DEFAULT [];

-- Action chain
DEFINE FIELD actions_taken ON agent_journeys TYPE array DEFAULT [];

-- Outcome
DEFINE FIELD outcome ON agent_journeys TYPE string DEFAULT '';

-- Additional metadata
DEFINE FIELD metadata ON agent_journeys TYPE object DEFAULT {};

-- Indexes for vector similarity search
-- MTREE indexes require SurrealDB 2.0+
-- DEFINE INDEX embedding_2048d_idx ON agent_journeys FIELDS embedding_2048d MTREE DIMENSION 2048 DIST COSINE;
-- DEFINE INDEX flume_latent_256d_idx ON agent_journeys FIELDS flume_latent_256d MTREE DIMENSION 256 DIST COSINE;

-- Indexes for common queries
DEFINE INDEX journey_id_idx ON agent_journeys FIELDS journey_id UNIQUE;
DEFINE INDEX session_id_idx ON agent_journeys FIELDS session_id;
DEFINE INDEX operation_type_idx ON agent_journeys FIELDS operation_type;
DEFINE INDEX started_at_idx ON agent_journeys FIELDS started_at;
"""


class JourneyTracker:
    """Track compound executions as unified FLUME trajectories.

    Maps execution quality metrics to unified axiomatic space using:
    - 2048D semantic embeddings for similarity search
    - 256D FLUME VAE latent for VAE operations
    - 12D axiomatic trajectories for physics visualization
    - Full execution metadata (decisions, actions, outcomes)

    Example:
        ```python
        tracker = JourneyTracker()

        # After executing a compound task
        result = executor.execute_task(...)

        journey = await tracker.record_journey(
            execution_result=result,
            task_description="Generate creative ideas",
            operation_type="generate",
            session_id="session-123",
        )

        # Find similar journeys
        similar = await tracker.find_similar_journeys(
            task_description="Another creative task",
            limit=5
        )
        ```
    """

    AXIOMATIC_DIMS: int = 12
    HASH_DIMS: int = 2048
    FLUME_LATENT_DIMS: int = 256
    CHUNK_SIZE: int = 128
    TRAJECTORY_WINDOW: int = 50
    MAX_CACHE_SIZE: int = 1000

    def __init__(self, seed: int = 42, use_surreal: bool = True):
        """Initialize journey tracker.

        Args:
            seed: Random seed for deterministic projections
            use_surreal: Whether to use SurrealDB for storage
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.use_surreal = use_surreal

        self._projection_cache: dict[str, np.ndarray] = {}

        self._recent_points: list[TrajectoryPoint] = []

        self._modulation_profiles = self._create_modulation_profiles()

        self._current_journey: Journey | None = None
        self._db = None
        self._encoder = None

        if self.use_surreal:
            self._db = get_surreal_client()
            self._encoder = get_encoder()

        logger.debug(
            "Initialized JourneyTracker with seed=%d, surrealdb=%s", seed, use_surreal
        )

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

    def text_to_latent(self, text: str) -> np.ndarray:
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

    def holographic_project(self, latent_2048d: np.ndarray) -> np.ndarray:
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

        latent_2048d = self.text_to_latent(task_description)
        projection_12d = self.holographic_project(latent_2048d)

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

    def get_embedding_2048d(self, text: str) -> np.ndarray:
        """Generate 2048D semantic embedding from text.

        Args:
            text: Input text

        Returns:
            2048D numpy array
        """
        return self.text_to_latent(text)

    def get_flume_latent_256d(self, text: str) -> np.ndarray:
        """Generate 256D FLUME VAE latent from text.

        Uses VAE encoder if available, falls back to hash encoding.

        Args:
            text: Input text

        Returns:
            256D numpy array
        """
        if self._encoder is not None and self._encoder.is_available():
            return self._encoder.encode(text)
        return self._fallback_256d_encoding(text)

    def _fallback_256d_encoding(self, text: str) -> np.ndarray:
        """Generate 256D encoding from text using hash.

        Args:
            text: Input text

        Returns:
            256D numpy array
        """
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        embedding = np.zeros(256, dtype=np.float32)
        for i in range(256):
            byte_idx = i % len(hash_bytes)
            embedding[i] = hash_bytes[byte_idx] / 255.0

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding

    async def record_journey(
        self,
        execution_result: ExecutionResult,
        task_description: str,
        operation_type: str,
        session_id: str | None = None,
        coherence_at_start: float = 0.5,
        decisions: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        outcome: str = "",
    ) -> Journey:
        """Record a complete journey with full trajectory chain.

        Generates and stores:
        - 2048D semantic embedding for similarity search
        - 256D FLUME VAE latent for VAE operations
        - 12D trajectory points for physics visualization

        Args:
            execution_result: ExecutionResult from compound executor
            task_description: Description of the task
            operation_type: Type of operation
            session_id: Optional session ID for linking
            coherence_at_start: Starting coherence value
            decisions: List of decisions made during execution
            actions: List of actions taken during execution
            outcome: Final outcome description

        Returns:
            Journey with full trajectory data
        """
        journey_id = str(uuid.uuid4())
        execution_id = (
            execution_result.id if hasattr(execution_result, "id") else journey_id
        )

        embedding_2048d = self.get_embedding_2048d(task_description)
        flume_latent_256d = self.get_flume_latent_256d(task_description)

        coherence = execution_result.metrics.get("coherence", 0.5)
        efficiency = (
            execution_result.token_metrics.get("cache_hit_rate", 0.5)
            if execution_result.token_metrics
            else 0.5
        )

        trajectory_12d = self.holographic_project(embedding_2048d)
        axiomatic_12d = self._step_to_axiomatic(
            trajectory_12d, operation_type, coherence, efficiency
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

        journey = Journey(
            journey_id=journey_id,
            execution_id=execution_id,
            session_id=session_id,
            started_at=datetime.now(),
            task_description=task_description,
            operation_type=operation_type,
            coherence_at_start=coherence_at_start,
            coherence_at_end=coherence,
            phi_score=phi_score,
            final_success=execution_result.success,
            embedding_2048d=embedding_2048d.tolist(),
            flume_latent_256d=flume_latent_256d.tolist()
            if hasattr(flume_latent_256d, "tolist")
            else list(flume_latent_256d),
            trajectory_12d=axiomatic_12d.tolist()
            if hasattr(axiomatic_12d, "tolist")
            else list(axiomatic_12d),
            decisions_made=decisions or [],
            actions_taken=actions or [],
            outcome=outcome,
            metadata={
                "duration_seconds": execution_result.duration_seconds,
                "output_length": len(execution_result.output),
                "smoothness": smoothness,
                "convergence": convergence,
            },
        )

        if self.use_surreal and self._db is not None:
            await self._store_journey_to_db(journey)

        logger.debug(
            "Recorded journey: %s (phi=%.2f, 2048d=%s, 256d=%s)",
            journey_id[:8],
            phi_score,
            len(embedding_2048d),
            len(flume_latent_256d) if hasattr(flume_latent_256d, "__len__") else 256,
        )

        return journey

    async def _store_journey_to_db(self, journey: Journey) -> None:
        """Store journey to SurrealDB.

        Args:
            journey: Journey to store
        """
        try:
            if self._db is None:
                return

            await self._db.query(
                """
                CREATE agent_journeys CONTENT {
                    journey_id: $journey_id,
                    execution_id: $execution_id,
                    session_id: $session_id,
                    started_at: $started_at,
                    task_description: $task_description,
                    operation_type: $operation_type,
                    journey_type: 'compound',
                    coherence_at_start: $coherence_at_start,
                    coherence_at_end: $coherence_at_end,
                    phi_score: $phi_score,
                    final_success: $final_success,
                    embedding_2048d: $embedding_2048d,
                    flume_latent_256d: $flume_latent_256d,
                    trajectory_12d: $trajectory_12d,
                    decisions_made: $decisions_made,
                    actions_taken: $actions_taken,
                    outcome: $outcome,
                    metadata: $metadata
                };
            """,
                {
                    "journey_id": journey.journey_id,
                    "execution_id": journey.execution_id,
                    "session_id": journey.session_id,
                    "started_at": journey.started_at.isoformat()
                    if journey.started_at
                    else datetime.now().isoformat(),
                    "task_description": journey.task_description,
                    "operation_type": journey.operation_type,
                    "coherence_at_start": journey.coherence_at_start,
                    "coherence_at_end": journey.coherence_at_end,
                    "phi_score": journey.phi_score,
                    "final_success": journey.final_success,
                    "embedding_2048d": journey.embedding_2048d,
                    "flume_latent_256d": journey.flume_latent_256d,
                    "trajectory_12d": journey.trajectory_12d,
                    "decisions_made": journey.decisions_made,
                    "actions_taken": journey.actions_taken,
                    "outcome": journey.outcome,
                    "metadata": journey.metadata,
                },
            )
            logger.info(f"Stored journey to SurrealDB: {journey.journey_id}")
        except Exception as e:
            logger.error(f"Failed to store journey to SurrealDB: {e}")

    async def find_similar_journeys(
        self,
        task_description: str | None = None,
        embedding: list[float] | None = None,
        limit: int = 5,
        use_256d: bool = True,
    ) -> list[dict[str, Any]]:
        """Find similar journeys using vector similarity search.

        Args:
            task_description: Task description to search for
            embedding: Optional pre-computed embedding (2048D or 256D)
            limit: Maximum number of results
            use_256d: Use 256D FLUME latent instead of 2048D

        Returns:
            List of similar journeys with similarity scores
        """
        if embedding is None and task_description is None:
            return []

        if embedding is None:
            if use_256d:
                embedding = self.get_flume_latent_256d(task_description).tolist()
            else:
                embedding = self.get_embedding_2048d(task_description).tolist()

        try:
            if self._db is not None:
                field = "flume_latent_256d" if use_256d else "embedding_2048d"
                query = f"""
                    SELECT *, vector::similarity::cosine({field}, $embedding) AS score
                    FROM agent_journeys
                    ORDER BY score DESC
                    LIMIT {limit}
                """
                results = await self._db.query(query, {"embedding": embedding})
                return results[0].get("result", []) if results else []
        except Exception as e:
            logger.error(f"Failed to query similar journeys: {e}")

        return []

    async def get_journey(self, journey_id: str) -> Journey | None:
        """Retrieve a journey by ID.

        Args:
            journey_id: Journey ID

        Returns:
            Journey if found, None otherwise
        """
        try:
            if self._db is not None:
                result = await self._db.query(
                    "SELECT * FROM agent_journeys WHERE journey_id = $journey_id;",
                    {"journey_id": journey_id},
                )
                if result and len(result) > 0:
                    data = result[0]
                    return Journey(
                        journey_id=data.get("journey_id"),
                        execution_id=data.get("execution_id"),
                        session_id=data.get("session_id"),
                        task_description=data.get("task_description", ""),
                        operation_type=data.get("operation_type", ""),
                        coherence_at_start=data.get("coherence_at_start", 0.0),
                        coherence_at_end=data.get("coherence_at_end", 0.0),
                        phi_score=data.get("phi_score", 0.0),
                        final_success=data.get("final_success", False),
                        embedding_2048d=data.get("embedding_2048d"),
                        flume_latent_256d=data.get("flume_latent_256d"),
                        trajectory_12d=data.get("trajectory_12d"),
                        decisions_made=data.get("decisions_made", []),
                        actions_taken=data.get("actions_taken", []),
                        outcome=data.get("outcome", ""),
                        metadata=data.get("metadata", {}),
                    )
        except Exception as e:
            logger.error(f"Failed to get journey: {e}")

        return None

    async def get_recent_journeys(
        self,
        operation_type: str | None = None,
        limit: int = 10,
    ) -> list[Journey]:
        """Get recent journeys, optionally filtered by type.

        Args:
            operation_type: Optional operation type filter
            limit: Maximum number of results

        Returns:
            List of recent journeys
        """
        journeys = []

        try:
            if self._db is not None:
                if operation_type:
                    result = await self._db.query(
                        """
                        SELECT * FROM agent_journeys
                        WHERE operation_type = $operation_type
                        ORDER BY started_at DESC
                        LIMIT $limit;
                        """,
                        {"operation_type": operation_type, "limit": limit},
                    )
                else:
                    result = await self._db.query(
                        """
                        SELECT * FROM agent_journeys
                        ORDER BY started_at DESC
                        LIMIT $limit;
                        """,
                        {"limit": limit},
                    )

                if result:
                    for data in result:
                        journeys.append(
                            Journey(
                                journey_id=data.get("journey_id"),
                                execution_id=data.get("execution_id"),
                                session_id=data.get("session_id"),
                                task_description=data.get("task_description", ""),
                                operation_type=data.get("operation_type", ""),
                                coherence_at_start=data.get("coherence_at_start", 0.0),
                                coherence_at_end=data.get("coherence_at_end", 0.0),
                                phi_score=data.get("phi_score", 0.0),
                                final_success=data.get("final_success", False),
                                embedding_2048d=data.get("embedding_2048d"),
                                flume_latent_256d=data.get("flume_latent_256d"),
                                trajectory_12d=data.get("trajectory_12d"),
                                decisions_made=data.get("decisions_made", []),
                                actions_taken=data.get("actions_taken", []),
                                outcome=data.get("outcome", ""),
                                metadata=data.get("metadata", {}),
                            )
                        )
        except Exception as e:
            logger.error(f"Failed to get recent journeys: {e}")

        return journeys


class JourneyTrackerFactory:
    """Factory for creating journey trackers."""

    @staticmethod
    def create(seed: int = 42, use_surreal: bool = True) -> JourneyTracker:
        """Create a journey tracker.

        Args:
            seed: Random seed for deterministic behavior
            use_surreal: Whether to use SurrealDB for storage

        Returns:
            JourneyTracker instance
        """
        return JourneyTracker(seed=seed, use_surreal=use_surreal)


_tracker: JourneyTracker | None = None


def get_journey_tracker(use_surreal: bool = True) -> JourneyTracker:
    """Get or create the global journey tracker instance.

    Args:
        use_surreal: Whether to use SurrealDB for storage

    Returns:
        JourneyTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = JourneyTrackerFactory.create(use_surreal=use_surreal)
    return _tracker


def reset_journey_tracker() -> None:
    """Reset the global journey tracker (for testing)."""
    global _tracker
    _tracker = None
