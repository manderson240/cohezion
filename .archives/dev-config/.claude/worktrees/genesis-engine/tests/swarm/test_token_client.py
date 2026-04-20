"""Tests for token-efficient Ollama client."""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.core.config import CohezionConfig
from cohezion.swarm.batch_processor import BatchItem
from cohezion.swarm.token_client import ResilientOllamaClient, TokenEfficientClient


@pytest.fixture
def config():
    """Create test configuration."""
    return CohezionConfig()


@pytest.fixture
def token_client(config):
    """Create token-efficient client."""
    return TokenEfficientClient(config=config)


class TestResilientOllamaClient:
    """Tests for ResilientOllamaClient."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        client = ResilientOllamaClient(base_url="http://localhost:11434")

        with patch("cohezion.swarm.token_client.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "message": {"content": "Hello, world!"},
                "eval_count": 50,
                "prompt_eval_count": 0,
            }

            response, tokens = await client.generate(
                prompt="Hello",
                model="phi3:mini",
            )

            assert response == "Hello, world!"
            assert tokens == 50

    @pytest.mark.asyncio
    async def test_generate_retry_success(self):
        """Test retry on failure then success."""
        client = ResilientOllamaClient(
            base_url="http://localhost:11434",
            max_retries=3,
        )

        with patch("cohezion.swarm.token_client.requests.post") as mock_post:
            # First call fails, second succeeds
            mock_post.side_effect = [
                Exception("Connection failed"),
                MagicMock(
                    json=lambda: {
                        "message": {"content": "Success"},
                        "eval_count": 100,
                        "prompt_eval_count": 0,
                    },
                    raise_for_status=lambda: None,
                ),
            ]

            response, tokens = await client.generate(
                prompt="Test",
                model="phi3:mini",
            )

            assert response == "Success"
            assert tokens == 100

    @pytest.mark.asyncio
    async def test_generate_max_retries_exceeded(self):
        """Test failure after max retries."""
        client = ResilientOllamaClient(
            base_url="http://localhost:11434",
            max_retries=2,
        )

        with patch("cohezion.swarm.token_client.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection failed")

            with pytest.raises(RuntimeError, match="failed after 2 retries"):
                await client.generate(
                    prompt="Test",
                    model="phi3:mini",
                )


class TestTokenEfficientClient:
    """Tests for TokenEfficientClient."""

    @pytest.mark.asyncio
    async def test_generate_cache_miss(self, token_client):
        """Test generate with cache miss."""
        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("Response", 100)

            response, tokens = await token_client.generate(
                prompt="Test prompt",
                model="phi3:mini",
            )

            assert response == "Response"
            assert tokens == 100
            assert token_client._cache_misses == 1
            assert token_client._cache_hits == 0

    @pytest.mark.asyncio
    async def test_generate_cache_hit(self, token_client):
        """Test generate with cache hit."""
        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("Response", 100)

            # First call (cache miss)
            _response1, _tokens1 = await token_client.generate(
                prompt="Test prompt",
                model="phi3:mini",
            )

            # Reset mock
            mock_gen.reset_mock()

            # Second call (cache hit)
            response2, tokens2 = await token_client.generate(
                prompt="Test prompt",
                model="phi3:mini",
            )

            assert response2 == "Response"
            assert tokens2 == 100
            # Mock should not be called again (cache hit)
            mock_gen.assert_not_called()
            assert token_client._cache_hits == 1
            assert token_client._cache_misses == 1

    @pytest.mark.asyncio
    async def test_batch_generate_all_cache_hits(self, token_client):
        """Test batch generation with all cache hits."""
        # Pre-populate cache
        items = [
            BatchItem(id="1", prompt="p1", system="s", model="phi3:mini"),
            BatchItem(id="2", prompt="p2", system="s", model="phi3:mini"),
        ]

        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.side_effect = [
                ("Response1", 100),
                ("Response2", 100),
            ]

            # Prime the cache
            await token_client.generate(prompt="p1", model="phi3:mini", system="s")
            await token_client.generate(prompt="p2", model="phi3:mini", system="s")

            # Reset for batch test
            mock_gen.reset_mock()

            # Now batch should all be hits
            result = await token_client.batch_generate(items)

            assert result.cache_hits == 2
            assert result.cache_misses == 0
            assert result.cache_hit_rate == 1.0
            # No API calls should be made
            mock_gen.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_generate_mixed(self, token_client):
        """Test batch with mixed cache hits and misses."""
        # Prime cache for item 1
        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("Cached", 100)
            await token_client.generate(prompt="p1", model="phi3:mini", system="s")

        # Create batch items (1 cached, 1 not)
        items = [
            BatchItem(id="1", prompt="p1", system="s", model="phi3:mini"),
            BatchItem(id="2", prompt="p_new", system="s", model="phi3:mini"),
        ]

        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("New", 100)

            result = await token_client.batch_generate(items)

            assert result.cache_hits == 1
            assert result.cache_misses == 1
            assert result.cache_hit_rate == 0.5
            # Only one API call for the miss
            assert mock_gen.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_generate_metrics(self, token_client):
        """Test token metrics from batch generation."""
        items = [
            BatchItem(id="1", prompt="p1", system="s", model="phi3:mini"),
            BatchItem(id="2", prompt="p2", system="s", model="phi3:mini"),
        ]

        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.side_effect = [("R1", 100), ("R2", 150)]

            result = await token_client.batch_generate(items)

            # BatchResult.total_tokens reflects the batch execution
            assert result.total_tokens == 250
            # token_client metrics track all operations
            metrics = token_client.get_metrics()
            assert metrics["total_tokens"] == 250  # Both calls: 100 + 150
            assert metrics["cache_misses"] == 2
            assert metrics["api_calls"] == 2

    def test_cache_key_generation(self, token_client):
        """Test cache key generation."""
        key1 = token_client._cache_key("prompt1", "sys1", "model1")
        key2 = token_client._cache_key("prompt1", "sys1", "model1")
        key3 = token_client._cache_key("prompt2", "sys1", "model1")

        assert key1 == key2  # Same input → same key
        assert key1 != key3  # Different input → different key
        assert len(key1) == 64  # SHA256 hex string

    def test_get_metrics(self, token_client):
        """Test metrics calculation."""
        token_client._total_tokens = 1000
        token_client._cache_hits = 5
        token_client._semantic_hits = 0
        token_client._cache_misses = 5
        token_client._api_calls = 5

        metrics = token_client.get_metrics()

        assert metrics["combined_hit_rate"] == 0.5
        assert metrics["l1_hits"] == 5
        assert metrics["cache_misses"] == 5
        assert metrics["total_operations"] == 10
        assert metrics["total_tokens"] == 1000
        assert metrics["api_calls"] == 5

    def test_get_metrics_estimated_savings(self, token_client):
        """Test estimated token savings calculation (L1 only, L2 hits don't count)."""
        token_client._cache_hits = 10
        token_client._semantic_hits = 5  # L2 hits don't contribute to token savings
        # Default cache_hit_value from CacheConfig is 150
        # Only L1 hits count: 10 * 150 = 1500
        expected_savings = 10 * token_client.config.cache.cache_hit_value

        metrics = token_client.get_metrics()

        assert metrics["estimated_tokens_saved"] == expected_savings
        assert metrics["estimated_tokens_saved"] == 1500

    def test_clear_cache(self, token_client):
        """Test cache clearing."""
        # Add something to cache
        from cohezion.swarm.batch_processor import CacheEntry

        token_client.batch_processor.cache["key1"] = CacheEntry(
            key="key1",
            value="value",
            tokens_used=100,
        )

        assert len(token_client.batch_processor.cache) == 1
        token_client.clear_cache()
        assert len(token_client.batch_processor.cache) == 0

    def test_reset_metrics(self, token_client):
        """Test metrics reset."""
        token_client._total_tokens = 1000
        token_client._cache_hits = 10
        token_client._cache_misses = 5
        token_client._api_calls = 5

        token_client.reset_metrics()

        assert token_client._total_tokens == 0
        assert token_client._cache_hits == 0
        assert token_client._cache_misses == 0
        assert token_client._api_calls == 0

    @pytest.mark.asyncio
    async def test_batch_generate_concurrent_different_models(self, token_client):
        """Test batch with different models (tests routing)."""
        items = [
            BatchItem(id="1", prompt="p1", system="s", model="qwen3-coder:30b"),
            BatchItem(id="2", prompt="p2", system="s", model="phi3:mini"),
        ]

        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.side_effect = [("Result1", 200), ("Result2", 100)]

            result = await token_client.batch_generate(items)

            # Verify both models were called
            assert result.cache_misses == 2
            assert result.total_tokens == 300

    @pytest.mark.asyncio
    async def test_batch_generate_large_batch(self, config):
        """Test batch with many items (concurrency control)."""
        # Create fresh client with isolated cache to avoid disk cache hits
        client = TokenEfficientClient(
            config=config,
            use_persistent_cache=False,
            use_semantic_cache=False,
        )

        items = [
            BatchItem(
                id=str(i),
                prompt=f"prompt_{i}",
                system="s",
                model="phi3:mini",
            )
            for i in range(10)
        ]

        with patch.object(client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("Result", 100)

            result = await client.batch_generate(items)

            assert result.cache_misses == 10
            assert result.total_tokens == 1000
            # Phase 1: Verify parallelism occurred (may exceed original config limit)
            # DynamicConcurrencyGate can scale from 4 up to 12 based on hardware state
            assert result.parallel_executions > 0
            assert result.parallel_executions <= len(items)

    def test_initialization(self, config):
        """Test client initialization."""
        client = TokenEfficientClient(
            ollama_base_url="http://custom:11434",
            config=config,
        )

        assert client.ollama.base_url == "http://custom:11434"
        assert client.config == config
        assert client.batch_processor is not None

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, token_client):
        """Test generate with system prompt."""
        with patch.object(token_client.ollama, "generate") as mock_gen:
            mock_gen.return_value = ("Response", 100)

            await token_client.generate(
                prompt="User prompt",
                model="phi3:mini",
                system="You are helpful",
            )

            # Verify system prompt was used
            assert token_client._cache_misses == 1

    @pytest.mark.asyncio
    async def test_batch_error_handling(self, token_client):
        """Test batch generation with some errors."""
        items = [
            BatchItem(id="1", prompt="p1", system="s", model="phi3:mini"),
            BatchItem(id="2", prompt="p2", system="s", model="phi3:mini"),
        ]

        async def failing_generate(*args, **kwargs):
            if kwargs.get("prompt") == "p2":
                raise ValueError("Simulated error")
            return ("Result", 100)

        with patch.object(
            token_client.ollama, "generate", side_effect=failing_generate
        ):
            result = await token_client.batch_generate(items)

            # First item should succeed, second should error
            assert result.items[0].result is not None
            assert result.items[1].error is not None
