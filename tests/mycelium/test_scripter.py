from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.mycelium.scripter import ShadowScripter


@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.ollama_base_url = "http://localhost:11434"
    mock.priority = 1
    mock.strict_security = False
    return mock

@pytest.mark.asyncio
async def test_scripter_initialization(mock_config):
    """Test that ShadowScripter initializes correctly."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                scripter = ShadowScripter(model_name="test-model", config=mock_config)
                assert scripter is not None
                assert scripter.model_name == "test-model"

@pytest.mark.asyncio
async def test_synthesize_test_suite_prompt(mock_config):
    """Test that synthesize_test_suite generates a correct prompt."""
    with patch("cohezion.registry.capability_registry.CapabilityRegistry"):
        with patch("cohezion.swarm.journey_narrator.JourneyNarrator"):
            with patch("cohezion.swarm.redundancy_suppression.RedundancyManager"):
                scripter = ShadowScripter(model_name="test-model", config=mock_config)
                scripter._call_ollama = AsyncMock(return_value="def test_generated(): pass")
                
                code_context = "def new_feature(): return True"
                test_code = await scripter.synthesize_test_suite(file_path="src/dummy.py", code_context=code_context)
                
                assert "test_generated" in test_code
                scripter._call_ollama.assert_called_once()
                prompt = scripter._call_ollama.call_args[0][0]
                assert "src/dummy.py" in prompt
                assert "new_feature" in prompt
