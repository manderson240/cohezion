"""Tests for ngrok AI Gateway adapter.

Tests cover:
- Basic request routing to ngrok gateway
- Automatic failover to Ollama
- Response caching (4th tier)
- Cost calculation and tracking
- Feature flag integration
- Error handling and retries
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from cohezion.deployment.feature_flags import (
    FeatureFlag,
    FeatureFlagContext,
    get_feature_flag_manager,
)
from cohezion.gateway import NgrokAIGateway


class TestNgrokAIGateway:
    """Test suite for NgrokAIGateway."""

    @pytest.fixture
    def gateway(self):
        """Create gateway instance for testing."""
        return NgrokAIGateway(
            ngrok_endpoint="https://test.ngrok.app/v1",
            ngrok_api_key="test-key",
            fallback_ollama_url="http://localhost:11434",
            enable_failover=True,
        )

    @pytest.fixture
    def flag_manager(self):
        """Get feature flag manager."""
        return get_feature_flag_manager()

    def test_gateway_initialization(self):
        """Test gateway initialization with different configurations."""
        # With ngrok endpoint
        gateway = NgrokAIGateway(
            ngrok_endpoint="https://test.ngrok.app/v1",
            ngrok_api_key="test-key",
        )
        assert gateway.ngrok_endpoint == "https://test.ngrok.app/v1"
        assert gateway.ngrok_api_key == "test-key"
        assert gateway.enable_failover is True

        # Without ngrok endpoint (fallback only)
        gateway_fallback = NgrokAIGateway(
            ngrok_endpoint=None,
            enable_failover=True,
        )
        assert gateway_fallback.ngrok_endpoint == ""
        assert gateway_fallback.enable_failover is True

    def test_cache_key_generation(self, gateway):
        """Test cache key generation is deterministic."""
        prompt = "test prompt"
        system = "test system"
        model = "gpt-4"

        key1 = gateway._cache_key(prompt, system, model)
        key2 = gateway._cache_key(prompt, system, model)

        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex

    def test_cache_key_different_inputs(self, gateway):
        """Test different inputs produce different cache keys."""
        key1 = gateway._cache_key("prompt1", "system", "model")
        key2 = gateway._cache_key("prompt2", "system", "model")
        key3 = gateway._cache_key("prompt1", "system2", "model")
        key4 = gateway._cache_key("prompt1", "system", "model2")

        assert key1 != key2
        assert key1 != key3
        assert key1 != key4

    def test_cost_calculation(self, gateway):
        """Test cost calculation for different models."""
        # GPT-4O: $5/1M input, $15/1M output
        cost = gateway._calculate_cost("gpt-4o", 1000, 1000)
        assert abs(cost - (5.0 / 1000 + 15.0 / 1000)) < 1e-6

        # Claude 3.5 Sonnet: $3/1M input, $15/1M output
        cost = gateway._calculate_cost("claude-3.5-sonnet", 1000, 1000)
        assert abs(cost - (3.0 / 1000 + 15.0 / 1000)) < 1e-6

        # Ollama: free
        cost = gateway._calculate_cost("ollama-default", 1000, 1000)
        assert cost == 0.0

    def test_response_cache(self, gateway):
        """Test response caching (4th tier)."""
        prompt = "test prompt"
        system = "test system"
        model = "gpt-4"
        response_text = "test response"
        tokens = 100

        # Initially no cache entry
        cache_key = gateway._cache_key(prompt, system, model)
        assert cache_key not in gateway._response_cache

        # Add to cache
        gateway._response_cache[cache_key] = (response_text, tokens)

        # Verify cache hit
        assert cache_key in gateway._response_cache
        cached_response, cached_tokens = gateway._response_cache[cache_key]
        assert cached_response == response_text
        assert cached_tokens == tokens

    def test_clear_cache(self, gateway):
        """Test cache clearing."""
        prompt = "test prompt"
        system = "test system"
        model = "gpt-4"

        cache_key = gateway._cache_key(prompt, system, model)
        gateway._response_cache[cache_key] = ("response", 100)

        assert cache_key in gateway._response_cache
        gateway.clear_cache()
        assert cache_key not in gateway._response_cache

    def test_metrics_initialization(self, gateway):
        """Test metrics initialization."""
        metrics = gateway.get_metrics()

        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["fallback_requests"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["total_tokens"] == 0
        assert metrics["total_cost"] == 0.0

    def test_metrics_tracking(self, gateway):
        """Test metrics are properly tracked."""
        gateway.metrics.total_requests = 10
        gateway.metrics.successful_requests = 8
        gateway.metrics.failed_requests = 2
        gateway.metrics.fallback_requests = 1
        gateway.metrics.cache_hits = 3
        gateway.metrics.total_tokens = 500
        gateway.metrics.total_cost = 0.005

        metrics = gateway.get_metrics()

        assert metrics["total_requests"] == 10
        assert metrics["successful_requests"] == 8
        assert metrics["failed_requests"] == 2
        assert metrics["fallback_requests"] == 1
        assert metrics["cache_hits"] == 3
        assert metrics["total_tokens"] == 500
        assert metrics["total_cost"] == 0.005

    def test_success_rate_calculation(self, gateway):
        """Test success rate calculation."""
        gateway.metrics.total_requests = 100
        gateway.metrics.successful_requests = 95
        gateway.metrics.failed_requests = 5

        metrics = gateway.get_metrics()

        assert metrics["success_rate"] == 95.0

    def test_cost_per_request_calculation(self, gateway):
        """Test average cost per request calculation."""
        gateway.metrics.total_requests = 10
        gateway.metrics.total_cost = 0.10  # $0.10 total

        metrics = gateway.get_metrics()

        assert abs(metrics["average_cost_per_request"] - 0.01) < 1e-6

    def test_reset_metrics(self, gateway):
        """Test metrics reset."""
        gateway.metrics.total_requests = 10
        gateway.metrics.total_tokens = 500

        gateway.reset_metrics()

        metrics = gateway.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_generate_cache_hit(self, gateway, flag_manager):
        """Test generate with cache hit."""
        # Enable ngrok feature flag
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)

        prompt = "test prompt"
        system = "test system"
        model = "gpt-4"
        expected_response = "cached response"
        expected_tokens = 50

        # Pre-populate cache
        cache_key = gateway._cache_key(prompt, system, model)
        gateway._response_cache[cache_key] = (expected_response, expected_tokens)

        # Call generate - should hit cache without making actual request
        response, tokens = await gateway.generate(prompt, model, system)

        assert response == expected_response
        assert tokens == expected_tokens
        assert gateway.metrics.cache_hits == 1

    @pytest.mark.asyncio
    async def test_generate_with_ngrok_disabled(self, gateway):
        """Test generate falls back to Ollama when ngrok is disabled."""
        # Ensure ngrok feature flag is disabled
        flag_manager = get_feature_flag_manager()
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, False)

        with patch("cohezion.gateway.ngrok_adapter.requests.post") as mock_ollama:
            # Mock Ollama /api/chat response
            mock_ollama.return_value.json.return_value = {
                "message": {"content": "ollama response"},
                "eval_count": 75,
                "prompt_eval_count": 0,
            }

            response, tokens = await gateway.generate(
                prompt="test",
                model="qwen3-coder:30b",
            )

            assert response == "ollama response"
            assert tokens == 75
            assert gateway.metrics.ollama_requests == 1

    @pytest.mark.asyncio
    async def test_generate_ngrok_then_fallback(self, gateway, flag_manager):
        """Test failover from ngrok to Ollama when ngrok fails."""
        # Enable ngrok feature flag
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)

        with patch("cohezion.gateway.ngrok_adapter.requests.post") as mock_post:
            # ngrok fails, then Ollama succeeds
            def side_effect(*args, **kwargs):
                if "v1/chat/completions" in args[0]:
                    raise Exception("ngrok failure")
                # This is Ollama call
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "message": {"content": "ollama fallback"},
                    "eval_count": 50,
                    "prompt_eval_count": 0,
                }
                return mock_response

            mock_post.side_effect = side_effect

            response, tokens = await gateway.generate(
                prompt="test",
                model="qwen3-coder:30b",
            )

            assert response == "ollama fallback"
            assert tokens == 50
            assert gateway.metrics.fallback_requests == 1

    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self, gateway, flag_manager):
        """Test error when all providers fail."""
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)

        with patch("cohezion.gateway.ngrok_adapter.requests.post") as mock_post:
            # All requests fail
            mock_post.side_effect = Exception("All providers failed")

            with pytest.raises(RuntimeError, match="All providers failed"):
                await gateway.generate(
                    prompt="test",
                    model="gpt-4",
                )

    def test_cost_tracking_integration(self, gateway, flag_manager):
        """Test cost tracking across requests."""
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)

        # Simulate cost tracking
        gateway.metrics.total_cost = 0.0

        # Add some costs
        costs = [
            gateway._calculate_cost("gpt-4o", 1000, 100),  # ~0.0005
            gateway._calculate_cost("claude-3.5-sonnet", 1000, 100),  # ~0.0003
            gateway._calculate_cost("ollama-default", 1000, 100),  # 0.0
        ]

        total_cost = sum(costs)
        gateway.metrics.total_cost = total_cost

        metrics = gateway.get_metrics()
        assert metrics["total_cost"] == pytest.approx(total_cost, rel=1e-4)

    def test_env_var_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "NGROK_ENDPOINT": "https://env.ngrok.app/v1",
                "NGROK_API_KEY": "env-key",
            },
        ):
            gateway = NgrokAIGateway()
            assert gateway.ngrok_endpoint == "https://env.ngrok.app/v1"
            assert gateway.ngrok_api_key == "env-key"

    def test_feature_flag_context(self, gateway):
        """Test feature flag context for gateway decisions."""
        context = FeatureFlagContext(
            user_id="user123",
            tenant_id="tenant456",
            region="us",
            session_id="sess789",
        )

        # Create a new gateway with context
        gateway._flag_context = context

        assert gateway._flag_context.user_id == "user123"
        assert gateway._flag_context.tenant_id == "tenant456"
        assert gateway._flag_context.region == "us"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, gateway, flag_manager):
        """Test generate includes system prompt in ngrok request."""
        flag_manager.set_flag(FeatureFlag.NGROK_AI_GATEWAY, True)

        prompt = "user prompt"
        system = "system prompt"
        model = "gpt-4"

        # Pre-populate cache to verify system prompt is part of cache key
        cache_key = gateway._cache_key(prompt, system, model)
        gateway._response_cache[cache_key] = ("response", 50)

        response, tokens = await gateway.generate(prompt, model, system)

        assert response == "response"
        assert tokens == 50


class TestTokenEfficientClientWithNgrok:
    """Test TokenEfficientClient integration with ngrok gateway."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        from cohezion.core.config import CohezionConfig

        return CohezionConfig()

    def test_token_client_with_ngrok_endpoint(self, config):
        """Test TokenEfficientClient initialization with ngrok."""
        from cohezion.swarm.token_client import TokenEfficientClient

        client = TokenEfficientClient(
            ngrok_endpoint="https://test.ngrok.app/v1",
            ngrok_api_key="test-key",
            config=config,
        )

        # Should have NgrokAIGateway as ollama
        assert isinstance(client.ollama, NgrokAIGateway)

    def test_token_client_without_ngrok_endpoint(self, config):
        """Test TokenEfficientClient defaults to Ollama."""
        from cohezion.swarm.token_client import (
            ResilientOllamaClient,
            TokenEfficientClient,
        )

        client = TokenEfficientClient(config=config)

        # Should have ResilientOllamaClient as ollama
        assert isinstance(client.ollama, ResilientOllamaClient)

    @pytest.mark.asyncio
    async def test_token_client_batch_with_ngrok(self, config):
        """Test batch generation with ngrok gateway."""
        from cohezion.swarm.batch_processor import BatchItem
        from cohezion.swarm.token_client import TokenEfficientClient

        with patch("cohezion.gateway.ngrok_adapter.requests.post") as mock_post:
            # Mock ngrok response
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "response"}}],
                "usage": {"completion_tokens": 50, "prompt_tokens": 10},
            }

            client = TokenEfficientClient(
                ngrok_endpoint="https://test.ngrok.app/v1",
                config=config,
            )

            # Create batch items
            items = [
                BatchItem(id="1", prompt="task1", system="", model="gpt-4"),
                BatchItem(id="2", prompt="task2", system="", model="gpt-4"),
            ]

            result = await client.batch_generate(items)

            assert len(result.items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
