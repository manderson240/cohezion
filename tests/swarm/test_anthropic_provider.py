"""Tests for AnthropicProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.swarm.providers.model_provider import GenerationResult


class TestAnthropicProvider:
    def test_init_without_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        with pytest.raises(ValueError, match="Anthropic API key required"):
            AnthropicProvider(config={})

    def test_init_with_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()
        assert provider._api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_generate_returns_generation_result(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello world")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate(
            model="claude-haiku-3.5-20241022",
            prompt="Say hello",
            max_tokens=100,
        )

        assert isinstance(result, GenerationResult)
        assert result.response == "Hello world"
        assert result.provider == "anthropic"
        assert result.tokens_used == 15
        assert result.model == "claude-haiku-3.5-20241022"

    @pytest.mark.asyncio
    async def test_generate_circuit_breaker_failure(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
        provider._client = mock_client

        with pytest.raises(RuntimeError, match="Anthropic generation error"):
            await provider.generate("claude-haiku-3.5-20241022", "test", max_tokens=10)

    @pytest.mark.asyncio
    async def test_list_models_returns_static_list(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()
        models = await provider.list_models()
        assert len(models) == 3
        assert "claude-sonnet-4-20250514" in models

    @pytest.mark.asyncio
    async def test_close_clears_client(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from cohezion.swarm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider()
        mock_client = AsyncMock()
        provider._client = mock_client
        await provider.close()
        assert provider._client is None
