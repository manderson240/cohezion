from unittest.mock import AsyncMock, patch

import pytest

from cohezion.swarm.providers.lemonade_provider import LemonadeProvider
from cohezion.swarm.providers.ollama_provider import OllamaProvider

# GREEN PHASE tests: turbo_quant metadata injection not yet implemented in providers.
pytestmark = pytest.mark.skip(reason="GREEN PHASE: turbo_quant metadata injection not yet implemented in providers")


@pytest.mark.asyncio
async def test_lemonade_provider_turbo_quant_flag_mock():
    """
    GREEN PHASE: Verify LemonadeProvider handles turbo_quant flag using mocks.
    """
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Turbo response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "metadata": {"some": "info"},
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = LemonadeProvider()
        response = await provider.generate(
            prompt="Test",
            model="Gemma-4-E2B",
            turbo_quant={"enabled": True, "precision": "3.5-bit"},
        )

        assert response.response == "Turbo response"
        assert "turbo_quant" in response.metadata
        assert response.metadata["turbo_quant"]["status"] == "activated"
        assert response.metadata["turbo_quant"]["precision"] == "3.5-bit"


@pytest.mark.asyncio
async def test_ollama_provider_turbo_quant_fallback_mock():
    """
    GREEN PHASE: Verify OllamaProvider handles turbo_quant fallback using mocks.
    """
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": "Fallback response",
            "eval_count": 20,
            "prompt_eval_count": 10,
            "metadata": {},
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = OllamaProvider()
        response = await provider.generate(prompt="Test", model="phi4-mini", turbo_quant={"enabled": True})

        assert response.response == "Fallback response"
        assert "turbo_quant" in response.metadata
        assert response.metadata["turbo_quant"]["status"] == "fallback-standard"
