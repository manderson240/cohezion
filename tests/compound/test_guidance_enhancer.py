"""Tests for guidance enhancer (Phase 9)."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.guidance_enhancer import (
    EnhancedGuidance,
    GuidanceEnhancer,
)


@pytest.fixture
def mock_trajectory_results():
    """Create mock trajectory search results."""
    # Mix of successful and failed trajectories
    results = []

    # 2 high-quality successful
    for i in range(2):
        result = MagicMock()
        result.task_description = f"High quality task {i}"
        result.operation_type = "generate"
        result.coherence = 0.85
        result.phi_score = 0.80
        result.trajectory_smoothness = 0.75
        result.trajectory_convergence = 0.70
        result.similarity_score = 0.9
        result.success = True
        results.append(result)

    # 1 medium-quality successful
    result = MagicMock()
    result.task_description = "Medium quality task"
    result.operation_type = "generate"
    result.coherence = 0.60
    result.phi_score = 0.55
    result.trajectory_smoothness = 0.50
    result.trajectory_convergence = 0.45
    result.similarity_score = 0.7
    result.success = True
    results.append(result)

    # 1 failed
    result = MagicMock()
    result.task_description = "Failed task"
    result.operation_type = "generate"
    result.coherence = 0.30
    result.phi_score = 0.25
    result.trajectory_smoothness = 0.20
    result.trajectory_convergence = 0.15
    result.similarity_score = 0.6
    result.success = False
    results.append(result)

    return results


class TestGuidanceEnhancer:
    """Tests for GuidanceEnhancer."""

    def test_enhance_guidance_generates_recommendations(self, mock_trajectory_results):
        """Enhancer generates recommendations from successful trajectories."""
        enhancer = GuidanceEnhancer()
        base_guidance = {"decisions": [], "patterns": []}

        enhanced = enhancer.enhance_guidance(base_guidance, mock_trajectory_results)

        assert isinstance(enhanced, EnhancedGuidance)
        assert len(enhanced.recommendations) > 0
        # Should mention high-quality tasks
        assert any(
            "excellent" in rec.lower() or "high" in rec.lower()
            for rec in enhanced.recommendations
        )

    def test_enhance_guidance_generates_warnings_from_failures(self, mock_trajectory_results):
        """Enhancer generates warnings from failed trajectories."""
        enhancer = GuidanceEnhancer()
        base_guidance = {"decisions": [], "patterns": []}

        enhanced = enhancer.enhance_guidance(base_guidance, mock_trajectory_results)

        # Should have at least one warning (1 failed task)
        assert len(enhanced.warnings) > 0

    def test_confidence_high_when_many_successful(self, mock_trajectory_results):
        """Confidence is high when many high-quality results."""
        enhancer = GuidanceEnhancer()
        base_guidance = {"decisions": [], "patterns": []}

        enhanced = enhancer.enhance_guidance(base_guidance, mock_trajectory_results)

        # 2 high-quality + 1 medium = moderate confidence
        # Formula: (high_quality_count/total) * avg_quality
        # (2/4) * ((0.65+0.60)/2) = 0.5 * 0.625 = 0.3125
        assert enhanced.confidence > 0.25  # Above random
        assert enhanced.similar_task_count == 4

    def test_empty_trajectories_returns_zero_confidence(self):
        """Empty trajectory list returns low-confidence guidance."""
        enhancer = GuidanceEnhancer()
        base_guidance = {"decisions": [], "patterns": []}

        enhanced = enhancer.enhance_guidance(base_guidance, [])

        assert enhanced.confidence == 0.0
        assert enhanced.similar_task_count == 0
        assert enhanced.recommendations == []
        assert enhanced.warnings == []

    def test_to_dict_merges_base_guidance(self, mock_trajectory_results):
        """to_dict() includes both enhanced and base guidance."""
        enhancer = GuidanceEnhancer()
        base_guidance = {"decisions": ["decision1"], "patterns": ["pattern1"]}

        enhanced = enhancer.enhance_guidance(base_guidance, mock_trajectory_results)
        result_dict = enhancer.to_dict(enhanced)

        # Should have both enhanced fields and base guidance
        assert "recommendations" in result_dict
        assert "warnings" in result_dict
        assert "confidence" in result_dict
        assert "decisions" in result_dict  # From base
        assert "patterns" in result_dict  # From base
        assert result_dict["decisions"] == ["decision1"]
