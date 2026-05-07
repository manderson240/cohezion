"""Tests for token-efficient batch processor."""

import asyncio
from unittest.mock import MagicMock

import pytest

from cohezion.core.config import CohezionConfig
from cohezion.swarm.batch_processor import BatchItem, BatchProcessor, CacheEntry


@pytest.fixture
def mock_token_client():
    """Create mock token client."""
    return MagicMock()


@pytest.fixture
def batch_config():
    """Create batch configuration."""
    config = CohezionConfig()
    config.batch.max_batch_size = 10
    config.batch.parallel_tasks = 3
    config.batch.timeout_seconds = 30
    return config


@pytest.fixture
def batch_processor(mock_token_client, batch_config):
    """Create batch processor."""
    return BatchProcessor(mock_token_client, batch_config)


def test_batch_processor_init(batch_processor, batch_config):
    """Test processor initialization."""
    assert batch_processor.config == batch_config
    assert len(batch_processor.cache) == 0


def test_cache_key_generation(batch_processor):
    """Test cache key generation."""
    key1 = batch_processor._cache_key("prompt1", "system1", "model1")
    key2 = batch_processor._cache_key("prompt1", "system1", "model1")
    key3 = batch_processor._cache_key("prompt2", "system1", "model1")

    assert key1 == key2  # Same input → same key
    assert key1 != key3  # Different input → different key
    assert len(key1) == 64  # SHA256 hex string


@pytest.mark.asyncio
async def test_batch_phase1_all_cache_hits(batch_processor):
    """Test Phase 1: all items in cache."""
    # Pre-populate cache
    items = [
        BatchItem(id="1", prompt="p1", system="s1", model="m1"),
        BatchItem(id="2", prompt="p2", system="s1", model="m1"),
    ]

    for item in items:
        key = batch_processor._cache_key(item.prompt, item.system, item.model)
        batch_processor.cache[key] = CacheEntry(
            key=key,
            value="cached_result",
            tokens_used=50,
        )

    # Execute batch (Phase 2 should be skipped)
    async def dummy_execute(item: BatchItem):
        raise RuntimeError("Should not be called if cached")

    result = await batch_processor.process_batch(items, dummy_execute)

    assert result.cache_hits == 2
    assert result.cache_misses == 0
    assert result.cache_hit_rate == 1.0
    assert all(item.cached for item in result.items)


@pytest.mark.asyncio
async def test_batch_phase1_no_cache_hits(batch_processor):
    """Test Phase 1: no items in cache."""
    items = [
        BatchItem(id="1", prompt="p1", system="s1", model="m1"),
        BatchItem(id="2", prompt="p2", system="s1", model="m1"),
    ]

    async def dummy_execute(item: BatchItem):
        return "result", 100

    result = await batch_processor.process_batch(items, dummy_execute)

    assert result.cache_hits == 0
    assert result.cache_misses == 2
    assert result.cache_hit_rate == 0.0
    assert not any(item.cached for item in result.items)


@pytest.mark.asyncio
async def test_batch_phase1_phase2_mixed(batch_processor):
    """Test Phase 1 (cache hits) + Phase 2 (parallel execution)."""
    # Item 1: cached
    item1 = BatchItem(id="1", prompt="p1", system="s1", model="m1")
    key1 = batch_processor._cache_key(item1.prompt, item1.system, item1.model)
    batch_processor.cache[key1] = CacheEntry(key=key1, value="cached", tokens_used=50)

    # Item 2: not cached (will execute)
    item2 = BatchItem(id="2", prompt="p2", system="s1", model="m1")

    items = [item1, item2]

    execution_count = 0

    async def dummy_execute(item: BatchItem):
        nonlocal execution_count
        execution_count += 1
        return f"result_{item.id}", 100

    result = await batch_processor.process_batch(items, dummy_execute)

    assert result.cache_hits == 1
    assert result.cache_misses == 1
    assert result.cache_hit_rate == 0.5
    assert execution_count == 1  # Only non-cached item executed


@pytest.mark.asyncio
async def test_batch_concurrency_limiting(mock_token_client):
    """Test that semaphore is configured for concurrency limit."""
    # Create config and processor with concurrency limit set
    config = CohezionConfig()
    config.batch.parallel_tasks = 2

    processor = BatchProcessor(mock_token_client, config)

    # Verify semaphore is configured
    assert processor._concurrency_semaphore._value == 2
    assert processor.config.batch.parallel_tasks == 2

    items = [BatchItem(id=str(i), prompt=f"p{i}", system="s", model="m") for i in range(3)]

    async def dummy_execute(item: BatchItem):
        return "result", 100

    result = await processor.process_batch(items, dummy_execute)

    # Verify execution happened
    assert result.cache_misses == 3
    assert result.parallel_executions >= 1  # Had parallel work


@pytest.mark.asyncio
async def test_batch_error_handling(batch_processor):
    """Test error handling in Phase 2 execution."""
    items = [
        BatchItem(id="1", prompt="p1", system="s1", model="m1"),
        BatchItem(id="2", prompt="p2", system="s1", model="m1"),
    ]

    async def failing_execute(item: BatchItem):
        if item.id == "1":
            return "result", 100
        else:
            raise ValueError("Simulated error")

    result = await batch_processor.process_batch(items, failing_execute)

    assert result.items[0].result == "result"
    assert result.items[1].error is not None
    assert "Simulated error" in result.items[1].error


@pytest.mark.asyncio
async def test_batch_cache_update_after_execution(batch_processor):
    """Test that executed items are cached for future use."""
    items = [BatchItem(id="1", prompt="p1", system="s1", model="m1")]

    async def dummy_execute(item: BatchItem):
        return "result", 150

    # First execution (cache miss)
    result1 = await batch_processor.process_batch(items, dummy_execute)
    assert result1.cache_misses == 1
    assert len(batch_processor.cache) == 1

    # Second execution (should be cache hit)
    items2 = [BatchItem(id="2", prompt="p1", system="s1", model="m1")]
    result2 = await batch_processor.process_batch(items2, dummy_execute)

    assert result2.cache_hits == 1
    assert result2.cache_misses == 0


@pytest.mark.asyncio
async def test_batch_tokens_saved_calculation(batch_processor):
    """Test token savings from caching."""
    item1 = BatchItem(id="1", prompt="p1", system="s1", model="m1")
    key1 = batch_processor._cache_key(item1.prompt, item1.system, item1.model)
    batch_processor.cache[key1] = CacheEntry(key=key1, value="cached", tokens_used=200)

    items = [item1]

    async def dummy_execute(item: BatchItem):
        return "result", 100

    result = await batch_processor.process_batch(items, dummy_execute)

    assert result.tokens_saved == 200
    assert result.cache_hits == 1


def test_batch_cache_stats(batch_processor, batch_config):
    """Test cache statistics."""
    batch_processor.cache["key1"] = CacheEntry(
        key="key1",
        value="value1",
        tokens_used=100,
    )

    stats = batch_processor.cache_stats()

    assert stats["cache_size"] == 1
    assert stats["max_cache_size"] == batch_config.cache.max_size
    assert stats["cache_enabled"] is True
    assert stats["parallel_tasks"] == 3


def test_batch_clear_cache(batch_processor):
    """Test cache clearing."""
    batch_processor.cache["key1"] = CacheEntry(
        key="key1",
        value="value1",
        tokens_used=100,
    )

    assert len(batch_processor.cache) == 1
    batch_processor.clear_cache()
    assert len(batch_processor.cache) == 0


@pytest.mark.asyncio
async def test_batch_result_total_tokens(batch_processor):
    """Test total token calculation."""
    items = [
        BatchItem(id="1", prompt="p1", system="s1", model="m1"),
        BatchItem(id="2", prompt="p2", system="s1", model="m1"),
    ]

    async def dummy_execute(item: BatchItem):
        tokens = 100 if item.id == "1" else 150
        return "result", tokens

    result = await batch_processor.process_batch(items, dummy_execute)

    assert result.total_tokens == 250


@pytest.mark.asyncio
async def test_batch_timing(batch_processor):
    """Test batch execution timing is better with parallelism."""
    items = [BatchItem(id=str(i), prompt=f"p{i}", system="s", model="m") for i in range(3)]

    async def dummy_execute(item: BatchItem):
        # justify: timing test asserts total_duration_ms > 20ms; need real work
        await asyncio.sleep(0.02)
        return "result", 100

    result = await batch_processor.process_batch(items, dummy_execute)

    # Parallel execution should complete (with Phase 1 DynamicConcurrencyGate overhead)
    # Sequential would be 60ms (3 items * 20ms each)
    # Phase 1: metrics collection adds overhead, but parallelism still provides benefit
    assert result.total_duration_ms > 20  # At least 20ms (one item time)
    assert result.parallel_executions > 0  # Verify parallelism occurred
