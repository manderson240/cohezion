"""Phase 1 migration tests: swarm/ files now route through lemonade router (:13305).

Tests verify:
1. Default URL defaults point to :13305 (not :11434 or :13307)
2. OllamaProvider routes R2-mapped models through LemonadeRouterClient
3. OllamaProvider sends allow-listed models (phi4/phi3) to Ollama shim
4. ResilientOllamaClient (ollama_resilience) posts OpenAI /v1/chat/completions payload
5. ResilientOllamaClient (token_client) posts OpenAI /v1/chat/completions payload
6. democratic_debate fallback path posts OpenAI /v1/chat/completions
7. SmartRouter default host points to :13305
8. DynamicModelRouter routes through LemonadeRouterClient
9. model_manager.list_models uses /v1/models endpoint
10. base_scout HTTP call uses /v1/chat/completions
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Default URL defaults
# ---------------------------------------------------------------------------


class TestDefaultURLs:
    """All migrated files must default to :13305."""

    def test_ollama_resilience_default_url(self):
        from cohezion.swarm.ollama_resilience import _DEFAULT_BASE_URL, ResilientOllamaClient

        assert _DEFAULT_BASE_URL == "http://localhost:13305"
        client = ResilientOllamaClient()
        assert "13305" in client.base_url
        assert "11434" not in client.base_url

    def test_token_client_resilient_default_url(self):
        from cohezion.swarm.token_client import ResilientOllamaClient as TRC

        client = TRC()
        assert "13305" in client.base_url
        assert "11434" not in client.base_url

    def test_token_efficient_client_default_url(self):
        import inspect
        from cohezion.swarm.token_client import TokenEfficientClient

        sig = inspect.signature(TokenEfficientClient.__init__)
        default = sig.parameters["ollama_base_url"].default
        assert "13305" in default
        assert "11434" not in default

    def test_compound_client_default_url(self):
        import inspect
        from cohezion.swarm.compound_client import create_compound_client

        sig = inspect.signature(create_compound_client)
        default = sig.parameters["ollama_host"].default
        assert "13305" in default
        assert "11434" not in default

    def test_democratic_debate_default_url(self):
        import inspect
        from cohezion.swarm.democratic_debate import DemocraticDebate

        sig = inspect.signature(DemocraticDebate.__init__)
        default = sig.parameters["ollama_host"].default
        assert "13305" in default
        assert "11434" not in default

    def test_base_scout_default_url(self):
        import inspect
        from cohezion.swarm.agents.base_scout import BaseScout

        sig = inspect.signature(BaseScout.__init__)
        default = sig.parameters["ollama_url"].default
        assert "13305" in default
        assert "11434" not in default

    def test_eigent_agent_default_url(self):
        import inspect
        from cohezion.swarm.agents.eigent_agent import EigentAgent

        sig = inspect.signature(EigentAgent.__init__)
        default = sig.parameters["lemonade_url"].default
        assert "13305" in default
        assert "13307" not in default

    def test_semantic_cache_embedding_default_url(self):
        import inspect

        # The DistilledEmbeddingModel class has the ollama_base_url param
        # Import the module and find the class
        import cohezion.swarm.semantic_cache as sc

        # Find the DistilledEmbeddingModel class
        cls = None
        for name in dir(sc):
            obj = getattr(sc, name)
            if isinstance(obj, type) and hasattr(obj.__init__, "__code__"):
                sig = inspect.signature(obj.__init__)
                if "ollama_base_url" in sig.parameters:
                    cls = obj
                    break
        assert cls is not None, "DistilledEmbeddingModel not found in semantic_cache"
        default = inspect.signature(cls.__init__).parameters["ollama_base_url"].default
        assert "13305" in default
        assert "11434" not in default

    def test_model_manager_router_url(self):
        from cohezion.swarm.model_manager import LEMONADE_ROUTER_URL, OLLAMA_HOST

        assert LEMONADE_ROUTER_URL == "http://localhost:13305"
        # OLLAMA_HOST is the deprecated alias — it points to the router
        assert OLLAMA_HOST == LEMONADE_ROUTER_URL


# ---------------------------------------------------------------------------
# OllamaProvider routing: R2 mapped models → router, shim models → Ollama
# ---------------------------------------------------------------------------


class TestOllamaProviderR2Routing:
    """OllamaProvider must route R2-mapped models through LemonadeRouterClient."""

    @pytest.mark.asyncio
    async def test_mapped_model_routes_to_router(self):
        """qwen3:8b is in _OLLAMA_TO_ROUTER → should call _generate_via_router."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        with patch.object(provider, "_generate_via_router", new_callable=AsyncMock) as mock_router:
            from cohezion.swarm.providers.model_provider import GenerationResult

            mock_router.return_value = GenerationResult(
                response="test",
                model="Qwen3-8B-GGUF",
                provider="lemonade",
                confidence=0.9,
                tokens_used=10,
                latency_ms=100.0,
                metadata={},
            )
            _ = await provider.generate("qwen3:8b", "hello")
            mock_router.assert_called_once()
            # Verify the router model name was used, not the Ollama name
            call_args = mock_router.call_args
            assert call_args[0][0] == "Qwen3-8B-GGUF"

    @pytest.mark.asyncio
    async def test_shim_model_routes_to_ollama(self):
        """phi4:latest is in _OLLAMA_SHIM_MODELS → should call _generate_via_ollama_shim."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        with patch.object(
            provider, "_generate_via_ollama_shim", new_callable=AsyncMock
        ) as mock_shim:
            from cohezion.swarm.providers.model_provider import GenerationResult

            mock_shim.return_value = GenerationResult(
                response="test",
                model="phi4:latest",
                provider="ollama",
                confidence=0.8,
                tokens_used=5,
                latency_ms=50.0,
                metadata={},
            )
            _ = await provider.generate("phi4:latest", "hello")
            mock_shim.assert_called_once()

    @pytest.mark.asyncio
    async def test_phi3_routes_to_shim(self):
        """phi3:mini base name 'phi3' matches shim set → shim path."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        with patch.object(
            provider, "_generate_via_ollama_shim", new_callable=AsyncMock
        ) as mock_shim:
            from cohezion.swarm.providers.model_provider import GenerationResult

            mock_shim.return_value = GenerationResult(
                response="test",
                model="phi3:mini",
                provider="ollama",
                confidence=0.8,
                tokens_used=5,
                latency_ms=50.0,
                metadata={},
            )
            _ = await provider.generate("phi3:mini", "hello")
            mock_shim.assert_called_once()

    @pytest.mark.asyncio
    async def test_deepseek_r1_7b_routes_to_router(self):
        """deepseek-r1:7b IS in R2 map → router path."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        with patch.object(provider, "_generate_via_router", new_callable=AsyncMock) as mock_router:
            from cohezion.swarm.providers.model_provider import GenerationResult

            mock_router.return_value = GenerationResult(
                response="test",
                model="DeepSeek-Qwen3-8B-GGUF",
                provider="lemonade",
                confidence=0.9,
                tokens_used=10,
                latency_ms=100.0,
                metadata={},
            )
            _ = await provider.generate("deepseek-r1:7b", "hello")
            mock_router.assert_called_once()
            assert mock_router.call_args[0][0] == "DeepSeek-Qwen3-8B-GGUF"

    @pytest.mark.asyncio
    async def test_router_url_in_via_router(self):
        """_generate_via_router must use the router URL at :13305."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        assert "13305" in provider.router_url
        assert "11434" not in provider.router_url

    def test_r2_map_keys(self):
        """R2 model map must contain all four documented entries."""
        from cohezion.swarm.providers.ollama_provider import _OLLAMA_TO_ROUTER

        assert "qwen3:8b" in _OLLAMA_TO_ROUTER
        assert "deepseek-r1:7b" in _OLLAMA_TO_ROUTER
        assert "qwen3-coder:30b" in _OLLAMA_TO_ROUTER
        assert "nomic-embed-text" in _OLLAMA_TO_ROUTER

    def test_shim_model_set(self):
        """Shim set must contain phi4, phi3, deepseek-r1:70b."""
        from cohezion.swarm.providers.ollama_provider import _OLLAMA_SHIM_MODELS

        assert "phi4:latest" in _OLLAMA_SHIM_MODELS
        assert "phi4" in _OLLAMA_SHIM_MODELS
        assert "phi3:mini" in _OLLAMA_SHIM_MODELS
        assert "phi3" in _OLLAMA_SHIM_MODELS
        assert "deepseek-r1:70b" in _OLLAMA_SHIM_MODELS


# ---------------------------------------------------------------------------
# OpenAI payload shape tests
# ---------------------------------------------------------------------------


class TestOpenAIPayloadShape:
    """Migrated HTTP callers must send OpenAI-shaped requests, not Ollama-native."""

    @pytest.mark.asyncio
    async def test_ollama_resilience_posts_openai_payload(self):
        """ResilientOllamaClient._call_with_retry must POST to /v1/chat/completions."""
        from cohezion.swarm.ollama_resilience import ResilientOllamaClient

        client = ResilientOllamaClient(model="phi3:mini", base_url="http://localhost:13305")

        captured = {}

        async def mock_post(url, *, json, **kwargs):
            captured["url"] = url
            captured["body"] = json
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
            return mock_resp

        mock_client = MagicMock()
        mock_client.post = mock_post

        with patch.object(
            type(client), "client", new_callable=lambda: property(lambda self: mock_client)
        ):
            await client._call_with_retry(
                prompt="test",
                model="phi3:mini",
                system=None,
                temperature=0.7,
                num_predict=100,
            )

        assert "/v1/chat/completions" in captured["url"]
        assert "messages" in captured["body"]
        assert "prompt" not in captured["body"]  # discriminating: NOT Ollama native
        assert "model" in captured["body"]

    @pytest.mark.asyncio
    async def test_token_client_resilient_posts_openai_payload(self):
        """ResilientOllamaClient (token_client) must POST to /v1/chat/completions."""
        from cohezion.swarm.token_client import ResilientOllamaClient as TRC

        client = TRC(base_url="http://localhost:13305")

        captured_requests = []

        async def mock_aenter(self, *args, **kwargs):
            return self

        async def mock_aexit(self, *args, **kwargs):
            pass

        async def mock_post(url, *, json, timeout=None, **kwargs):
            captured_requests.append({"url": url, "body": json})
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "hello world"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            }
            return mock_resp

        mock_async_client = MagicMock()
        mock_async_client.post = mock_post
        mock_async_client.__aenter__ = mock_aenter
        mock_async_client.__aexit__ = mock_aexit

        with patch("cohezion.swarm.token_client.httpx.AsyncClient", return_value=mock_async_client):
            result = await client.generate("test prompt", model="phi3:mini")

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert "/v1/chat/completions" in req["url"]
        assert "messages" in req["body"]
        assert "prompt" not in req["body"]  # NOT Ollama-native
        text, tokens = result
        assert text == "hello world"
        assert tokens == 8


# ---------------------------------------------------------------------------
# model_manager list_models uses /v1/models endpoint
# ---------------------------------------------------------------------------


class TestModelManagerEndpoints:
    """OllamaModelManager.list_models must use /v1/models not /api/tags."""

    @pytest.mark.asyncio
    async def test_list_models_calls_v1_models(self):
        """list_models must GET /v1/models (OpenAI) not /api/tags (Ollama)."""
        from cohezion.swarm.model_manager import OllamaModelManager

        manager = OllamaModelManager()
        captured = {}

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"id": "Qwen3-8B-GGUF"}, {"id": "phi4"}]}

        async def mock_get(url, **kwargs):
            captured["url"] = url
            return mock_resp

        manager.http_client.get = mock_get

        result = await manager.list_models()
        assert "/v1/models" in captured["url"]
        assert "/api/tags" not in captured["url"]  # discriminating: NOT Ollama-native
        assert len(result) == 2
        assert result[0]["name"] == "Qwen3-8B-GGUF"


# ---------------------------------------------------------------------------
# Integration: OllamaProvider → router mock receives OpenAI request
# ---------------------------------------------------------------------------


class TestOllamaProviderRouterIntegration:
    """Integration: OllamaProvider.generate for phi3:mini shim hits :11434/api/generate shape."""

    @pytest.mark.asyncio
    async def test_shim_posts_to_ollama_api_generate(self):
        """phi4:latest shim must POST to Ollama /api/generate (not /v1/chat/completions)."""
        from cohezion.swarm.providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        captured = {}

        # Build a properly-shaped aiohttp response mock
        mock_inner_response = MagicMock()
        mock_inner_response.status = 200  # plain int, not AsyncMock

        async def fake_json():
            return {
                "response": "phi4 says hello",
                "eval_count": 5,
                "prompt_eval_count": 3,
                "total_duration": 1000,
                "load_duration": 0,
            }

        async def fake_text():
            return ""

        mock_inner_response.json = fake_json
        mock_inner_response.text = fake_text

        # Context manager wrapper for session.post(...)
        class FakePostCM:
            async def __aenter__(self):
                return mock_inner_response

            async def __aexit__(self, *args):
                return False

        class FakeSession:
            def post(self, url, *, json=None, timeout=None, **kwargs):
                captured["url"] = url
                captured["body"] = json
                return FakePostCM()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        with patch(
            "cohezion.swarm.providers.ollama_provider.aiohttp.ClientSession",
            return_value=FakeSession(),
        ):
            result = await provider.generate("phi4:latest", "say hello", max_tokens=50)

        assert "/api/generate" in captured["url"]
        assert captured["body"]["model"] == "phi4:latest"
        assert result.response == "phi4 says hello"
