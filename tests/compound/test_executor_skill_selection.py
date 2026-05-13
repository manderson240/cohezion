"""Tests for CompoundExecutor skill suggestion integration."""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def executor(mock_mcp_client):
    """Create compound executor with mock MCP client."""
    # Patch VaultLogger during initialization
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)

    # Replace logger with a fresh mock that persists after initialization
    mock_logger = MagicMock()
    mock_logger.get_experience_guidance.return_value = {
        "relevant_context": [],
        "guidance": "No prior patterns found.",
    }
    executor.logger = mock_logger
    return executor


class TestExecutorSkillSuggestion:
    """Tests for skill suggestion in CompoundExecutor."""

    def test_suggest_skills_integration(self, executor):
        """Test suggest_skills returns ranked list."""
        # Mock the vault_find_relevant_context to return skill patterns
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "generator_generate", "content": "coherence: 0.9"},
            {"title": "analyzer_generate", "content": "coherence: 0.7"},
        ]

        suggestions = executor.suggest_skills(
            "Generate creative content",
            "generate",
            top_k=2,
        )

        assert len(suggestions) == 2
        assert suggestions[0][0] == "generator"  # Highest score first
        assert suggestions[0][1] > suggestions[1][1]

    def test_suggest_skills_returns_tuples(self, executor):
        """Test that suggest_skills returns (skill_name, score) tuples."""
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "skill1", "content": "coherence: 0.8"}
        ]

        suggestions = executor.suggest_skills(
            "Task",
            "generate",
        )

        assert len(suggestions) > 0
        assert isinstance(suggestions[0], tuple)
        assert len(suggestions[0]) == 2
        assert isinstance(suggestions[0][0], str)  # skill_name
        assert isinstance(suggestions[0][1], float)  # score

    def test_suggest_skills_top_k_limit(self, executor):
        """Test that suggest_skills respects top_k parameter."""
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "skill1", "content": "coherence: 0.9"},
            {"title": "skill2", "content": "coherence: 0.8"},
            {"title": "skill3", "content": "coherence: 0.7"},
            {"title": "skill4", "content": "coherence: 0.6"},
        ]

        suggestions = executor.suggest_skills(
            "Task",
            "generate",
            top_k=2,
        )

        assert len(suggestions) == 2

    def test_suggest_skills_empty_results(self, executor):
        """Test suggest_skills with no matches."""
        executor.mcp_client.vault_find_relevant_context.return_value = []

        suggestions = executor.suggest_skills(
            "Obscure task",
            "generate",
        )

        assert suggestions == []

    def test_suggest_skills_error_handling(self, executor):
        """Test suggest_skills gracefully handles errors."""
        executor.mcp_client.vault_find_relevant_context.side_effect = RuntimeError("Vault error")

        suggestions = executor.suggest_skills(
            "Task",
            "generate",
        )

        assert suggestions == []

    def test_suggest_skills_operation_types(self, executor):
        """Test suggest_skills with different operation types."""
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "analyzer", "content": "coherence: 0.85"}
        ]

        for op_type in ["generate", "analyze", "search", "transform", "persist"]:
            suggestions = executor.suggest_skills(
                "Task",
                op_type,
            )

            # Should work for all operation types
            assert isinstance(suggestions, list)

    def test_suggest_skills_passes_project(self, executor):
        """Test that suggest_skills passes project parameter."""
        executor.mcp_client.vault_find_relevant_context.return_value = []

        executor.suggest_skills(
            "Task",
            "generate",
            project="my_project",
        )

        # Verify project was passed to vault
        executor.mcp_client.vault_find_relevant_context.assert_called()
        call_kwargs = executor.mcp_client.vault_find_relevant_context.call_args.kwargs
        assert call_kwargs.get("project") == "my_project"


class TestExecutorSkillSelectionWorkflow:
    """Integration tests for skill selection workflow."""

    def test_get_guidance_then_suggest_skills(self, executor):
        """Test typical workflow: get guidance then suggest skills."""
        executor.logger.get_experience_guidance.return_value = {"relevant_context": [{"pattern": "test"}]}
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "skill1", "content": "coherence: 0.9"}
        ]

        # Step 1: Get experience guidance
        guidance = executor.get_experience_guidance("Task description")
        assert "relevant_context" in guidance

        # Step 2: Suggest skills
        suggestions = executor.suggest_skills(
            "Task description",
            "generate",
        )

        assert len(suggestions) > 0
        assert suggestions[0][0] == "skill1"

    def test_skill_selection_with_multiple_operations(self, executor):
        """Test selecting different skills for different operations."""

        # Setup different patterns for different operations
        def vault_response(query, project=None):
            if "generate" in query:
                return [{"title": "generator", "content": "coherence: 0.9"}]
            elif "analyze" in query:
                return [{"title": "analyzer", "content": "coherence: 0.85"}]
            else:
                return []

        executor.mcp_client.vault_find_relevant_context.side_effect = vault_response

        # Different operations should select different skills
        gen_skills = executor.suggest_skills("Generate content", "generate")
        ana_skills = executor.suggest_skills("Analyze data", "analyze")

        assert gen_skills[0][0] == "generator"
        assert ana_skills[0][0] == "analyzer"

    def test_skill_suggestions_ranked_by_performance(self, executor):
        """Test that suggestions are ranked by performance metrics."""
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "skill1", "content": "coherence: 0.95\nefficiency: 0.9"},
            {"title": "skill2", "content": "coherence: 0.6\nefficiency: 0.6"},
            {"title": "skill3", "content": "coherence: 0.8\nefficiency: 0.85"},
        ]

        suggestions = executor.suggest_skills("Task", "generate", top_k=3)

        # Should be ranked by composite score
        assert len(suggestions) == 3
        # skill1 should be highest
        assert suggestions[0][0] == "skill1"
        assert suggestions[0][1] > suggestions[1][1]
        assert suggestions[1][1] >= suggestions[2][1]


class TestExecutorSkillSelectionIntegrationWithExecution:
    """Tests for skill selection integrated with task execution."""

    def test_execution_with_suggested_skill(self, executor):
        """Test executing with a skill suggested from vault."""
        executor.mcp_client.vault_find_relevant_context.return_value = [
            {"title": "recommended_skill", "content": "coherence: 0.9"}
        ]

        # Get suggestions
        suggestions = executor.suggest_skills("Task", "generate", top_k=1)

        if suggestions:
            suggested_skill = suggestions[0][0]

            # Now execute with the suggested skill
            with (
                patch.object(
                    executor.logger,
                    "get_experience_guidance",
                    return_value={"context": "test"},
                ),
                patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
                patch.object(executor.logger, "log_execution_result"),
                patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
            ):

                def execute_fn(guidance):
                    return "output", {"coherence": 0.85}

                result = executor.execute_task(
                    "Task description",
                    suggested_skill,
                    "generate",
                    execute_fn,
                )

                assert result.success
                assert result.output == "output"

    def test_fallback_to_default_skill(self, executor):
        """Test fallback when vault suggestions empty."""
        executor.mcp_client.vault_find_relevant_context.return_value = []

        # Get suggestions (should be empty)
        suggestions = executor.suggest_skills("Unusual task", "generate")
        assert suggestions == []

        # Should still be able to execute with default skill
        default_skill = "fallback_skill"

        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn(guidance):
                return "output", {"coherence": 0.7}

            result = executor.execute_task(
                "Task description",
                default_skill,
                "generate",
                execute_fn,
            )

            assert result.success
