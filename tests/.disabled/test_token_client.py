"""Tests for the TokenEfficientClient middleware (cohezion.swarm.token_client)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.swarm.token_client import TokenEfficientClient, TokenMetrics


# ---------------------------------------------------------------------------
# TokenMetrics
# ---------------------------------------------------------------------------


class TestTokenMetrics:
    def test_defaults(self):
        m = TokenMetrics()
        assert m.cache_hits == 0
        assert m.cache_misses == 0
        assert m.tokens_saved == 0
        assert m.total_calls == 0
        assert m.model_usage == {}

    def test_cache_hit_rate_zero_calls(self):
        m = TokenMetrics()
        assert m.cache_hit_rate == 0.0

    def test_cache_hit_rate_computed(self):
        m = TokenMetrics(cache_hits=3, cache_misses=7)
        assert m.cache_hit_rate == pytest.approx(0.3)

    def test_to_dict(self):
        m = TokenMetrics(cache_hits=1, cache_misses=2, tokens_saved=50, total_calls=3)
        d = m.to_dict()
        assert d["cache_hits"] == 1
        assert d["cache_misses"] == 2
        assert d["cache_hit_rate"] == pytest.approx(0.3333, abs=1e-3)
        assert d["tokens_saved"] == 50
        assert d["total_calls"] == 3
        assert "model_usage" in d


# ---------------------------------------------------------------------------
# TokenEfficientClient
# ---------------------------------------------------------------------------


class TestTokenEfficientClientCaching:
    @pytest.mark.asyncio
    async def test_cache_miss_calls_ollama(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="hello world")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama)
        result = await client.generate("test prompt")

        assert result == "hello world"
        mock_ollama.generate.assert_awaited_once()
        assert client.metrics.cache_misses == 1
        assert client.metrics.cache_hits == 0
        assert client.metrics.total_calls == 1

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="cached response")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama)

        # First call: cache miss
        await client.generate("same prompt", system="sys")
        # Second call: cache hit
        result = await client.generate("same prompt", system="sys")

        assert result == "cached response"
        # Ollama should only be called once
        assert mock_ollama.generate.await_count == 1
        assert client.metrics.cache_hits == 1
        assert client.metrics.cache_misses == 1

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="response")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama)

        await client.generate("prompt", use_cache=False)
        await client.generate("prompt", use_cache=False)

        # Both calls go to Ollama
        assert mock_ollama.generate.await_count == 2

    @pytest.mark.asyncio
    async def test_cache_eviction_at_max_size(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="resp")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama, cache_max_size=2)

        await client.generate("prompt_a")
        await client.generate("prompt_b")
        await client.generate("prompt_c")  # should evict prompt_a

        assert len(client._cache) == 2
        # prompt_a should be evicted, prompt_b and prompt_c remain
        key_a = client._cache_key("prompt_a", None, None)
        assert key_a not in client._cache

    @pytest.mark.asyncio
    async def test_tokens_saved_counted_on_hit(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="three word response")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama)
        await client.generate("p")
        await client.generate("p")  # cache hit

        assert client.metrics.tokens_saved == 3  # "three word response" = 3 words


class TestTokenEfficientClientHarnessing:
    @pytest.mark.asyncio
    async def test_context_harness_prunes_prompt(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="ok")
        mock_ollama.model = "phi3:mini"

        mock_harness = MagicMock()
        mock_harness.harness_prompt.return_value = {
            "prompt": "pruned",
            "system": "harnessed_system",
        }

        client = TokenEfficientClient(ollama_client=mock_ollama, context_harness=mock_harness)
        await client.generate("very long prompt " * 1000, system="original system")

        # Verify harness was called
        mock_harness.harness_prompt.assert_called_once()
        # Verify Ollama received the pruned prompt
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs.kwargs["prompt"] == "pruned"
        assert call_kwargs.kwargs["system"] == "harnessed_system"

    @pytest.mark.asyncio
    async def test_harness_failure_falls_back_to_raw(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="ok")
        mock_ollama.model = "phi3:mini"

        mock_harness = MagicMock()
        mock_harness.harness_prompt.side_effect = RuntimeError("harness broken")

        client = TokenEfficientClient(ollama_client=mock_ollama, context_harness=mock_harness)
        result = await client.generate("raw prompt", system="raw system")

        assert result == "ok"
        # Ollama should have received the raw prompt
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs.kwargs["prompt"] == "raw prompt"
        assert call_kwargs.kwargs["system"] == "raw system"


class TestTokenEfficientClientRouting:
    @pytest.mark.asyncio
    async def test_model_routing_selects_model(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="routed response")
        mock_ollama.model = "phi3:mini"

        mock_config = MagicMock()
        mock_config.name = "qwen3:8b"

        mock_router = AsyncMock()
        mock_router.select_optimal_model = AsyncMock(return_value=mock_config)

        client = TokenEfficientClient(ollama_client=mock_ollama, model_router=mock_router)
        result = await client.generate("code this", task_type="coding")

        assert result == "routed response"
        mock_router.select_optimal_model.assert_awaited_once()
        # Ollama should have been called with the routed model
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs.kwargs["model"] == "qwen3:8b"

    @pytest.mark.asyncio
    async def test_explicit_model_overrides_router(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="ok")
        mock_ollama.model = "phi3:mini"

        mock_router = AsyncMock()

        client = TokenEfficientClient(ollama_client=mock_ollama, model_router=mock_router)
        await client.generate("prompt", model="explicit_model")

        # Router should NOT be called when model is explicit
        mock_router.select_optimal_model.assert_not_awaited()
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs.kwargs["model"] == "explicit_model"

    @pytest.mark.asyncio
    async def test_router_failure_uses_default(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="ok")
        mock_ollama.model = "phi3:mini"

        mock_router = AsyncMock()
        mock_router.select_optimal_model = AsyncMock(side_effect=RuntimeError("router broken"))

        client = TokenEfficientClient(ollama_client=mock_ollama, model_router=mock_router)
        result = await client.generate("prompt")

        assert result == "ok"
        # model should be None (default) when router fails
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs.kwargs["model"] is None


class TestTokenEfficientClientMetrics:
    @pytest.mark.asyncio
    async def test_model_usage_tracked(self):
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="resp")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(ollama_client=mock_ollama)
        await client.generate("a", model="modelA")
        await client.generate("b", model="modelA")
        await client.generate("c", model="modelB")

        assert client.metrics.model_usage["modelA"] == 2
        assert client.metrics.model_usage["modelB"] == 1

    def test_get_metrics_returns_dict(self):
        client = TokenEfficientClient(ollama_client=MagicMock())
        m = client.get_metrics()
        assert isinstance(m, dict)
        for key in (
            "cache_hits",
            "cache_misses",
            "cache_hit_rate",
            "tokens_saved",
            "total_calls",
        ):
            assert key in m


class TestTokenEfficientClientGracefulDegradation:
    @pytest.mark.asyncio
    async def test_no_dependencies(self):
        """Client works with only an Ollama client and no harness/router."""
        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="basic")
        mock_ollama.model = "phi3:mini"

        client = TokenEfficientClient(
            ollama_client=mock_ollama,
            context_harness=None,
            model_router=None,
        )
        result = await client.generate("prompt")
        assert result == "basic"

    def test_clear_cache(self):
        client = TokenEfficientClient(ollama_client=MagicMock())
        client._cache["key"] = "value"
        client.clear_cache()
        assert len(client._cache) == 0

    @pytest.mark.asyncio
    async def test_close_delegates_to_ollama(self):
        mock_ollama = AsyncMock()
        mock_ollama.close = AsyncMock()

        client = TokenEfficientClient(ollama_client=mock_ollama)
        await client.close()
        mock_ollama.close.assert_awaited_once()


class TestDemocraticDebateIntegration:
    @pytest.mark.asyncio
    async def test_debate_uses_token_client(self):
        """DemocraticDebate routes through TokenEfficientClient when provided."""
        from cohezion.swarm.democratic_debate import (
            AGENT_PERSONAS,
            AgentRole,
            DemocraticDebate,
        )

        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="I AGREE. This is good.")
        mock_ollama.model = "phi3:mini"

        token_client = TokenEfficientClient(ollama_client=mock_ollama)
        debate = DemocraticDebate(token_client=token_client)

        persona = AGENT_PERSONAS[AgentRole.ARCHITECT]
        result = await debate._call_agent(persona, "test prompt")

        assert "AGREE" in result
        mock_ollama.generate.assert_awaited_once()
        assert token_client.metrics.total_calls == 1
        await debate.close()

    @pytest.mark.asyncio
    async def test_debate_without_token_client_still_works(self):
        """DemocraticDebate falls back to direct httpx when no token_client."""
        from cohezion.swarm.democratic_debate import (
            AGENT_PERSONAS,
            AgentRole,
            DemocraticDebate,
        )

        debate = DemocraticDebate(ollama_host="http://nonexistent:99999")
        assert debate._token_client is None

        persona = AGENT_PERSONAS[AgentRole.ARCHITECT]
        result = await debate._call_agent(persona, "test prompt")
        # Should return an error string, not raise
        assert "error" in result.lower() or "unavailable" in result.lower()
        await debate.close()
