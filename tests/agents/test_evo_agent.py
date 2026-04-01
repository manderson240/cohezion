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
async def test_evo_agent_initialization(mock_config):
    """Test that EVOAgent initializes with all required subsystems."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                mock_surreal = MagicMock()
                mock_obsidian = MagicMock()
                agent = EVOAgent(
                    model_name="test-model", 
                    config=mock_config,
                    surreal_logger=mock_surreal,
                    obsidian_mcp=mock_obsidian
                )
                assert agent.model_name == "test-model"
                assert agent._surreal_logger == mock_surreal
                assert agent._obsidian_mcp == mock_obsidian

@pytest.mark.asyncio
async def test_evo_agent_act_cycle(mock_config):
    """Test that the act() method runs a full simulation step."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                # Mock subsystems
                mock_surreal = MagicMock()
                mock_obsidian = MagicMock()
                agent = EVOAgent(
                    model_name="test-model", 
                    config=mock_config,
                    surreal_logger=mock_surreal,
                    obsidian_mcp=mock_obsidian
                )
                
                agent._triune_engine = AsyncMock()
                agent._flume_vae = MagicMock()
                agent._ratchet = AsyncMock()
                
                # Mock VAE output
                mock_mu = torch.randn(1, 256)
                mock_logvar = torch.randn(1, 256)
                agent._flume_vae.encode.return_value = (mock_mu, mock_logvar)
                agent._flume_vae.reparameterize.return_value = mock_mu.squeeze()
                
                # Input prompt
                prompt = "test mission"
                
                # Execute action
                await agent.act(prompt, trajectory_id="traj_1")
                
                # Verify VAE was used to encode the intent
                agent._flume_vae.encode.assert_called_once()
                
                # Verify engine was stepped
                agent._triune_engine.step.assert_called_once()
                args, kwargs = agent._triune_engine.step.call_args
                assert kwargs["trajectory_id"] == "traj_1"
                assert isinstance(kwargs["environment"], torch.Tensor)
