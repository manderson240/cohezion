"""Tests for GeminiProvider — Google Gemini model provider implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.providers.model_provider import (
    GenerationResult,
    get_model_provider,
    list_providers,
)


class TestGeminiProviderRegistration:
    """Test that GeminiProvider auto-registers in the provider registry."""

    def test_gemini_registered(self):
        # Import triggers auto-registration
        import cohezion.swarm.providers.gemini_provider  # noqa: F401

        assert "gemini" in list_providers()

    def test_get_gemini_provider(self):
        import cohezion.swarm.providers.gemini_provider  # noqa: F401

        provider = get_model_provider("gemini", config={"api_key": "test-key"}, use_singleton=False)
        assert provider is not None
        assert provider.api_key == "test-key"


class TestGeminiProviderConfig:
    """Test GeminiProvider configuration handling."""

    def test_default_config(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert provider.timeout == 30
        assert "generativelanguage.googleapis.com" in provider.base_url

    def test_custom_config(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(
            config={
                "api_key": "custom-key",
                "timeout": 60,
            }
        )
        assert provider.api_key == "custom-key"
        assert provider.timeout == 60

    def test_env_var_fallback(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}):
            provider = GeminiProvider()
            assert provider.api_key == "env-key"


class TestGeminiProviderCostTiers:
    """Test cost tier configuration matches CLAUDE.md 70/20/10 split."""

    def test_cost_tiers_defined(self):
        from cohezion.swarm.providers.gemini_provider import GEMINI_COST_PER_M_TOKENS

        assert GEMINI_COST_PER_M_TOKENS["gemini-2.0-flash-lite"] == 0.075
        assert GEMINI_COST_PER_M_TOKENS["gemini-2.0-flash"] == 0.30
        assert GEMINI_COST_PER_M_TOKENS["gemini-2.5-pro"] == 2.00

    def test_context_windows_defined(self):
        from cohezion.swarm.providers.gemini_provider import GEMINI_CONTEXT_WINDOWS

        assert GEMINI_CONTEXT_WINDOWS["gemini-2.5-pro"] == 2_000_000
        assert GEMINI_CONTEXT_WINDOWS["gemini-2.0-flash-lite"] == 1_000_000


class TestGeminiProviderGenerate:
    """Test generation with mocked API responses."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(config={"api_key": "test-key"})

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Hello from Gemini!"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                },
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        provider._session = mock_session

        result = await provider.generate(
            model="gemini-2.5-flash",
            prompt="Hello",
            max_tokens=100,
        )

        assert isinstance(result, GenerationResult)
        assert result.response == "Hello from Gemini!"
        assert result.provider == "gemini"
        assert result.model == "gemini-2.5-flash"
        assert result.tokens_used == 15
        assert result.confidence == 0.9
        assert result.metadata["estimated_cost_usd"] > 0

        await provider.close()

    @pytest.mark.asyncio
    async def test_generate_no_api_key_raises(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(config={"api_key": ""})

        with pytest.raises(RuntimeError, match="API key not configured"):
            await provider.generate(model="gemini-2.5-flash", prompt="test")

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(config={"api_key": "test-key"})

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.text = AsyncMock(return_value="Rate limited")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        provider._session = mock_session

        with pytest.raises(RuntimeError, match="Gemini API error 429"):
            await provider.generate(model="gemini-2.5-flash", prompt="test")

        await provider.close()


class TestGeminiProviderHealth:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_no_key(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(config={"api_key": ""})
        health = await provider.health_check()

        assert health["provider"] == "gemini"
        assert health["status"] == "degraded"
        assert health["api_configured"] is False
        assert "cost_tiers" in health

    @pytest.mark.asyncio
    async def test_list_models_no_key_returns_defaults(self):
        from cohezion.swarm.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(config={"api_key": ""})
        models = await provider.list_models()

        assert len(models) > 0
        assert "gemini-2.5-pro" in models
        assert "gemini-2.0-flash-lite" in models
