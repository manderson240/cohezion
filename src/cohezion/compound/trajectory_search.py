"""Trajectory search engine for experience-guided execution.

Queries ExperienceCollector using semantic similarity and VAE embeddings
to find past trajectories similar to current task. Enables agents to
learn from historical execution patterns.

Architecture:
    1. Encode task description using ExperienceEncoder
    2. Query ExperienceCollector for similar experiences
    3. Rank by trajectory quality (phi_score, coherence)
    4. Return top-k trajectories with outcome data

Example:
    ```python
    search = TrajectorySearchEngine(collector, encoder)

    results = search.find_similar_trajectories(
        task_description="Generate creative ideas",
        operation_type="generate",
        top_k=5,
    )

    for result in results:
        print(f"Task: {result.task}, coherence: {result.coherence:.2f}")
        print(f"Recommendation: {result.guidance}")
    ```
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class TrajectorySearchResult:
    """Single search result from trajectory database."""

    task_description: str
    operation_type: str
    coherence: float
    phi_score: float
    trajectory_smoothness: float
    trajectory_convergence: float
    similarity_score: float  # Cosine similarity to query
    success: bool
    guidance: str  # Human-readable recommendation


class TrajectorySearchEngine:
    """Search engine for finding similar past execution trajectories.

    Uses semantic similarity (via ExperienceEncoder) to find tasks similar
    to the current one, then ranks by execution quality metrics to provide
    actionable guidance.

    Example:
        ```python
        from cohezion.flume.experience_collector import ExperienceCollector
        from cohezion.flume.experience_encoder import ExperienceEncoder

        collector = ExperienceCollector()
        encoder = ExperienceEncoder()
        search = TrajectorySearchEngine(collector, encoder)

        results = search.find_similar_trajectories(
            "Implement new feature",
            "generate",
            top_k=3,
        )
        ```
    """

    def __init__(
        self,
        collector: Any,  # ExperienceCollector
        encoder: Any,  # ExperienceEncoder
        similarity_threshold: float = 0.5,
    ):
        """Initialize trajectory search engine.

        Args:
            collector: ExperienceCollector instance
            encoder: ExperienceEncoder instance
            similarity_threshold: Minimum cosine similarity for matches
        """
        self.collector = collector
        self.encoder = encoder
        self.similarity_threshold = similarity_threshold
        logger.debug(
            "Initialized TrajectorySearchEngine (threshold=%.2f)", similarity_threshold
        )

    def find_similar_trajectories(
        self,
        task_description: str,
        operation_type: str,
        top_k: int = 5,
        min_coherence: float = 0.4,  # HIHO threshold
    ) -> list[TrajectorySearchResult]:
        """Find past trajectories similar to current task.

        Args:
            task_description: Description of current task
            operation_type: Type of operation (generate, analyze, etc.)
            top_k: Number of results to return
            min_coherence: Minimum coherence for recommendations

        Returns:
            List of TrajectorySearchResult, ranked by similarity * quality
        """
        # Step 1: Get all experiences from collector
        try:
            experiences = self.collector.collect_all(max_samples=1000)
        except Exception as e:
            logger.warning("Failed to collect experiences: %s", e)
            return []

        if not experiences:
            logger.debug("No experiences found for trajectory search")
            return []

        # Step 2: Encode query task
        query_vector = self._encode_task(task_description, operation_type)

        # Step 3: Compute similarity to all experiences
        results = []
        for exp in experiences:
            # Encode experience
            exp_vector = self.encoder.encode_experience(exp)

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_vector, exp_vector)

            if similarity < self.similarity_threshold:
                continue  # Skip low-similarity matches

            # Extract metrics
            coherence = exp.get("coherence", 0.5)
            phi_score = exp.get("phi_score", 0.5)
            smoothness = exp.get("trajectory_smoothness", 0.5)
            convergence = exp.get("trajectory_convergence", 0.5)
            success = exp.get("success", False)

            # Filter by minimum coherence (don't learn from bad executions)
            if coherence < min_coherence:
                continue

            # Generate guidance
            guidance = self._generate_guidance(exp, coherence, phi_score, smoothness, convergence, success)

            results.append(
                TrajectorySearchResult(
                    task_description=exp.get("task_description", ""),
                    operation_type=exp.get("operation_type", ""),
                    coherence=coherence,
                    phi_score=phi_score,
                    trajectory_smoothness=smoothness,
                    trajectory_convergence=convergence,
                    similarity_score=similarity,
                    success=success,
                    guidance=guidance,
                )
            )

        # Step 4: Rank by combined score (similarity * quality)
        results.sort(
            key=lambda r: r.similarity_score * (r.coherence * 0.5 + r.phi_score * 0.5),
            reverse=True,
        )

        # Step 5: Return top-k
        top_results = results[:top_k]
        logger.info(
            "Found %d similar trajectories (top coherence: %.2f, similarity: %.2f)",
            len(top_results),
            top_results[0].coherence if top_results else 0.0,
            top_results[0].similarity_score if top_results else 0.0,
        )

        return top_results

    def _encode_task(self, task_description: str, operation_type: str) -> np.ndarray:
        """Encode task description using ExperienceEncoder.

        Args:
            task_description: Task description text
            operation_type: Operation type

        Returns:
            256D encoded vector
        """
        # Create minimal experience dict for encoding
        exp = {
            "task_description": task_description,
            "operation_type": operation_type,
            # Default values for required fields
            "coherence": 0.5,
            "phi_score": 0.5,
            "trajectory_smoothness": 0.5,
            "trajectory_convergence": 0.5,
            "success": True,
            "state_trajectory": [],
        }

        return self.encoder.encode_experience(exp)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _generate_guidance(
        self,
        exp: dict,
        coherence: float,
        phi_score: float,
        smoothness: float,
        convergence: float,
        success: bool,
    ) -> str:
        """Generate human-readable guidance from trajectory data.

        Args:
            exp: Experience dictionary
            coherence: Coherence score
            phi_score: Trajectory quality score
            smoothness: Trajectory smoothness
            convergence: HIHO convergence
            success: Whether execution succeeded

        Returns:
            Guidance text
        """
        if not success:
            return f"Similar task failed (coherence={coherence:.2f}). Approach with caution."

        if coherence >= 0.7 and phi_score >= 0.7:
            return (
                f"Similar task had excellent outcomes"
                f" (coherence={coherence:.2f}, phi={phi_score:.2f})."
                f" High confidence."
            )
        elif coherence >= 0.5:
            return f"Similar task succeeded (coherence={coherence:.2f}). Moderate confidence."
        else:
            return f"Similar task barely succeeded (coherence={coherence:.2f}). Low confidence."
