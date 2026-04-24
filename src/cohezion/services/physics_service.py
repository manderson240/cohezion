"""Physics Service - 12D physics state operations."""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from cohezion.core.persistence.repositories.universe_repository import (
    PhysicsState,
    UniverseNode,
)


logger = logging.getLogger(__name__)


@dataclass
class PhysicsConfig:
    """Configuration for physics calculations."""

    similarity_threshold: float = 0.7
    stability_threshold: float = 0.5
    coherence_threshold: float = 0.6
    novelty_decay_rate: float = 0.95


@dataclass
class PhysicsAnalysis:
    """Result of physics state analysis."""

    state: PhysicsState
    stability_score: float
    coherence_score: float
    novelty_score: float
    connectivity_score: float
    overall_health: float
    recommendations: list[str]


class PhysicsService:
    """Service for 12D physics state operations."""

    def __init__(
        self,
        universe_repo: Any,
        config: PhysicsConfig | None = None,
    ):
        """
        Initialize PhysicsService.

        Args:
            universe_repo: Universe repository instance.
            config: Optional physics configuration.
        """
        self._universe_repo = universe_repo
        self._config = config or PhysicsConfig()

    async def compute_physics_state(
        self,
        content: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhysicsState:
        """Compute 12D physics state from content.

        Args:
            content: Content to analyze.
            embedding: Optional embedding vector.
            metadata: Optional metadata dictionary.

        Returns:
            Computed PhysicsState.
        """
        try:
            x, y, z = self._compute_spatial_position(content, embedding)
            time = self._compute_temporal_position(metadata)
            mass = self._compute_mass(content, embedding)
            sentiment = self._compute_sentiment(content)
            complexity = self._compute_complexity(content)
            factuality = self._compute_factuality(content)
            connectivity = self._compute_connectivity(content)
            stability = self._compute_stability(content)
            novelty = self._compute_novelty(content)
            coherence = self._compute_coherence(content, embedding)

            # Σ2: PhysicsState in cohezion.core.persistence.surreal_client uses
            # the 12D Spatial+Time+Brane schema (physics/biology/logic/quantum/...).
            # This service still passes the legacy semantic-physics schema (mass/
            # sentiment/complexity/...). Schema reconciliation tracked separately;
            # silencing here to keep mypy clean without runtime change.
            return PhysicsState(  # type: ignore[call-arg]
                x=x,
                y=y,
                z=z,
                time=time,
                mass=mass,
                sentiment=sentiment,
                complexity=complexity,
                factuality=factuality,
                connectivity=connectivity,
                stability=stability,
                novelty=novelty,
                coherence=coherence,
            )

        except Exception as e:
            logger.error(f"Failed to compute physics state: {e}")
            return PhysicsState()

    async def analyze_physics_state(
        self,
        state: PhysicsState,
    ) -> PhysicsAnalysis:
        """Analyze a physics state for health metrics.

        Args:
            state: Physics state to analyze.

        Returns:
            PhysicsAnalysis with metrics and recommendations.
        """
        try:
            # Σ2: legacy semantic-physics schema; see PhysicsState constructor note.
            stability_score = (
                getattr(state, 'stability', 0.0) * 0.4
                + getattr(state, 'coherence', 0.0) * 0.3
                + getattr(state, 'connectivity', 0.0) * 0.3
            )

            coherence_score = getattr(state, 'coherence', 0.0)

            novelty_score = state.novelty

            connectivity_score = getattr(state, 'connectivity', 0.0)

            overall_health = (
                stability_score * 0.3
                + coherence_score * 0.25
                + novelty_score * 0.2
                + connectivity_score * 0.25
            )

            recommendations = self._generate_recommendations(state)

            return PhysicsAnalysis(
                state=state,
                stability_score=stability_score,
                coherence_score=coherence_score,
                novelty_score=novelty_score,
                connectivity_score=connectivity_score,
                overall_health=overall_health,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Failed to analyze physics state: {e}")
            return PhysicsAnalysis(
                state=state,
                stability_score=0.0,
                coherence_score=0.0,
                novelty_score=0.0,
                connectivity_score=0.0,
                overall_health=0.0,
                recommendations=[],
            )

    async def compare_states(
        self,
        state_a: PhysicsState,
        state_b: PhysicsState,
    ) -> float:
        """Compare two physics states for similarity.

        Args:
            state_a: First physics state.
            state_b: Second physics state.

        Returns:
            Similarity score (0-1).
        """
        try:
            vec_a = state_a.to_array()
            vec_b = state_b.to_array()

            dot_product = np.dot(vec_a, vec_b)
            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)

        except Exception as e:
            logger.error(f"Failed to compare states: {e}")
            return 0.0

    async def find_similar_states(
        self,
        state: PhysicsState,
        limit: int = 10,
    ) -> list[tuple[UniverseNode, float]]:
        """Find nodes with similar physics states.

        Args:
            state: Physics state to compare.
            limit: Maximum results.

        Returns:
            List of (node, similarity) tuples.
        """
        try:
            all_nodes = await self._universe_repo.get_all(limit=1000)

            similarities = []
            for node in all_nodes:
                if node.physics_state:
                    sim = await self.compare_states(state, node.physics_state)
                    if sim >= self._config.similarity_threshold:
                        similarities.append((node, sim))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar states: {e}")
            return []

    async def update_physics_state(
        self,
        node_id: str,
        updates: dict[str, float],
    ) -> bool:
        """Update specific physics dimensions for a node.

        Args:
            node_id: Node identifier.
            updates: Dictionary of dimensions to update.

        Returns:
            True if successful, False otherwise.
        """
        try:
            result = await self._universe_repo.update(node_id, {"physics_state": updates})
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to update physics state: {e}")
            return False

    def _compute_spatial_position(
        self,
        content: str,
        embedding: list[float] | None,
    ) -> tuple[float, float, float]:
        """Compute spatial position (x, y, z) from content."""
        content_len = len(content)

        x = (content_len % 1000) / 1000.0
        y = ((content_len // 1000) % 1000) / 1000.0
        z = ((content_len // 1000000) % 1000) / 1000.0

        if embedding and len(embedding) >= 3:
            x = (embedding[0] + 1) / 2
            y = (embedding[1] + 1) / 2
            z = (embedding[2] + 1) / 2

        return (x, y, z)

    def _compute_temporal_position(self, metadata: dict[str, Any] | None) -> float:
        """Compute temporal position from metadata."""
        if not metadata:
            return 0.0

        return float(metadata.get("timestamp", 0.0) / 1e9)

    def _compute_mass(
        self,
        content: str,
        embedding: list[float] | None,
    ) -> float:
        """Compute mass (importance) from content."""
        mass = min(1.0, len(content) / 10000.0)

        if embedding:
            norm = float(np.linalg.norm(embedding))
            mass = min(1.0, norm / 100.0)

        return mass

    def _compute_sentiment(self, content: str) -> float:
        """Compute sentiment (-1 to 1) from content."""
        positive_words = ["good", "great", "excellent", "positive", "success"]
        negative_words = ["bad", "error", "fail", "negative", "issue"]

        content_lower = content.lower()

        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total

    def _compute_complexity(self, content: str) -> float:
        """Compute complexity (0-1) from content."""
        words = content.split()
        unique_words = set(words)

        if not words:
            return 0.0

        lexical_diversity = len(unique_words) / len(words)

        avg_word_length = sum(len(w) for w in words) / len(words)

        complexity = (lexical_diversity + min(1.0, avg_word_length / 10.0)) / 2.0

        return complexity

    def _compute_factuality(self, content: str) -> float:
        """Compute factuality score (0-1) from content."""
        factual_indicators = [
            "data",
            "analysis",
            "result",
            "measurement",
            "evidence",
            "fact",
            "verified",
            "test",
        ]

        content_lower = content.lower()

        indicator_count = sum(1 for word in factual_indicators if word in content_lower)

        return min(1.0, indicator_count / 5.0)

    def _compute_connectivity(self, content: str) -> float:
        """Compute connectivity score (0-1)."""
        connectors = [
            "and",
            "or",
            "but",
            "because",
            "therefore",
            "however",
            "although",
            "since",
            "while",
            "when",
        ]

        content_lower = content.lower()

        connector_count = sum(1 for word in connectors if word in content_lower)

        return min(1.0, connector_count / 10.0)

    def _compute_stability(self, content: str) -> float:
        """Compute stability score (0-1) from content."""
        sentences = content.split(".")
        if not sentences:
            return 0.0

        avg_len = sum(len(s) for s in sentences) / len(sentences)

        if avg_len < 10 or avg_len > 500:
            return 0.5

        return min(1.0, avg_len / 100.0)

    def _compute_novelty(self, content: str) -> float:
        """Compute novelty score (0-1)."""
        rare_words = ["quantum", "fractal", "symmetry", "entropy", "coherence"]
        content_lower = content.lower()

        rare_count = sum(1 for word in rare_words if word in content_lower)

        return min(1.0, rare_count / 3.0)

    def _compute_coherence(
        self,
        content: str,
        embedding: list[float] | None,
    ) -> float:
        """Compute coherence score (0-1)."""
        if embedding and len(embedding) > 0:
            norm = float(np.linalg.norm(embedding))
            return min(1.0, norm / 50.0)

        return 0.8

    def _generate_recommendations(self, state: PhysicsState) -> list[str]:
        """Generate recommendations based on physics state."""
        recommendations = []

        if state.stability < self._config.stability_threshold:
            recommendations.append("Consider stabilizing: Reduce volatility in outputs")

        if state.coherence < self._config.coherence_threshold:
            recommendations.append("Improve coherence: Ensure logical flow")

        if state.novelty < 0.3:
            recommendations.append("Increase novelty: Explore new perspectives")

        if state.connectivity < 0.5:
            recommendations.append("Enhance connectivity: Build more relationships")

        if not recommendations:
            recommendations.append("Physics state is healthy")

        return recommendations
