"""Tests for Gemma4Provider — Google Gemma 4 model provider implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.providers.model_provider import (
    GenerationResult,
    get_model_provider,
    list_providers,
)


class TestGemma4ProviderRegistration:
    """Test that Gemma4Provider auto-registers in the provider registry."""

    def test_gemma4_registered(self):
        # Import triggers auto-registration
        import cohezion.swarm.providers.gemma4_provider  # noqa: F401

        assert "gemma4" in list_providers()

    def test_get_gemma4_provider(self):
        import cohezion.swarm.providers.gemma4_provider  # noqa: F401

        provider = get_model_provider("gemma4", use_singleton=False)
        assert provider is not None


class TestGemma4ProviderConfig:
    """Test Gemma4Provider configuration handling."""

    def test_default_config(self):
        from cohezion.swarm.providers.gemma4_provider import Gemma4Provider

        provider = Gemma4Provider()
        assert provider.timeout == 120  # Gemma 4 reasoning needs more time
        assert "localhost:11434" in provider.base_url
        assert provider.thinking_mode is True

    def test_custom_config(self):
        from cohezion.swarm.providers.gemma4_provider import Gemma4Provider

        provider = Gemma4Provider(
            config={
                "base_url": "http://other-host:11434",
                "thinking_mode": False,
                "timeout": 60,
                "context_window": 128000,
            }
        )
        assert provider.base_url == "http://other-host:11434"
        assert provider.thinking_mode is False
        assert provider.timeout == 60
        assert provider.context_window == 128000


class TestGemma4ProviderGenerate:
    """Test generation with mocked Ollama API responses."""

    @pytest.mark.asyncio
    async def test_generate_thinking_mode(self):
        from cohezion.swarm.providers.gemma4_provider import Gemma4Provider

        provider = Gemma4Provider()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "response": "Final answer after thinking.",
                "eval_count": 50,
                "prompt_eval_count": 20,
                "total_duration": 1000000000,
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        provider._session = mock_session

        result = await provider.generate(
            model="gemma4:31b",
            prompt="Solve this complex problem",
            max_tokens=500,
        )

        assert isinstance(result, GenerationResult)
        assert result.response == "Final answer after thinking."
        assert result.provider == "gemma4"
        assert result.model == "gemma4:31b"

        # Verify thinking mode was sent in payload
        args, kwargs = mock_session.post.call_args
        payload = kwargs["json"]
        assert payload["options"]["thinking"] is True
        assert payload["options"]["num_ctx"] == 256000

        await provider.close()

    @pytest.mark.asyncio
    async def test_generate_structured_output(self):
        from cohezion.swarm.providers.gemma4_provider import Gemma4Provider

        provider = Gemma4Provider()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "response": '{"result": "success"}',
                "eval_count": 10,
                "prompt_eval_count": 5,
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        provider._session = mock_session

        result = await provider.generate(
            model="gemma4:26b",
            prompt="Return JSON",
            format="json",
        )

        assert result.response == '{"result": "success"}'

        # Verify format was sent in payload
        args, kwargs = mock_session.post.call_args
        payload = kwargs["json"]
        assert payload["format"] == "json"

        await provider.close()
