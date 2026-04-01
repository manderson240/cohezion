from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import torch

from cohezion.agents.evo_agent import EVOAgent


@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.ollama_base_url = "http://localhost:11434"
    mock.priority = 1
    mock.strict_security = False
    mock.cache_ttl_seconds = 3600
    mock.mrp_sync = False
    mock.max_refinement_rounds = 1
    mock.min_phi_threshold = 0.8
    mock.semantic_cache_threshold = 0.9
    return mock

@pytest.mark.asyncio
async def test_evo_agent_full_cycle_integration(mock_config):
    """Test the complete flow from act() to reward and potential ratchet."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                agent = EVOAgent(model_name="test-model", config=mock_config)
                
                # Mock reward/ratchet to track calls
                agent._reward_calculator = MagicMock()
                agent._reward_calculator.calculate_score.return_value = 0.95
                agent._ratchet = AsyncMock()
                
                # Mock VAE and Engine
                agent._flume_vae = MagicMock()
                agent._flume_vae.encode.return_value = (torch.randn(1, 256), torch.randn(1, 256))
                agent._flume_vae.reparameterize.return_value = torch.randn(256)
                agent._triune_engine = AsyncMock()
                
                # Execute action
                await agent.act(prompt="high performance mission", trajectory_id="cycle_1")
                
                # Verify reward was calculated
                agent._reward_calculator.calculate_score.assert_called_once()
                
                # Verify ratchet was evaluated
                agent._ratchet.evaluate_and_ratchet.assert_called_once()
                args, kwargs = agent._ratchet.evaluate_and_ratchet.call_args
                assert kwargs["score"] == 0.95
                assert kwargs["trajectory_id"] == "cycle_1"
