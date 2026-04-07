"""Tests for EcoResilience Agent Data Grounding.

Verifies that the agent correctly incorporates real-world data from the EnvDataMCP.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from cohezion.agents.ecoresilience_agent import EcoResilienceAgent
from cohezion.mcp.env_data_mcp import fetch_noaa_data, fetch_copernicus_data

class TestEcoResilienceGrounding:
    @pytest.mark.asyncio
    @patch("cohezion.agents.ecoresilience_agent.get_model_provider")
    async def test_data_grounded_analysis(self, mock_get_provider):
        # 1. Setup mock provider
        mock_provider = AsyncMock()
        mock_result = AsyncMock()
        mock_result.response = "Analysis with grounding complete."
        mock_provider.generate.return_value = mock_result
        mock_get_provider.return_value = mock_provider

        # 2. Get mock data from MCP tools
        noaa_raw = await fetch_noaa_data("GHCND:TEST")
        copernicus_raw = await fetch_copernicus_data("Test_Region")
        
        env_data = {
            "noaa": json.loads(noaa_raw),
            "copernicus": json.loads(copernicus_raw)
        }

        # 3. Initialize and run agent
        agent = EcoResilienceAgent(model_name="gemma4")
        
        with patch.object(agent, 'act', new_callable=AsyncMock) as mock_act:
            result = await agent.analyze_ecosystem(
                scenario="Local drought impact",
                trajectory_id="traj-grounding",
                env_data=env_data
            )
            
            assert result == "Analysis with grounding complete."
            
            # 4. Verify grounding data reached the provider prompt
            call_kwargs = mock_provider.generate.call_args.kwargs
            prompt = call_kwargs["prompt"]
            
            assert "REAL-WORLD GROUNDING DATA" in prompt
            assert "GHCND:TEST" in prompt
            assert "Test_Region" in prompt
            assert "NDVI" in prompt
