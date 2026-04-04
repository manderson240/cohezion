"""Tests for the EcoResilience Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from cohezion.agents.ecoresilience_agent import EcoResilienceAgent


class TestEcoResilienceAgent:
    @pytest.mark.asyncio
    @patch("cohezion.agents.ecoresilience_agent.get_model_provider")
    async def test_analyze_and_simulate(self, mock_get_provider):
        # Setup mock provider
        mock_provider = AsyncMock()
        
        # We need two mock results: one for analysis, one for action extraction
        mock_analysis_result = AsyncMock()
        mock_analysis_result.response = "Synthesized TEK and Physics analysis complete. Recommending prescribed burn."
        
        mock_action_result = AsyncMock()
        mock_action_result.response = "prescribed burn"
        
        mock_provider.generate.side_effect = [mock_analysis_result, mock_action_result]
        mock_get_provider.return_value = mock_provider

        # Initialize agent with mocked graph loading
        with patch.object(EcoResilienceAgent, '_load_tek_graph', return_value={"nodes": [], "edges": []}):
            agent = EcoResilienceAgent(model_name="gemma4")
            
            # Mock the base act method since it involves ML infrastructure
            with patch.object(agent, 'act', new_callable=AsyncMock) as mock_act:
                result = await agent.analyze_and_simulate("Deforestation in the Amazon", "traj-123")
            
            assert "analysis" in result
            assert "trajectory" in result
            assert result["intervention_identified"] == "prescribed burn"
            assert len(result["trajectory"]) == 6 # initial state + 5 steps
            
            mock_act.assert_called_once()
            assert mock_provider.generate.call_count == 2
