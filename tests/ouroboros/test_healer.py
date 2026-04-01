from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.ouroboros.healer import HealerAgent


@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.ollama_base_url = "http://localhost:11434"
    mock.priority = 1
    mock.strict_security = False
    return mock

@pytest.mark.asyncio
async def test_healer_agent_initialization(mock_config):
    """Test that HealerAgent initializes with correct role."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                agent = HealerAgent(model_name="test-model", config=mock_config)
                assert agent.model_name == "test-model"
                assert "healer" in agent.__class__.__name__.lower()

@pytest.mark.asyncio
async def test_healer_synthesize_patch_success(mock_config):
    """Test that the agent generates a structured patch proposal."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                agent = HealerAgent(model_name="test-model", config=mock_config)
                
                # Mock the LLM call
                mock_response = "PATCH Proposal: Adjust manifold stiffness to 0.15."
                agent._call_ollama = AsyncMock(return_value=mock_response)
                
                anomaly_report = {
                    "is_degraded": True,
                    "anomaly_count": 5,
                    "total_count": 10
                }
                
                patch_proposal = await agent.synthesize_patch(anomaly_report)
                
                assert "PATCH" in patch_proposal
                agent._call_ollama.assert_called_once()
                # Verify prompt contains anomaly details
                prompt = agent._call_ollama.call_args[0][0]
                assert "anomaly_count\": 5" in prompt
