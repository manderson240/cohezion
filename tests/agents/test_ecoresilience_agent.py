"""Tests for the EcoResilience Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.agents.ecoresilience_agent import EcoResilienceAgent


class TestEcoResilienceAgent:
    @pytest.mark.asyncio
    @patch("cohezion.agents.ecoresilience_agent.get_model_provider")
    async def test_analyze_ecosystem(self, mock_get_provider):
        # Setup mock provider
        mock_provider = AsyncMock()
        mock_result = AsyncMock()
        mock_result.response = "Synthesized TEK and Physics analysis complete."
        mock_provider.generate.return_value = mock_result
        mock_get_provider.return_value = mock_provider

        # Initialize agent
        agent = EcoResilienceAgent(model_name="gemma4")

        # Mock the base act method since it involves ML infrastructure
        with patch.object(agent, "act", new_callable=AsyncMock) as mock_act:
            result = await agent.analyze_ecosystem("Deforestation in the Amazon", "traj-123")

            assert result == "Synthesized TEK and Physics analysis complete."
            mock_act.assert_called_once()
            mock_provider.generate.assert_called_once()

            # Verify the correct prompt and model were used
            call_kwargs = mock_provider.generate.call_args.kwargs
            assert "gemma4:31b" == call_kwargs["model"]
            assert "Traditional Ecological Knowledge" in call_kwargs["prompt"]
