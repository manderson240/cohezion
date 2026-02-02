"""Core Universe Simulation Engine for Cohezion.

Captures every agent interaction as 12D/512D manifold trajectory data,
enabling universe simulation, experience learning, and reality precipitation.

The 12:512 Dual-State Manifold:
- 512D Latent: Semantic hypervolume ("Soul") - intent, meaning, reasoning
- 12D Axiomatic: Physical projection ("Body") - observable, measurable state

Every task becomes a journey through this manifold, with coherence tracked
at the HIHO (0.5) stability point.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import numpy as np

from cohezion.flume.autoencoder import FlumeEncoder

logger = logging.getLogger(__name__)


@dataclass
class AxiomaticState:
    """12D physical projection of agent state (The "Body").

    Dimensions:
    - Physical: spatial_x, spatial_y, spatial_z, temporal
    - Logical: physics, biology, logic, quantum
    - Abstract: field, control, novelty, precipitation
    """

    spatial_x: float = 0.0
    spatial_y: float = 0.0
    spatial_z: float = 0.0
    temporal: float = 0.0
    physics: float = 0.5  # Target: HIHO at 0.5
    biology: float = 0.5
    logic: float = 0.5
    quantum: float = 0.5
    field: float = 0.5
    control: float = 0.5
    novelty: float = 0.5
    precipitation: float = 0.0

    def to_vector(self) -> list[float]:
        return [
            self.spatial_x,
            self.spatial_y,
            self.spatial_z,
            self.temporal,
            self.physics,
            self.biology,
            self.logic,
            self.quantum,
            self.field,
            self.control,
            self.novelty,
            self.precipitation,
        ]

    @classmethod
    def from_vector(cls, vector: list[float]) -> AxiomaticState:
        return cls(*vector)

    def coherence_score(self) -> float:
        """Calculate HIHO coherence (0.5 = optimal stability)."""
        # Variance from 0.5 across all dimensions
        dimensions = [
            self.physics,
            self.biology,
            self.logic,
            self.quantum,
            self.field,
            self.control,
            self.novelty,
        ]
        variance = sum((d - 0.5) ** 2 for d in dimensions) / len(dimensions)
        # Convert to coherence: 1.0 = perfect 0.5, 0.0 = extreme deviation
        return 1.0 - min(variance * 4, 1.0)  # Scale so 0.25 variance = 0 coherence


@dataclass
class LatentState:
    """512D semantic hypervolume (The "Soul").

    Contains the semantic intent, reasoning, and meaning of the agent.
    """

    embedding: list[float]  # 512-dimensional vector
    semantic_intent: str  # Human-readable description
    reasoning_chain: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self):
        if len(self.embedding) != 512:
            # Pad or truncate to 512
            if len(self.embedding) < 512:
                self.embedding.extend([0.0] * (512 - len(self.embedding)))
            else:
                self.embedding = self.embedding[:512]


@dataclass
class TrajectoryPoint:
    """A single point in the FLUME evolution through the manifold."""

    step_number: int
    timestamp: float
    axiomatic: AxiomaticState
    latent: LatentState
    coherence: float
    action_taken: str
    result_achieved: str | None = None


@dataclass
class UniverseJourney:
    """Complete journey of a task through the 12D/512D manifold."""

    id: str
    agent_name: str
    intent: str  # Original query/task
    status: str = "active"  # active, completed, failed

    # States
    initial_axiomatic: AxiomaticState = field(default_factory=AxiomaticState)
    initial_latent: LatentState | None = None

    # Trajectory
    trajectory: list[TrajectoryPoint] = field(default_factory=list)

    # Results
    precipitation: dict[str, Any] = field(default_factory=dict)  # Code, docs, actions
    knowledge_extracted: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    final_coherence: float = 0.0
    final_phi_score: float = 0.0

    def add_trajectory_point(self, point: TrajectoryPoint) -> None:
        """Add a step in the journey."""
        self.trajectory.append(point)
        self.final_coherence = point.coherence

    def complete(self, precipitation: dict[str, Any], phi_score: float) -> None:
        """Mark journey as complete with results."""
        self.status = "completed"
        self.precipitation = precipitation
        self.final_phi_score = phi_score
        self.completed_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Serialize for database storage."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "intent": self.intent,
            "status": self.status,
            "initial_axiomatic": self.initial_axiomatic.to_vector(),
            "initial_latent_embedding": self.initial_latent.embedding
            if self.initial_latent
            else [],
            "trajectory_count": len(self.trajectory),
            "precipitation_type": list(self.precipitation.keys()),
            "final_coherence": self.final_coherence,
            "final_phi_score": self.final_phi_score,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


class EncoderProtocol(Protocol):
    """Protocol for text-to-vector encoders."""

    async def encode(self, text: str) -> list[float]: ...


class UniverseSimulationEngine:
    """Core engine for universe simulation and journey tracking.

    Every agent interaction flows through:
    1. Intent Embedding (512D) - Capture semantic meaning
    2. Axiomatic Projection (12D) - Project to physical space
    3. FLUME Evolution - Navigate trajectory toward goal
    4. Coherence Monitoring - Maintain HIHO at 0.5
    5. Reality Precipitation - Manifest results (code/docs/actions)
    6. Knowledge Extraction - Capture learnings for future use
    """

    def __init__(
        self,
        encoder: EncoderProtocol | None = None,
        db_client: Any | None = None,
        local_storage_path: Path | str = "data/universe",
    ):
        self.encoder = encoder
        self.db_client = db_client
        self.local_storage = Path(local_storage_path)
        self.local_storage.mkdir(parents=True, exist_ok=True)

        # Fallback encoder using simple hashing if no FLUME available
        self._fallback_encoder = None

    async def _ensure_encoder(self) -> EncoderProtocol:
        """Ensure we have an encoder, using fallback if needed."""
        if self.encoder:
            return self.encoder

        if self._fallback_encoder is None:
            # Simple TF-IDF style encoder as fallback
            self._fallback_encoder = SimpleEncoder()

        return self._fallback_encoder

    async def start_journey(
        self, agent_name: str, intent: str, context: dict[str, Any] | None = None
    ) -> UniverseJourney:
        """Begin a new journey through the manifold.

        Args:
            agent_name: Name of the agent initiating journey
            intent: The task/query to accomplish
            context: Optional context (previous journeys, skills, etc.)

        Returns:
            UniverseJourney tracking object
        """
        journey_id = f"journey_{int(time.time())}_{uuid4().hex[:8]}"

        # Encode intent to 512D latent space
        encoder = await self._ensure_encoder()
        embedding = await encoder.encode(intent)
        latent = LatentState(
            embedding=embedding, semantic_intent=intent, confidence=0.7
        )

        # Project to 12D axiomatic space
        axiomatic = self._project_to_axiomatic(embedding, context)

        journey = UniverseJourney(
            id=journey_id,
            agent_name=agent_name,
            intent=intent,
            initial_axiomatic=axiomatic,
            initial_latent=latent,
        )

        logger.info(f"🌌 Universe journey started: {journey_id} by {agent_name}")
        logger.info(f"   Intent: {intent[:60]}...")
        logger.info(f"   Initial coherence: {axiomatic.coherence_score():.3f}")

        # Persist to storage
        await self._persist_journey(journey)

        return journey

    def _project_to_axiomatic(
        self, embedding_512d: list[float], context: dict[str, Any] | None = None
    ) -> AxiomaticState:
        """Project 512D latent vector to 12D axiomatic space.

        Uses dimensionality reduction to map semantic space to physical.
        """
        # Simple projection: use 12 representative dimensions
        # In production, this would use a learned projection matrix
        step = 512 // 12
        representative_dims = [embedding_512d[i * step] for i in range(12)]

        # Normalize to 0-1 range and center around 0.5
        normalized = []
        for val in representative_dims:
            # Assuming embedding values are roughly -1 to 1
            norm = (val + 1) / 2  # Now 0 to 1
            normalized.append(norm)

        axiomatic = AxiomaticState(
            spatial_x=normalized[0],
            spatial_y=normalized[1],
            spatial_z=normalized[2],
            temporal=time.time(),  # Actual timestamp
            physics=normalized[4],
            biology=normalized[5],
            logic=normalized[6],
            quantum=normalized[7],
            field=normalized[8],
            control=normalized[9],
            novelty=normalized[10],
            precipitation=0.0,  # Will increase as results manifest
        )

        return axiomatic

    async def evolve_trajectory(
        self,
        journey: UniverseJourney,
        action: str,
        result: str | None = None,
        phi_score: float = 0.5,
    ) -> TrajectoryPoint:
        """Evolve the journey by one step through the manifold.

        Args:
            journey: Current journey being tracked
            action: Action taken at this step
            result: Result of the action (if completed)
            phi_score: Quality score from self-evaluation

        Returns:
            TrajectoryPoint recording this step
        """
        step_num = len(journey.trajectory)

        # Update axiomatic state based on progress
        current_axiomatic = journey.initial_axiomatic
        if journey.trajectory:
            current_axiomatic = journey.trajectory[-1].axiomatic

        # Evolve state: move toward goal, adjust coherence
        new_axiomatic = AxiomaticState(
            spatial_x=current_axiomatic.spatial_x + 0.1,
            spatial_y=current_axiomatic.spatial_y + 0.05,
            spatial_z=current_axiomatic.spatial_z,
            temporal=time.time(),
            physics=self._toward_target(current_axiomatic.physics, 0.5, phi_score),
            biology=self._toward_target(current_axiomatic.biology, 0.5, phi_score),
            logic=self._toward_target(current_axiomatic.logic, 0.5, phi_score),
            quantum=self._toward_target(current_axiomatic.quantum, 0.5, phi_score),
            field=self._toward_target(current_axiomatic.field, 0.5, phi_score),
            control=self._toward_target(current_axiomatic.control, 0.5, phi_score),
            novelty=min(current_axiomatic.novelty + 0.1, 1.0),  # Increase novelty
            precipitation=phi_score,  # Precipitation = quality of result
        )

        # Encode new semantic state
        encoder = await self._ensure_encoder()
        new_embedding = await encoder.encode(f"{action} {result or ''}")
        new_latent = LatentState(
            embedding=new_embedding,
            semantic_intent=action,
            reasoning_chain=[action],
            confidence=phi_score,
        )

        # Calculate coherence
        coherence = new_axiomatic.coherence_score()

        point = TrajectoryPoint(
            step_number=step_num,
            timestamp=time.time(),
            axiomatic=new_axiomatic,
            latent=new_latent,
            coherence=coherence,
            action_taken=action,
            result_achieved=result,
        )

        journey.add_trajectory_point(point)

        logger.debug(
            f"   Trajectory step {step_num}: coherence={coherence:.3f}, phi={phi_score:.3f}"
        )

        return point

    def _toward_target(self, current: float, target: float, factor: float) -> float:
        """Move current value toward target by factor amount."""
        distance = target - current
        return current + distance * factor * 0.5  # 0.5 for gentle convergence

    async def precipitate_reality(
        self, journey: UniverseJourney, outputs: dict[str, Any], phi_score: float
    ) -> dict[str, Any]:
        """Manifest the journey results into reality (code, docs, actions).

        Args:
            journey: Completed journey
            outputs: Dict of outputs (code, documentation, decisions, etc.)
            phi_score: Final quality score

        Returns:
            Precipitation manifest with metadata
        """
        precipitation = {
            "journey_id": journey.id,
            "manifested_at": datetime.now().isoformat(),
            "outputs": outputs,
            "phi_score": phi_score,
            "coherence_at_manifestation": journey.final_coherence,
            "trajectory_length": len(journey.trajectory),
        }

        journey.complete(precipitation, phi_score)

        # Extract knowledge for future use
        knowledge = self._extract_knowledge(journey)
        journey.knowledge_extracted = knowledge

        logger.info(f"✨ Reality precipitated: {journey.id}")
        logger.info(f"   Phi score: {phi_score:.3f}")
        logger.info(f"   Outputs: {list(outputs.keys())}")

        # Persist final state
        await self._persist_journey(journey)

        return precipitation

    def _extract_knowledge(self, journey: UniverseJourney) -> list[dict[str, Any]]:
        """Extract reusable knowledge from completed journey."""
        knowledge = []

        # Pattern: What worked well?
        if journey.final_phi_score > 0.8:
            knowledge.append(
                {
                    "type": "success_pattern",
                    "pattern": f"High-quality {journey.agent_name} execution",
                    "conditions": [
                        "phi > 0.8",
                        f"coherence ~ {journey.final_coherence:.2f}",
                    ],
                    "applicability": [journey.agent_name, journey.intent[:50]],
                }
            )

        # Pattern: Trajectory insights
        if len(journey.trajectory) > 3:
            knowledge.append(
                {
                    "type": "process_pattern",
                    "pattern": "Multi-step refinement successful",
                    "step_count": len(journey.trajectory),
                    "avg_coherence": sum(t.coherence for t in journey.trajectory)
                    / len(journey.trajectory),
                }
            )

        return knowledge

    async def _persist_journey(self, journey: UniverseJourney) -> None:
        """Persist journey to storage (DB or local)."""
        # Try database first
        if self.db_client:
            try:
                await self.db_client.create("universe_journey", journey.to_dict())
                return
            except Exception as e:
                logger.debug(f"DB persist failed, using local: {e}")

        # Fallback to local JSON
        filepath = self.local_storage / f"{journey.id}.json"
        with open(filepath, "w") as f:
            json.dump(journey.to_dict(), f, indent=2, default=str)

    async def find_similar_journeys(
        self, query_embedding: list[float], threshold: float = 0.7, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find similar past journeys for experience replay."""
        # This would query SurrealDB vector index in production
        # For now, return empty list as placeholder
        logger.debug(f"Searching for similar journeys (threshold={threshold})")
        return []


class SimpleEncoder:
    """Fallback encoder using simple hashing when FLUME unavailable."""

    async def encode(self, text: str) -> list[float]:
        """Create simple embedding from text hash."""
        # Use hash to generate deterministic vector
        hash_val = hashlib.sha256(text.encode()).hexdigest()

        # Convert hash to 512D vector
        vector = []
        for i in range(512):
            # Use bytes from hash
            byte_idx = i % len(hash_val)
            val = int(hash_val[byte_idx], 16) / 16.0  # 0-1
            vector.append(val)

        return vector
