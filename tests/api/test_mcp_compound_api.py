"""Automated API tests for MCP Compound Server.

Tests MCP tool endpoints with mocked dependencies.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.api
@pytest.mark.compound
class TestMCPCompoundAPI:
    """API tests for MCP Compound Server tools."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock CompoundSessionManager for isolated testing."""
        mock = MagicMock()
        mock.start_session.return_value = {
            "session_id": "test-session-123",
            "cache_entries_loaded": 128,
        }
        mock.check_alignment.return_value = MagicMock(
            coherence=0.75, should_proceed=True, issues=[]
        )
        mock.end_session.return_value = {"session_id": "test-session-123", "duration_seconds": 3600}
        return mock

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for vault operations."""
        mock = AsyncMock()
        mock.vault_health.return_value = {"status": "healthy"}
        mock.vault_write.return_value = "logs/test.json"
        mock.vault_log_experiment.return_value = "experiments/test.md"
        return mock

    @pytest.mark.fast
    async def test_compound_start_session_success(self, mock_session_manager):
        """[P0] Session start returns success with valid params."""
        from cohezion.mcp.compound_server import compound_start_session

        with patch("cohezion.mcp.compound_server.session_manager", mock_session_manager):
            result = await compound_start_session(max_cache_entries=256)

        assert result["status"] == "success"
        assert result["session_id"] == "test-session-123"
        assert result["cache_entries_loaded"] == 128

    @pytest.mark.fast
    async def test_compound_start_session_error_handling(self):
        """[P0] Session start handles errors gracefully."""
        from cohezion.mcp.compound_server import compound_start_session

        with patch("cohezion.mcp.compound_server.session_manager") as mock:
            mock.start_session.side_effect = Exception("Database error")
            result = await compound_start_session()

        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.fast
    async def test_compound_check_alignment_high_coherence(self, mock_session_manager):
        """[P0] Alignment check passes with high coherence."""
        from cohezion.mcp.compound_server import compound_check_alignment

        with patch("cohezion.mcp.compound_server.session_manager", mock_session_manager):
            result = await compound_check_alignment(request="Test request", threshold=0.5)

        assert result["status"] == "success"
        assert result["should_proceed"] is True
        assert result["coherence"] == 0.75

    @pytest.mark.fast
    async def test_compound_check_alignment_low_coherence(self):
        """[P0] Alignment check blocks with low coherence."""
        from cohezion.mcp.compound_server import compound_check_alignment

        mock_session = MagicMock()
        mock_session.check_alignment.return_value = MagicMock(
            coherence=0.3, should_proceed=False, issues=["Ambiguous request"]
        )

        with patch("cohezion.mcp.compound_server.session_manager", mock_session):
            result = await compound_check_alignment(request="Unclear request", threshold=0.5)

        assert result["status"] == "success"
        assert result["should_proceed"] is False
        assert result["coherence"] == 0.3

    @pytest.mark.fast
    async def test_compound_check_alignment_no_session(self):
        """[P1] Alignment check errors when no session active."""
        from cohezion.mcp.compound_server import compound_check_alignment

        with patch("cohezion.mcp.compound_server.session_manager", None):
            result = await compound_check_alignment(request="Test")

        assert result["status"] == "error"
        assert "session" in result["error"].lower()

    @pytest.mark.fast
    async def test_cache_get_metrics_success(self):
        """[P0] Cache metrics returns valid data structure."""
        from cohezion.mcp.compound_server import cache_get_metrics

        mock_optimizer = MagicMock()
        mock_optimizer.get_metrics.return_value = {"overall_hit_rate": 0.82, "total_requests": 1000}

        with patch(
            "cohezion.swarm.token_cache_optimizer.get_token_cache_optimizer",
            return_value=mock_optimizer,
        ):
            result = await cache_get_metrics()

        assert result["status"] == "success"
        assert "metrics" in result
        assert result["metrics"]["overall_hit_rate"] == 0.82

    @pytest.mark.fast
    async def test_ralph_lopps_review_finds_issues(self):
        """[P0] Ralph Lopps review identifies code issues."""
        from cohezion.mcp.compound_server import ralph_lopps_review

        code_with_issues = """
async def execute(request):
    return await process(request)
"""

        result = await ralph_lopps_review(code=code_with_issues, context="")

        assert result["status"] == "success"
        assert result["total_findings"] > 0
        assert len(result["findings"]) > 0

    @pytest.mark.fast
    async def test_learning_capture_persists_to_vault(self, mock_mcp_client):
        """[P0] Learning capture persists execution results."""
        from cohezion.mcp.compound_server import learning_capture

        execution_result = json.dumps(
            {
                "request": "Test task",
                "success": True,
                "tokens_used": 5000,
                "lessons": ["Lesson learned"],
            }
        )

        with patch("cohezion.mcp.compound_server.get_mcp_client", return_value=mock_mcp_client):
            with patch("cohezion.mcp.compound_server.retrospection") as mock_retro:
                mock_retro.capture_learning = AsyncMock(return_value="logs/test.json")
                result = await learning_capture(execution_result)

        assert result["status"] == "success"

    @pytest.mark.fast
    async def test_skill_refinement_input_validation(self):
        """[P0] Skill refinement validates inputs."""
        from cohezion.mcp.compound_server import skill_refinement_apply

        # Test invalid skill_name (path traversal attempt)
        result = await skill_refinement_apply(
            skill_name="../etc/passwd", refinement_type="token_optimization"
        )

        assert result["status"] == "error"
        assert "invalid" in result["error"].lower()

    @pytest.mark.fast
    async def test_skill_refinement_invalid_type(self):
        """[P0] Skill refinement validates refinement_type."""
        from cohezion.mcp.compound_server import skill_refinement_apply

        result = await skill_refinement_apply(
            skill_name="TOKEN_EFFICIENCY_PRIME", refinement_type="invalid_type"
        )

        assert result["status"] == "error"
        assert "refinement_type" in result["error"].lower()

    @pytest.mark.fast
    async def test_autoresearch_analyze_identifies_opportunities(self):
        """[P0] Autoresearch analyzes metrics and finds improvements."""
        from cohezion.mcp.compound_server import autoresearch_analyze

        metrics = json.dumps({"cache_hit_rate": 0.45, "avg_tokens_per_request": 15000})

        result = await autoresearch_analyze(metrics_json=metrics)

        assert result["status"] == "success"
        assert len(result["opportunities"]) > 0


@pytest.mark.integration
@pytest.mark.compound
class TestMCPCompoundIntegrationFlow:
    """Integration tests for complete MCP workflows."""

    @pytest.mark.fast
    async def test_session_lifecycle(self):
        """[P0] Complete session start → check → end workflow."""
        from cohezion.mcp.compound_server import (
            compound_check_alignment,
            compound_end_session,
            compound_start_session,
        )

        # Mock session manager to return dict-like objects
        mock_summary = {
            "session_id": "test-lifecycle-123",
            "cache_entries_loaded": 64,
            "duration_seconds": 300,
        }

        # Need to patch the global session_manager BEFORE importing functions
        with patch("cohezion.mcp.compound_server.session_manager") as mock_mgr:
            # Set up mock for start_session
            start_mock = MagicMock()
            start_mock.start_session.return_value = mock_summary
            start_mock.check_alignment.return_value = MagicMock(
                coherence=0.8, should_proceed=True, issues=[]
            )
            start_mock.end_session.return_value = mock_summary

            # Import and patch
            import cohezion.mcp.compound_server as server_module

            original_session_manager = server_module.session_manager
            server_module.session_manager = start_mock

            try:
                # Start session
                start_result = await compound_start_session(max_cache_entries=128)
                assert start_result["status"] == "success"

                # Check alignment
                align_result = await compound_check_alignment(
                    request="Test workflow", threshold=0.5
                )
                assert align_result["status"] == "success"

                # End session
                end_result = await compound_end_session(save_cache=True)
                assert end_result["status"] == "success"
            finally:
                server_module.session_manager = original_session_manager

    @pytest.mark.fast
    async def test_adversarial_review_workflow(self):
        """[P0] Ralph Lopps → Multiperspective review chain."""
        from cohezion.mcp.compound_server import multiperspective_review, ralph_lopps_review

        code_sample = """
def process_items(items):
    for item in items:
        result = expensive_operation(item)
    return results
"""

        # Run Ralph Lopps
        ralph_result = await ralph_lopps_review(code=code_sample)
        assert ralph_result["status"] == "success"

        # Run multiperspective
        proposal = json.dumps({"workflow": {"steps": ["init", "process", "save"]}})

        multi_result = await multiperspective_review(proposal=proposal)
        assert multi_result["status"] == "success"
        assert "review" in multi_result


@pytest.mark.e2e
@pytest.mark.compound
class TestMCPCompoundE2E:
    """End-to-end tests simulating user workflows."""

    @pytest.mark.slow
    async def test_token_optimization_workflow(self):
        """[P1] User optimizes token usage via MCP tools."""
        from cohezion.mcp.compound_server import cache_get_metrics, cache_optimize, learning_capture

        # Check current metrics
        metrics = await cache_get_metrics()
        assert metrics["status"] == "success"

        # Run optimization
        optimization = await cache_optimize()
        assert optimization["status"] == "success"

        # Capture learnings
        execution = json.dumps(
            {
                "request": "Optimize token usage",
                "tokens_used": 5000,
                "cache_hits": 5,
                "success": True,
                "lessons": ["Use semantic cache for similar requests"],
            }
        )

        capture = await learning_capture(execution)
        assert capture["status"] in ["success", "warning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
