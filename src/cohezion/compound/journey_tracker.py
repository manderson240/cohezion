# ruff: noqa: SIM105  # best-effort: ignored exceptions are intentional in init/cleanup paths
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
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.thermodynamic_metrics import ThermodynamicState

import numpy as np

from cohezion.compound.executor import ExecutionResult


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
    metadata: dict[str, Any] = None  # Additional context


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

    # 12D axiomatic dimensions
    AXIOMATIC_DIMS = 12

    # Holographic projection settings
    HASH_DIMS = 2048  # Intermediate hash dimension
    CHUNK_SIZE = 128  # Segment size for chunk-mean projection

    # Maximum points in the recent trajectory buffer
    TRAJECTORY_WINDOW = 20

    # Maximum entries in the projection cache
    MAX_CACHE_SIZE = 1000

    def __init__(self, seed: int = 42):
        """Initialize journey tracker.

        Args:
            seed: Random seed for deterministic projections
        """
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # Cache for projections
        self._projection_cache: dict[str, np.ndarray] = {}

        # Recent trajectory points for real smoothness/convergence
        self._recent_points: list[TrajectoryPoint] = []

        # Hash-chain state for OLIF audit trail: {chain_id: {sequence, last_hash}}
        self._chain_state: dict[str, dict[str, int | str]] = {}

        # Operation modulation profiles (12D vectors)
        self._modulation_profiles = self._create_modulation_profiles()

        # Write buffer for batched SurrealDB persistence (EXP-COMPOUND-1)
        # Flush when buffer reaches _WRITE_BATCH_SIZE or manually via _flush_write_buffer()
        self._write_buffer: list[str] = []
        self._WRITE_BATCH_SIZE: int = 10

        # Optional FLUME encoder (injected externally or loaded from checkpoint)
        self._flume_encoder = None

        # Try loading TemporalVAELoader from checkpoint if one is available
        self._temporal_encoder = None
        try:
            from cohezion.flume.temporal_encoder import TemporalVAELoader

            loader = TemporalVAELoader()
            if loader.enabled:
                self._temporal_encoder = loader
        except Exception as exc:
            logger.debug("TemporalVAELoader unavailable: %s", exc)

        logger.debug("Initialized JourneyTracker with seed=%d", seed)

    def _create_modulation_profiles(self) -> dict[str, np.ndarray]:
        """Create operation-specific modulation profiles.

        Each operation type has a different 12D modulation vector
        that emphasizes different dimensions.

        Returns:
            Dictionary mapping operation type to 12D modulation vector
        """
        profiles = {}

        # GENERATE: High novelty (0) + logic (1)
        profiles[OperationType.GENERATE.value] = np.array(
            [
                0.9,  # novelty
                0.8,  # logic
                0.4,  # field
                0.3,  # spatial
                0.5,  # temporal
                0.5,  # precipitation
                0.6,  # coherence
                0.5,  # efficiency
                0.4,  # convergence
                0.3,  # smoothness
                0.5,  # resonance
                0.4,  # harmony
            ]
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

        # Vectorized expansion to HASH_DIMS — replaces a 2048-iteration Python
        # loop with three numpy ops. ~9× speedup on this function. Output is
        # bit-identical to the loop version (verified). See Z6 perf report
        # (research/perf/2026-04-24-executor-profile.md, Recommendation #3).
        hash_arr = np.frombuffer(hash_bytes, dtype=np.uint8)
        indices = np.arange(self.HASH_DIMS)
        byte_lookup = hash_arr[indices % len(hash_bytes)]
        phases = (2.0 * np.pi * indices) / self.HASH_DIMS
        latent = (byte_lookup / 255.0) * 0.5 + 0.25 * np.sin(phases) + 0.25 * np.cos(phases * 2)

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
            [
                np.mean(latent_2048d[i * self.CHUNK_SIZE : (i + 1) * self.CHUNK_SIZE])
                for i in range(num_chunks)
            ]
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
        result_12d = (result_12d - np.min(result_12d)) / (
            np.max(result_12d) - np.min(result_12d) + 1e-8
        )

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
        # Extract metrics
        coherence = execution_result.metrics.get("coherence", 0.5)
        efficiency = (
            execution_result.token_metrics.get("cache_hit_rate", 0.5)
            if execution_result.token_metrics
            else 0.5
        )

        # Generate embeddings
        latent_2048d = self._text_to_latent(task_description)
        projection_12d = self._holographic_project(latent_2048d)

        # Apply operation modulation
        axiomatic_12d = self._step_to_axiomatic(
            projection_12d, operation_type, coherence, efficiency
        )

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
                "observer_consistency": self._compute_observer_consistency(axiomatic_12d),
            },
        )

        # Enrich with JEPA surprise scoring (non-blocking)
        if len(self._recent_points) >= 1:
            try:
                # Use API singleton for trained model access
                from cohezion.api.services.world_model import _get_model

                jepa = _get_model()
                if jepa._trained:
                    prev = self._recent_points[-1].dimensions
                    action = axiomatic_12d - prev
                    surprise = jepa.surprise_score(prev, action, axiomatic_12d)
                    point.metadata["jepa_surprise"] = float(surprise)
            except Exception:
                pass

        # Enrich with bioelectric percolation (non-blocking)
        try:
            from cohezion.physics.bioelectric_model import BioelectricNetwork

            bio = BioelectricNetwork(n_cells=8)
            bio.set_uniform_conductance(coherence)
            percolation = bio.percolation_analysis()
            point.metadata["bioelectric_percolated"] = percolation.is_percolated
            point.metadata["bioelectric_clusters"] = percolation.cluster_count
        except Exception:
            pass

        # Maintain recent points buffer (capped at window size)
        self._recent_points.append(point)
        if len(self._recent_points) > self.TRAJECTORY_WINDOW:
            self._recent_points = self._recent_points[-self.TRAJECTORY_WINDOW :]

        # Persist trajectory point to SurrealDB (non-blocking, fire-and-forget)
        try:
            self._persist_to_surreal(point)
        except Exception:
            pass  # Non-blocking: SurrealDB may be unavailable

        # Append to audit hash chain (non-blocking)
        chain_id = hashlib.sha256(
            f"{operation_type}:{task_description[:100]}".encode()
        ).hexdigest()[:16]
        chain_payload = {
            "coherence": point.coherence,
            "efficiency": point.efficiency,
            "operation_type": point.operation_type,
            "phi_score": phi_score,
            "task": task_description[:100],
        }
        self._record_chain_entry(chain_id, chain_payload)

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

    def track_evo_step(
        self,
        task_description: str,
        operation_type: str,
        coherence: float,
        efficiency: float,
        success: bool = True,
        duration_seconds: float = 0.0,
    ) -> TrajectoryPoint:
        """Track a RecursiveTracer EVO step as a 12D trajectory point.

        Accepts the raw physics metrics from recursive_tracer.trace_step() rather
        than an ExecutionResult, then delegates to the existing trajectory pipeline.
        Called once per step in the HIHO trace monad.
        """
        latent_2048d = self._text_to_latent(task_description)
        projection_12d = self._holographic_project(latent_2048d)
        axiomatic_12d = self._step_to_axiomatic(
            projection_12d, operation_type, coherence, efficiency
        )
        smoothness, convergence = 0.5, 0.5
        if len(self._recent_points) >= 2:
            quality = self.compute_trajectory_quality(self._recent_points)
            smoothness = quality["smoothness"]
            convergence = quality["convergence"]
        phi_score = self._compute_phi_score(
            coherence=coherence, smoothness=smoothness, convergence=convergence
        )
        point = TrajectoryPoint(
            dimensions=axiomatic_12d,
            timestamp=duration_seconds,
            coherence=coherence,
            efficiency=efficiency,
            operation_type=operation_type,
            task_description=task_description,
            metadata={
                "phi_score": phi_score,
                "success": success,
                "observer_consistency": self._compute_observer_consistency(axiomatic_12d),
            },
        )
        self._recent_points.append(point)
        if len(self._recent_points) > self.TRAJECTORY_WINDOW:
            self._recent_points = self._recent_points[-self.TRAJECTORY_WINDOW :]
        try:
            self._persist_to_surreal(point)
        except Exception:
            pass
        return point

    def emit_evo_voyage(
        self,
        voyage: object,
        skill_id: str | None = None,
    ) -> None:
        """Dual-write a completed ExperientialVoyage to SurrealDB and Obsidian vault.

        Writes to the evo_journey table (for _query_phi_trend σ adaptation) and
        writes a cerebellum note (for _load_cerebellum_context RAG injection).
        skill_id must be supplied to enable phi-trend queries per skill.
        """
        import base64
        import datetime
        import urllib.request

        phi = float(getattr(voyage, "phi_score", 0.0))
        voyage_id = str(getattr(voyage, "voyage_id", ""))
        agent_id = str(getattr(voyage, "agent_id", ""))
        journey_id = str(getattr(voyage, "journey_id", ""))
        modalities = getattr(voyage, "modalities_used", [])
        latent_snap = getattr(voyage, "latent_snapshot", [])[:16]
        started_at = float(getattr(voyage, "started_at", 0.0))
        completed_at = float(getattr(voyage, "completed_at", 0.0))
        duration_s = completed_at - started_at
        refined = bool(getattr(voyage, "skill_refinements", []))
        phi_dist_obj = getattr(voyage, "phi_distribution", None)

        gate_prob_val = "NONE"
        if phi_dist_obj is not None:
            try:
                gate_prob_val = str(round(phi_dist_obj.gate_probability(), 6))
            except Exception:
                pass

        phi_dist_str = "NONE"
        if phi_dist_obj is not None:
            try:
                d = phi_dist_obj.as_dict()
                phi_dist_str = (
                    '{"bins": '
                    + str(d.get("bins", []))
                    + ', "probs": '
                    + str(d.get("probs", []))
                    + "}"
                )
            except Exception:
                pass

        sid = (skill_id or agent_id).replace("'", "")
        mods_str = str(modalities)
        snap_str = str([round(x, 6) for x in latent_snap])
        surql = (
            f"CREATE evo_journey SET "
            f"voyage_id = '{voyage_id}', "
            f"agent_id = '{agent_id}', "
            f"journey_id = '{journey_id}', "
            f"skill_id = '{sid}', "
            f"phi_score = {phi}, "
            f"modalities = {mods_str}, "
            f"step_count = {len(self._recent_points)}, "
            f"duration_s = {duration_s}, "
            f"refined = {str(refined).lower()}, "
            f"valid_from = time::now(), "
            f"valid_to = NONE, "
            f"latent_snap = {snap_str}, "
            f"gate_prob = {gate_prob_val}, "
            f"phi_dist = {phi_dist_str};"
        )
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=surql.encode(),
            headers={
                "Accept": "application/json",
                "surreal-ns": "cohezion",
                "surreal-db": "cohezion",
                "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass

        # Cerebellum note for future ticks via _load_cerebellum_context RAG
        if skill_id:
            try:
                from pathlib import Path

                cerebellum_dir = Path.home() / "vaults" / "cohezion-vault" / "cerebellum"
                cerebellum_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.date.today().isoformat()
                slug = skill_id.lower()
                note_path = cerebellum_dir / f"{date_str}-skill-refinement-{slug}.md"
                gate_str = gate_prob_val if gate_prob_val != "NONE" else "n/a"
                note_path.write_text(
                    f"---\nskill: {skill_id}\ndate: {date_str}\n---\n"
                    f"Insight: phi={phi:.3f} gate_prob={gate_str} "
                    f"duration={duration_s:.1f}s modalities={modalities} "
                    f"refined={refined}\n"
                    f"Coherence: {phi:.4f}\n"
                )
            except Exception:
                pass

    def _persist_to_surreal(self, point: TrajectoryPoint) -> None:
        """Buffer trajectory point for batched SurrealDB persistence.

        Accumulates SurQL statements and flushes when buffer reaches
        _WRITE_BATCH_SIZE. Single HTTP POST per batch reduces round-trips
        by ~90% vs one-write-per-call (EXP-COMPOUND-1: 2400→240ms/session).
        """
        task = point.task_description[:100].replace("'", "")
        dims = (
            point.dimensions.tolist()
            if hasattr(point.dimensions, "tolist")
            else list(point.dimensions)
        )
        surql = (
            f"CREATE journey_transition SET dimensions = {dims}, "
            f"coherence = {point.coherence}, efficiency = {point.efficiency}, "
            f"operation_type = '{point.operation_type}', task = '{task}', "
            f"created = time::now();"
        )
        self._write_buffer.append(surql)
        if len(self._write_buffer) >= self._WRITE_BATCH_SIZE:
            self._flush_write_buffer()

    def _flush_write_buffer(self) -> None:
        """Flush all buffered SurQL statements in a single HTTP POST.

        Fire-and-forget: silently fails if SurrealDB is unavailable.
        """
        if not self._write_buffer:
            return
        import base64
        import urllib.request

        batch_sql = "\n".join(self._write_buffer)
        self._write_buffer.clear()
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=batch_sql.encode(),
            headers={
                "Accept": "application/json",
                "surreal-ns": "cohezion",
                "surreal-db": "cohezion",
                "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass

    def get_last_point(self) -> TrajectoryPoint | None:
        """Return the most recent trajectory point, or None if no points tracked."""
        return self._recent_points[-1] if self._recent_points else None

    def get_recent_point_count(self) -> int:
        """Return the number of points in the recent trajectory buffer."""
        return len(self._recent_points)

    def text_to_latent(self, text: str) -> np.ndarray:
        """Convert text to 2048D latent vector via FLUME encoding pipeline.

        Uses HFEmbeddingBridge (sentence-transformers) when available,
        falls back to deterministic hash-based encoding for environments
        without GPU/model dependencies.

        The 2048D vector represents the raw semantic embedding BEFORE
        the FLUME compression pipeline (2048→256→12D manifold).

        Args:
            text: Text to encode

        Returns:
            Normalized 2048D numpy array
        """
        # FLUME encoder path: 256D → tile to 2048D (preserves cosine similarity structure)
        if self._flume_encoder is not None and self._flume_encoder.is_available():
            emb = self._flume_encoder.encode(text).astype(np.float64)
            latent = np.tile(emb, 8)[:2048]
            norm = np.linalg.norm(latent)
            return latent / norm if norm > 0 else latent

        # Fallback: deterministic hash-based encoding
        # Always produces 2048D for consistency with FLUME compression pipeline
        import hashlib

        h = hashlib.sha512(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
        latent = rng.standard_normal(2048).astype(np.float64)
        norm = np.linalg.norm(latent)
        return latent / norm if norm > 0 else latent

    def encode_step_sequence(self, steps: list[dict]) -> np.ndarray:
        """Encode a sequence of journey steps to a deterministic 2048D embedding.

        Each step dict should have: trajectory (list[float]), coherence, novelty,
        improvement (floats), skill (str).  Returns a normalized unit vector in
        [-1, 1]^2048.
        """
        import hashlib

        feats = []
        for step in steps:
            traj = np.array(step.get("trajectory", [0.0] * 12), dtype=np.float64)
            scalars = np.array(
                [
                    float(step.get("coherence", 0.5)),
                    float(step.get("novelty", 0.5)),
                    float(step.get("improvement", 0.0)),
                    int(hashlib.md5(step.get("skill", "").encode()).hexdigest()[:8], 16) / 2**32,
                ],
                dtype=np.float64,
            )
            feats.append(np.concatenate([traj, scalars]))

        feat_arr = np.array(feats, dtype=np.float64)
        mean_f = feat_arr.mean(axis=0)
        std_f = feat_arr.std(axis=0) if len(feats) > 1 else np.zeros_like(mean_f)
        agg = np.concatenate([mean_f, std_f])

        # Hash-project aggregate to 2048D deterministically
        seed = int.from_bytes(hashlib.sha256(agg.tobytes()).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        embedding = rng.standard_normal(2048).astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding

    def holographic_project(self, latent: np.ndarray) -> np.ndarray:
        """Project latent vector to 12D manifold via chunk-mean projection.

        Splits the latent vector into 12 equal chunks, takes the mean of each
        chunk, then normalizes to [0, 1] via sigmoid. Cached by latent hash.

        Args:
            latent: Latent vector (any dimension, typically 2048D)

        Returns:
            12D manifold coordinates normalized to [0, 1]
        """
        # Cache key from latent hash
        cache_key = hash(latent.tobytes())
        if not hasattr(self, "_projection_cache"):
            self._projection_cache: dict[int, np.ndarray] = {}
        if cache_key in self._projection_cache:
            return self._projection_cache[cache_key]

        # Chunk-mean projection: split into 12 chunks, take mean of each
        latent_flat = latent.flatten().astype(np.float64)
        dim = 12
        chunk_size = len(latent_flat) // dim
        if chunk_size == 0:
            # Latent shorter than 12D — pad with zeros
            padded = np.zeros(dim * 1)
            padded[: len(latent_flat)] = latent_flat
            latent_flat = padded
            chunk_size = 1

        projected = np.array(
            [np.mean(latent_flat[i * chunk_size : (i + 1) * chunk_size]) for i in range(dim)]
        )

        # Normalize to [0, 1] via sigmoid
        result = (1.0 / (1.0 + np.exp(-projected * 5.0))).astype(np.float64)

        self._projection_cache[cache_key] = result
        return result

    def _compute_observer_consistency(self, current_12d: np.ndarray) -> float:
        """Compute observer consistency between current execution and previous.

        Uses OPH Axiom 2: overlapping observer patches must agree.
        Returns consistency score [0, 1] where 1 = perfect alignment.

        Wire 3: Observer Patch → JourneyTracker.
        """
        if len(self._recent_points) < 1:
            return 0.5  # HIHO default — no history to compare

        try:
            from cohezion.governance.flume_bridge import agent_state_to_patch_center
            from cohezion.physics.observer_patch import evo_observer_consistency
            from cohezion.physics.spinor import SpinorState

            # Current agent's Bloch sphere position from 12D state
            theta_curr, phi_curr = agent_state_to_patch_center(current_12d)
            spinor_curr = SpinorState.from_bloch(theta_curr, phi_curr)

            # Previous agent's position
            prev_12d = self._recent_points[-1].dimensions
            theta_prev, phi_prev = agent_state_to_patch_center(prev_12d)
            spinor_prev = SpinorState.from_bloch(theta_prev, phi_prev)

            # Compute OPH overlap consistency
            result = evo_observer_consistency("current", spinor_curr, "previous", spinor_prev)
            return result.consistency_score

        except (ImportError, ValueError, TypeError):
            return 0.5  # Fallback to HIHO if physics modules unavailable

    def _compute_chain_hash(self, prev_hash: str, payload: dict) -> str:
        """Compute SHA-256 chain hash linking prev_hash to the current payload.

        Binds the previous chain entry to the current payload so any
        tampering of historical records breaks all subsequent hashes.

        Args:
            prev_hash: chain_hash of the previous entry (or "0"*64 for genesis)
            payload: Serialisable dict of the current entry's content

        Returns:
            64-character hex SHA-256 digest
        """
        canonical = f"{prev_hash}:{json.dumps(payload, sort_keys=True, default=str)}"
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _record_chain_entry(
        self,
        chain_id: str,
        payload: dict,
        payload_type: str = "journey_transition",
    ) -> str:
        """Append one link to the hash chain for chain_id and persist to SurrealDB.

        Args:
            chain_id: Execution or journey ID used as the chain identifier
            payload: Content to hash (journey transition data)
            payload_type: Must match hash_chain ENUM constraint in schema

        Returns:
            The new chain_hash (hex digest)
        """
        state = self._chain_state.setdefault(chain_id, {"sequence": 0, "last_hash": "0" * 64})

        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        prev_hash = str(state["last_hash"])
        # chain_hash links prev_hash → payload_hash so verification needs only stored fields
        chain_hash = hashlib.sha256(f"{prev_hash}:{payload_hash}".encode()).hexdigest()
        sequence = int(state["sequence"])

        state["sequence"] = sequence + 1
        state["last_hash"] = chain_hash

        # Buffer the hash_chain write (same batch buffer as journey_transitions)
        surql = (
            f"CREATE hash_chain SET "
            f"chain_id = '{chain_id}', "
            f"sequence = {sequence}, "
            f"prev_hash = '{prev_hash}', "
            f"payload_hash = '{payload_hash}', "
            f"chain_hash = '{chain_hash}', "
            f"payload_type = '{payload_type}', "
            f"payload_ref = '{chain_id}:{sequence}', "
            f"created_at = time::now();"
        )
        self._write_buffer.append(surql)
        if len(self._write_buffer) >= self._WRITE_BATCH_SIZE:
            self._flush_write_buffer()

        return chain_hash

    def verify_chain(self, chain_id: str) -> bool:
        """Verify the integrity of the stored hash chain for chain_id.

        Reads all hash_chain records from SurrealDB ordered by sequence
        and re-derives each chain_hash from the previous entry.  Any
        mismatch indicates tampering or data corruption.

        Args:
            chain_id: The chain to verify (execution_id / journey_id)

        Returns:
            True if every link is intact, False if any link is broken or
            if the chain cannot be read from SurrealDB.
        """
        try:
            import base64
            import urllib.request

            surql = (
                f"SELECT sequence, prev_hash, payload_hash, chain_hash "
                f"FROM hash_chain WHERE chain_id = '{chain_id}' ORDER BY sequence ASC;"
            )
            req = urllib.request.Request(
                "http://localhost:8001/sql",
                data=surql.encode(),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())

            entries = result[0].get("result", []) if result else []
            if not entries:
                logger.warning("verify_chain: no entries found for chain_id=%s", chain_id)
                return False

            for entry in entries:
                prev_hash = entry["prev_hash"]
                payload_hash = entry["payload_hash"]
                stored_chain_hash = entry["chain_hash"]
                recomputed = hashlib.sha256(f"{prev_hash}:{payload_hash}".encode()).hexdigest()
                if stored_chain_hash != recomputed:
                    logger.warning(
                        "verify_chain: broken link at sequence=%s for chain_id=%s",
                        entry["sequence"],
                        chain_id,
                    )
                    return False

            return True

        except Exception as exc:
            logger.warning("verify_chain failed (cannot read SurrealDB): %s", exc)
            return False

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
        phi_scores = np.array([(p.metadata or {}).get("phi_score", 0.0) for p in points])

        # Compute smoothness (variance of dimension changes)
        dimensions = np.array([p.dimensions for p in points])
        if len(dimensions) > 1:
            diffs = np.diff(dimensions, axis=0)
            smoothness = 1.0 - np.mean(np.abs(diffs))
        else:
            smoothness = 1.0

        # Compute convergence (trend toward stable state)
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
        """Compute thermodynamic state from recent trajectory.

        Converts the trajectory history into thermodynamic quantities:
        entropy production, free energy, susceptibility, heat capacity.

        Returns
        -------
        ThermodynamicState | None
            Current thermodynamic state, or None if insufficient data.
        """
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
                    energy=None,  # Estimated from coherence
                )

            return thermo.compute_state()
        except Exception as e:
            logger.warning("Thermodynamic computation failed (non-blocking): %s", e)
            return None

    def compute_topological_summary(self) -> dict[str, float]:
        """Compute topological persistence summary of recent trajectory.

        Analyzes the shape of the trajectory in 12D space to detect:
        - Clusters (distinct behavioral modes)
        - Loops (repetitive behavioral cycles)
        - Topological complexity (persistence entropy)

        Returns
        -------
        dict[str, float]
            Topological summary. Empty dict if insufficient data.
        """
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
        """Compute trajectory quality with thermodynamic + topological metrics.

        Extends compute_trajectory_quality with novel metrics that have
        real mathematical foundations.

        Parameters
        ----------
        points : list[TrajectoryPoint] | None
            Points to analyze. If None, uses recent buffer.

        Returns
        -------
        dict[str, Any]
            Extended quality metrics including thermodynamic state
            and topological features.
        """
        pts = points if points is not None else list(self._recent_points)
        base = self.compute_trajectory_quality(pts)

        # Add thermodynamic state
        thermo = self.compute_thermodynamic_state()
        if thermo is not None:
            base["entropy_production_rate"] = thermo.entropy_production_rate
            base["free_energy"] = thermo.free_energy
            base["susceptibility"] = thermo.susceptibility
            base["heat_capacity"] = thermo.heat_capacity
            base["effective_temperature"] = thermo.temperature

        # Add topological features
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
        """Create a journey tracker.

        Args:
            seed: Random seed for deterministic behavior

        Returns:
            JourneyTracker instance
        """
        return JourneyTracker(seed=seed)
