from unittest.mock import AsyncMock, patch

import pytest

from cohezion.swarm.autoresearch_executor import AutoresearchExecutor


class TestAutoresearchExecutor:
    """Tests for autoresearch_executor."""

    @pytest.fixture
    def mock_compound_client(self):
        with patch("cohezion.swarm.autoresearch_executor.get_compound_client") as mock:
            client_instance = AsyncMock()
            mock.return_value = client_instance
            yield client_instance

    @pytest.fixture
    def executor(self):
        return AutoresearchExecutor(min_speed_tokens_sec=1.0, max_duration_seconds=5)

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_evaluate_hypothesis_returns_metrics(self, mock_compound_client, executor):
        """Test _evaluate_hypothesis returns expected metrics including coherence."""
        mock_compound_client.generate.return_value = (
            "I give this a coherence score of 0.85.",
            None,
        )
        mock_mgr = AsyncMock()

        result = await executor._evaluate_hypothesis("Test Hypothesis", mock_mgr)

        assert result["hypothesis"] == "Test Hypothesis"
        assert result["coherence"] == 0.85
        assert "response" in result
        assert "tokens_per_sec" in result
        assert "duration" in result
        mock_compound_client.generate.assert_called_once()

    @pytest.mark.fast
    @pytest.mark.asyncio
    @patch("cohezion.swarm.autoresearch_executor.RZeroEvolver")
    @patch("cohezion.compound.session_manager.CompoundSessionManager")
    async def test_execute_run_triggers_r_zero_on_high_coherence(
        self, mock_mgr, mock_rzero, mock_compound_client, executor
    ):
        """Test that high coherence triggers RZeroEvolver."""
        mock_compound_client.generate.return_value = ("coherence score 0.9", None)
        mock_evolver_instance = AsyncMock()
        mock_rzero.return_value = mock_evolver_instance

        await executor.execute_run()

        mock_evolver_instance.run_loop.assert_called()
