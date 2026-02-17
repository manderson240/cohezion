"""Guidance enhancer for experience-guided execution.

Transforms trajectory search results into actionable execution guidance.
Aggregates insights from similar past executions to provide:
- Recommended approaches from successful trajectories
- Warnings from failed trajectories
- Confidence scores based on similarity and outcome quality

Architecture:
    1. Receive trajectory search results
    2. Aggregate patterns across results
    3. Generate recommendations (do's and don'ts)
    4. Compute confidence scores
    5. Return enhanced guidance dict for executor

Example:
    ```python
    enhancer = GuidanceEnhancer()

    enhanced = enhancer.enhance_guidance(
        base_guidance={"decisions": [...], "patterns": [...]},
        trajectory_results=[...],  # From TrajectorySearchEngine
    )

    # enhanced includes:
    # - recommendations: What worked well
    # - warnings: What to avoid
    # - confidence: How reliable this guidance is
    ```
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class EnhancedGuidance:
    """Enhanced execution guidance from trajectory analysis."""

    recommendations: list[str]  # What to do (from successful trajectories)
    warnings: list[str]  # What to avoid (from failed trajectories)
    confidence: float  # Overall confidence in guidance (0.0-1.0)
    similar_task_count: int  # Number of similar past tasks found
    avg_coherence: float  # Average coherence of similar tasks
    avg_phi_score: float  # Average trajectory quality
    base_guidance: dict[str, Any]  # Original vault guidance


class GuidanceEnhancer:
    """Enhance execution guidance using trajectory analysis.

    Aggregates insights from similar past trajectories to provide
    actionable recommendations for current execution.

    Example:
        ```python
        from cohezion.compound.trajectory_search import TrajectorySearchEngine

        search = TrajectorySearchEngine(collector, encoder)
        enhancer = GuidanceEnhancer()

        # Find similar trajectories
        results = search.find_similar_trajectories(
            "Implement new feature", "generate"
        )

        # Enhance guidance
        enhanced = enhancer.enhance_guidance(
            base_guidance={"decisions": [], "patterns": []},
            trajectory_results=results,
        )

        print(f"Confidence: {enhanced.confidence:.2f}")
        for rec in enhanced.recommendations:
            print(f"  ✓ {rec}")
        ```
    """

    def __init__(
        self,
        min_confidence_threshold: float = 0.5,
        high_quality_threshold: float = 0.7,
    ):
        """Initialize guidance enhancer.

        Args:
            min_confidence_threshold: Minimum confidence for recommendations
            high_quality_threshold: Coherence threshold for "high quality"
        """
        self.min_confidence_threshold = min_confidence_threshold
        self.high_quality_threshold = high_quality_threshold
        logger.debug(
            "Initialized GuidanceEnhancer (min_confidence=%.2f, high_quality=%.2f)",
            min_confidence_threshold,
            high_quality_threshold,
        )

    def enhance_guidance(
        self,
        base_guidance: dict[str, Any],
        trajectory_results: list[Any],  # TrajectorySearchResult
    ) -> EnhancedGuidance:
        """Enhance guidance with trajectory analysis.

        Args:
            base_guidance: Base guidance from vault (decisions, patterns, etc.)
            trajectory_results: Search results from TrajectorySearchEngine

        Returns:
            EnhancedGuidance with recommendations, warnings, confidence
        """
        if not trajectory_results:
            logger.debug("No trajectory results, returning base guidance only")
            return EnhancedGuidance(
                recommendations=[],
                warnings=[],
                confidence=0.0,
                similar_task_count=0,
                avg_coherence=0.0,
                avg_phi_score=0.0,
                base_guidance=base_guidance,
            )

        # Separate successful and failed trajectories
        successful = [r for r in trajectory_results if r.success and r.coherence >= 0.5]
        failed = [r for r in trajectory_results if not r.success or r.coherence < 0.5]

        # Generate recommendations from successful trajectories
        recommendations = self._generate_recommendations(successful)

        # Generate warnings from failed trajectories
        warnings = self._generate_warnings(failed)

        # Compute aggregate metrics
        all_coherences = [r.coherence for r in trajectory_results]
        all_phi_scores = [r.phi_score for r in trajectory_results]
        avg_coherence = sum(all_coherences) / len(all_coherences) if all_coherences else 0.0
        avg_phi_score = sum(all_phi_scores) / len(all_phi_scores) if all_phi_scores else 0.0

        # Compute confidence (higher if many high-quality results)
        high_quality_count = sum(
            1 for r in trajectory_results if r.coherence >= self.high_quality_threshold and r.success
        )
        confidence = min(
            1.0,
            (high_quality_count / max(1, len(trajectory_results))) * (avg_coherence * 0.5 + avg_phi_score * 0.5),
        )

        logger.info(
            "Enhanced guidance: %d recommendations, %d warnings, confidence=%.2f",
            len(recommendations),
            len(warnings),
            confidence,
        )

        return EnhancedGuidance(
            recommendations=recommendations,
            warnings=warnings,
            confidence=confidence,
            similar_task_count=len(trajectory_results),
            avg_coherence=avg_coherence,
            avg_phi_score=avg_phi_score,
            base_guidance=base_guidance,
        )

    def _generate_recommendations(self, successful: list[Any]) -> list[str]:
        """Generate recommendations from successful trajectories.

        Args:
            successful: List of successful TrajectorySearchResult

        Returns:
            List of recommendation strings
        """
        if not successful:
            return []

        recommendations = []

        # High-quality trajectories (coherence >= 0.7)
        high_quality = [r for r in successful if r.coherence >= self.high_quality_threshold]
        if high_quality:
            # Sort by quality
            high_quality.sort(key=lambda r: r.coherence * 0.5 + r.phi_score * 0.5, reverse=True)
            best = high_quality[0]
            recommendations.append(
                f"Approach similar to '{best.task_description[:50]}...' "
                f"had excellent results (coherence={best.coherence:.2f}, "
                f"phi={best.phi_score:.2f})"
            )

        # Smooth trajectories (low variance)
        smooth = [r for r in successful if r.trajectory_smoothness >= 0.7]
        if smooth:
            recommendations.append(
                f"{len(smooth)}/{len(successful)} similar tasks had smooth trajectories. "
                f"Maintain steady progress through fabrics."
            )

        # Convergent trajectories (approach HIHO)
        convergent = [r for r in successful if r.trajectory_convergence >= 0.7]
        if convergent:
            recommendations.append(
                f"{len(convergent)}/{len(successful)} similar tasks converged to HIHO. "
                f"Target coherence ≈ 0.5 for stability."
            )

        return recommendations[:3]  # Top 3 recommendations

    def _generate_warnings(self, failed: list[Any]) -> list[str]:
        """Generate warnings from failed trajectories.

        Args:
            failed: List of failed TrajectorySearchResult

        Returns:
            List of warning strings
        """
        if not failed:
            return []

        warnings = []

        # High failure rate
        if len(failed) >= 3:
            warnings.append(f"Warning: {len(failed)} similar tasks had poor outcomes. Proceed with caution.")

        # Low smoothness (chaotic trajectories)
        chaotic = [r for r in failed if r.trajectory_smoothness < 0.3]
        if chaotic:
            warnings.append(
                f"{len(chaotic)} similar tasks had chaotic trajectories (high variance across fabrics). Plan carefully."
            )

        # Low convergence (didn't reach HIHO)
        divergent = [r for r in failed if r.trajectory_convergence < 0.3]
        if divergent:
            warnings.append(f"{len(divergent)} similar tasks failed to converge. Monitor coherence closely.")

        return warnings[:2]  # Top 2 warnings

    def to_dict(self, enhanced: EnhancedGuidance) -> dict[str, Any]:
        """Convert EnhancedGuidance to dictionary format.

        Args:
            enhanced: EnhancedGuidance instance

        Returns:
            Dictionary representation for executor
        """
        return {
            "recommendations": enhanced.recommendations,
            "warnings": enhanced.warnings,
            "confidence": enhanced.confidence,
            "similar_task_count": enhanced.similar_task_count,
            "avg_coherence": enhanced.avg_coherence,
            "avg_phi_score": enhanced.avg_phi_score,
            **enhanced.base_guidance,  # Merge in base guidance
        }
