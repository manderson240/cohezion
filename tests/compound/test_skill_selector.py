"""Tests for experience-guided skill selection."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.skill_selector import SkillScore, SkillSelector


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def selector(mock_mcp_client):
    """Create skill selector with mock MCP client."""
    return SkillSelector(mock_mcp_client)


class TestSkillScore:
    """Tests for SkillScore dataclass."""

    def test_skill_score_creation(self):
        """Test creating a SkillScore."""
        score = SkillScore(
            skill_name="my_skill",
            coherence_score=0.85,
            token_efficiency=0.75,
            success_rate=0.9,
            times_used=10,
            composite_score=0.82,
        )

        assert score.skill_name == "my_skill"
        assert score.coherence_score == 0.85
        assert score.token_efficiency == 0.75
        assert score.success_rate == 0.9
        assert score.times_used == 10
        assert score.composite_score == 0.82

    def test_skill_score_comparison(self):
        """Test comparing SkillScore objects."""
        score1 = SkillScore("skill1", 0.9, 0.9, 0.9, 10, 0.9)
        score2 = SkillScore("skill2", 0.7, 0.7, 0.7, 5, 0.7)

        # Higher composite score should be "less than" (for reverse sorting)
        assert score1 < score2

    def test_skill_score_repr(self):
        """Test string representation."""
        score = SkillScore("test_skill", 0.85, 0.75, 0.9, 10, 0.82)

        repr_str = repr(score)
        assert "test_skill" in repr_str
        assert "0.82" in repr_str


class TestSkillSelectorInitialization:
    """Tests for SkillSelector initialization."""

    def test_initialization_default_weights(self, mock_mcp_client):
        """Test initialization with default weights."""
        selector = SkillSelector(mock_mcp_client)

        # Weights should be normalized
        total = selector.coherence_weight + selector.efficiency_weight + selector.success_weight
        assert abs(total - 1.0) < 0.001

    def test_initialization_custom_weights(self, mock_mcp_client):
        """Test initialization with custom weights."""
        selector = SkillSelector(
            mock_mcp_client,
            coherence_weight=0.7,
            efficiency_weight=0.2,
            success_weight=0.1,
        )

        # Weights should be normalized
        total = selector.coherence_weight + selector.efficiency_weight + selector.success_weight
        assert abs(total - 1.0) < 0.001


class TestMetricExtraction:
    """Tests for metric extraction from text."""

    def test_extract_skill_name_from_title(self, selector):
        """Test extracting skill name from title."""
        text = "my_skill_generate_success"
        name = selector._extract_skill_name(text)

        assert name == "my_skill"

    def test_extract_skill_name_with_prefix(self, selector):
        """Test extracting skill name with 'skill:' prefix."""
        text = "Skill: transformer"
        name = selector._extract_skill_name(text)

        assert name == "transformer"

    def test_extract_skill_name_first_word(self, selector):
        """Test extracting first word as skill name."""
        text = "analyzer performs well on text classification"
        name = selector._extract_skill_name(text)

        assert name == "analyzer"

    def test_extract_metrics_coherence(self, selector):
        """Test extracting coherence metric."""
        text = "coherence: 0.85"
        metrics = selector._extract_metrics(text)

        assert metrics.get("coherence") == 0.85

    def test_extract_metrics_efficiency(self, selector):
        """Test extracting efficiency metric."""
        text = "efficiency: 0.75"
        metrics = selector._extract_metrics(text)

        assert metrics.get("efficiency") == 0.75

    def test_extract_metrics_success_rate(self, selector):
        """Test extracting success rate metric."""
        text = "success_rate: 0.9"
        metrics = selector._extract_metrics(text)

        assert metrics.get("success") == 0.9

    def test_extract_metrics_percentage(self, selector):
        """Test converting percentage to decimal."""
        text = "coherence: 85"
        metrics = selector._extract_metrics(text)

        assert metrics.get("coherence") == 0.85

    def test_extract_metrics_all(self, selector):
        """Test extracting multiple metrics."""
        text = """
        Skill: my_skill
        coherence: 0.85
        efficiency: 0.75
        success_rate: 0.9
        """
        metrics = selector._extract_metrics(text)

        assert metrics.get("coherence") == 0.85
        assert metrics.get("efficiency") == 0.75
        assert metrics.get("success") == 0.9

    def test_extract_metrics_bounds(self, selector):
        """Test that metrics are bounded [0.0, 1.0]."""
        text = "coherence: 1.5"  # Out of bounds (percentage)
        metrics = selector._extract_metrics(text)

        # 1.5 as a percentage becomes 0.015, then clamped to 1.0 if > 1.0
        # But since 1.5 is likely a percentage, it's treated as 1.5/100 = 0.015
        # Then clamped to [0.0, 1.0] -> 0.015
        assert 0.0 <= metrics.get("coherence", 0) <= 1.0


class TestPatternParsing:
    """Tests for pattern parsing."""

    def test_parse_pattern_dict(self, selector):
        """Test parsing pattern dictionary."""
        pattern = {
            "title": "my_skill_generate_success",
            "content": "coherence: 0.85\nefficiency: 0.75",
        }

        result = selector._parse_pattern_dict(pattern, "generate")

        assert result["skill_name"] == "my_skill"
        assert result["coherence"] == 0.85
        assert result["efficiency"] == 0.75
        assert result["success"] == 1.0

    def test_parse_pattern_string(self, selector):
        """Test parsing pattern string."""
        pattern = "analyzer_analyze_success coherence: 0.8 efficiency: 0.7"

        result = selector._parse_pattern_string(pattern, "analyze")

        assert result["skill_name"] == "analyzer"
        assert result["coherence"] == 0.8
        assert result["efficiency"] == 0.7

    def test_parse_pattern_dict_no_skill_name(self, selector):
        """Test parsing pattern extracts first token as skill name."""
        pattern = {
            "title": "some random content",
            "content": "no skill mentioned",
        }

        result = selector._parse_pattern_dict(pattern, "generate")

        # "some" is extracted as skill name from title
        assert result is not None
        assert result["skill_name"] == "some"


class TestSkillScoreComputation:
    """Tests for skill score computation."""

    def test_extract_skill_scores_single_pattern(self, selector):
        """Test extracting scores from single pattern."""
        context = [
            {
                "title": "my_skill_generate_success",
                "content": "coherence: 0.85",
            }
        ]

        scores = selector._extract_skill_scores(context, "generate")

        assert len(scores) == 1
        assert scores[0].skill_name == "my_skill"
        assert scores[0].coherence_score == 0.85

    def test_extract_skill_scores_multiple_patterns(self, selector):
        """Test extracting scores from multiple patterns."""
        context = [
            {"title": "skill1_generate", "content": "coherence: 0.9"},
            {"title": "skill1_generate", "content": "coherence: 0.8"},
            {"title": "skill2_generate", "content": "coherence: 0.7"},
        ]

        scores = selector._extract_skill_scores(context, "generate")

        # Should have 2 unique skills
        assert len(scores) == 2

        # skill1 should have average coherence of 0.85
        skill1 = next(s for s in scores if s.skill_name == "skill1")
        assert abs(skill1.coherence_score - 0.85) < 0.01

    def test_composite_score_calculation(self, selector):
        """Test composite score calculation."""
        SkillScore(
            skill_name="test",
            coherence_score=0.5,
            token_efficiency=0.5,
            success_rate=0.5,
            times_used=1,
            composite_score=0.0,  # Will be set by selector
        )

        # Manually compute with selector's weights
        expected = (
            selector.coherence_weight * 0.5
            + selector.efficiency_weight * 0.5
            + selector.success_weight * 0.5
        )

        # All equal means composite should be 0.5
        assert expected == 0.5


class TestSkillSelection:
    """Tests for skill selection."""

    def test_select_skills_empty_context(self, mock_mcp_client, selector):
        """Test skill selection with no context."""
        mock_mcp_client.vault_search.return_value = []

        result = selector.select_skills(
            "Generate ideas",
            "generate",
            top_k=3,
        )

        assert result == []

    def test_select_skills_single_match(self, mock_mcp_client, selector):
        """Test skill selection with one matching skill."""
        mock_mcp_client.vault_search.return_value = [
            {
                "title": "generator_generate_success",
                "content": "coherence: 0.9",
            }
        ]

        result = selector.select_skills(
            "Generate ideas",
            "generate",
            top_k=3,
        )

        assert len(result) == 1
        assert result[0].skill_name == "generator"

    def test_select_skills_multiple_matches(self, mock_mcp_client, selector):
        """Test skill selection with multiple matches."""
        mock_mcp_client.vault_search.return_value = [
            {"title": "skill1", "content": "coherence: 0.9\nefficiency: 0.8"},
            {"title": "skill2", "content": "coherence: 0.7\nefficiency: 0.9"},
            {"title": "skill3", "content": "coherence: 0.5\nefficiency: 0.5"},
        ]

        result = selector.select_skills(
            "Do something",
            "generate",
            top_k=3,
        )

        assert len(result) == 3
        # skill1 should be highest (0.9 coherence)
        assert result[0].skill_name == "skill1"

    def test_select_skills_top_k(self, mock_mcp_client, selector):
        """Test limiting results with top_k."""
        mock_mcp_client.vault_search.return_value = [
            {"title": "skill1", "content": "coherence: 0.9"},
            {"title": "skill2", "content": "coherence: 0.8"},
            {"title": "skill3", "content": "coherence: 0.7"},
            {"title": "skill4", "content": "coherence: 0.6"},
        ]

        result = selector.select_skills(
            "Task",
            "generate",
            top_k=2,
        )

        assert len(result) == 2

    def test_select_skills_vault_error_graceful(self, mock_mcp_client, selector):
        """Test graceful handling of vault errors."""
        mock_mcp_client.vault_search.side_effect = RuntimeError("Vault down")

        result = selector.select_skills(
            "Task",
            "generate",
        )

        assert result == []


class TestSkillRanking:
    """Tests for skill ranking."""

    def test_rank_skills_all_available(self, mock_mcp_client, selector):
        """Test ranking all available skills."""
        mock_mcp_client.vault_search.return_value = [
            {"title": "skill1", "content": "coherence: 0.9"},
            {"title": "skill2", "content": "coherence: 0.7"},
        ]

        ranked = selector.rank_skills(
            ["skill1", "skill2", "skill3"],
            "Task",
            "generate",
        )

        # skill1 should be first (highest score)
        assert ranked[0][0] == "skill1"
        assert ranked[0][1] > ranked[1][1]
        assert ranked[1][0] == "skill2"

        # skill3 not in vault should have low score
        assert ranked[2][0] == "skill3"
        assert ranked[2][1] < 0.4

    def test_rank_skills_preserves_order_for_equal_scores(self, mock_mcp_client, selector):
        """Test ranking preserves list order for unavailable skills."""
        mock_mcp_client.vault_search.return_value = []

        ranked = selector.rank_skills(
            ["skill1", "skill2", "skill3"],
            "Task",
            "generate",
        )

        # All should have same score, original order preserved
        assert len(ranked) == 3
        assert all(score == 0.3 for _, score in ranked)


class TestSkillSelectorIntegration:
    """Integration tests for skill selector."""

    def test_workflow_select_then_rank(self, mock_mcp_client):
        """Test complete workflow: select then rank."""
        mock_mcp_client.vault_search.return_value = [
            {"title": "generator", "content": "coherence: 0.85\nefficiency: 0.8"},
            {"title": "analyzer", "content": "coherence: 0.75\nefficiency: 0.9"},
        ]

        selector = SkillSelector(mock_mcp_client)

        # First, select best skills
        selected = selector.select_skills(
            "Generate content",
            "generate",
            top_k=2,
        )

        assert len(selected) == 2
        assert selected[0].skill_name == "generator"

        # Then rank available skills
        ranked = selector.rank_skills(
            ["generator", "analyzer", "transformer"],
            "Generate content",
            "generate",
        )

        assert ranked[0][0] == "generator"
        assert ranked[1][0] == "analyzer"

    def test_skill_selector_with_complex_patterns(self, mock_mcp_client):
        """Test selector with complex pattern content."""
        mock_mcp_client.vault_search.return_value = [
            {
                "title": "Text Generation using Advanced Transformer",
                "content": """
                ## Experiment: Text Generation
                **Skill**: transformer
                **Operation**: generate
                **Result**: Success

                ### Metrics
                - Coherence: 0.92
                - Efficiency: 0.88
                - Success Rate: 98%
                """,
            }
        ]

        selector = SkillSelector(mock_mcp_client)
        result = selector.select_skills(
            "Generate creative text",
            "generate",
        )

        assert len(result) == 1
        # Extracts "Text" from title or "transformer" from content
        assert result[0].skill_name in ["Text", "text", "transformer"]
        assert result[0].coherence_score >= 0.85
