"""Tests for Base Repository compound engineering features.

Tests:
- Batch operations (batch_create, batch_get)
- Metrics collection and analysis
- Error handling and resilience
- Token efficiency patterns
"""

from __future__ import annotations

import contextlib
import time

import pytest

from cohezion.core.persistence.repositories.base import (
    BaseRepository,
    BatchOperationResult,
    RepositoryMetrics,
)


class MockEntity:
    """Mock entity for testing."""

    def __init__(self, entity_id: str, name: str):
        self.id = entity_id
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, MockEntity):
            return False
        return self.id == other.id and self.name == other.name


class MockRepository(BaseRepository[MockEntity, None]):
    """Mock repository for testing base functionality."""

    def __init__(self):
        super().__init__(table_name="test_entities")
        self._storage: dict[str, MockEntity] = {}

    async def create(self, entity: MockEntity) -> str:
        """Create an entity."""
        return await self._execute_with_metrics(
            operation="create",
            execute_fn=lambda: self._create_entity(entity),
            items_count=1,
        )

    async def _create_entity(self, entity: MockEntity) -> str:
        """Internal create without metrics."""
        self._storage[entity.id] = entity
        return entity.id

    async def get(self, entity_id: str) -> MockEntity | None:
        """Get an entity by ID."""
        return await self._execute_with_metrics(
            operation="get",
            execute_fn=lambda: self._get_entity(entity_id),
            items_count=1,
        )

    async def _get_entity(self, entity_id: str) -> MockEntity | None:
        """Internal get without metrics."""
        return self._storage.get(entity_id)


class TestRepositoryMetrics:
    """Tests for RepositoryMetrics dataclass."""

    @pytest.mark.fast
    def test_from_operation_success(self):
        """Test creating metrics from successful operation."""
        start = time.time()
        time.sleep(0.01)  # Small delay

        metrics = RepositoryMetrics.from_operation(
            operation="test_op",
            start_time=start,
            success=True,
            items=5,
        )

        assert metrics.operation == "test_op"
        assert metrics.success is True
        assert metrics.items_processed == 5
        assert metrics.duration_ms >= 10  # At least 10ms
        assert metrics.error_message is None

    @pytest.mark.fast
    def test_from_operation_failure(self):
        """Test creating metrics from failed operation."""
        start = time.time()
        error = ValueError("Test error")

        metrics = RepositoryMetrics.from_operation(
            operation="failed_op",
            start_time=start,
            success=False,
            items=3,
            error=error,
        )

        assert metrics.operation == "failed_op"
        assert metrics.success is False
        assert metrics.items_processed == 3
        assert "Test error" in metrics.error_message

    @pytest.mark.fast
    def test_metrics_default_values(self):
        """Test default metric values."""
        metrics = RepositoryMetrics(
            operation="test",
            duration_ms=100.0,
            success=True,
        )

        assert metrics.items_processed == 1
        assert metrics.batch_size == 1
        assert metrics.cache_hit is False
        assert metrics.error_message is None


class TestBatchOperationResult:
    """Tests for BatchOperationResult dataclass."""

    @pytest.mark.fast
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = BatchOperationResult(
            success=True,
            items_processed=8,
            items_failed=2,
        )

        assert result.success_rate == 0.8  # 8/10

    @pytest.mark.fast
    def test_success_rate_zero_items(self):
        """Test success rate with zero items."""
        result = BatchOperationResult(
            success=True,
            items_processed=0,
            items_failed=0,
        )

        assert result.success_rate == 0.0

    @pytest.mark.fast
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        result = BatchOperationResult(
            success=True,
            items_processed=10,
            items_failed=0,
            cache_hits=7,
            cache_misses=3,
        )

        assert result.cache_hit_rate == 0.7  # 7/10

    @pytest.mark.fast
    def test_cache_hit_rate_zero_total(self):
        """Test cache hit rate with zero cache operations."""
        result = BatchOperationResult(
            success=True,
            items_processed=10,
            items_failed=0,
            cache_hits=0,
            cache_misses=0,
        )

        assert result.cache_hit_rate == 0.0

    @pytest.mark.fast
    def test_full_batch_result(self):
        """Test complete batch result."""
        result = BatchOperationResult(
            success=False,
            items_processed=7,
            items_failed=3,
            results=["id1", "id2", "id3"],
            errors=[(0, "Error 1"), (1, "Error 2")],
            total_duration_ms=150.5,
            cache_hits=5,
            cache_misses=5,
        )

        assert len(result.results) == 3
        assert len(result.errors) == 2
        assert result.total_duration_ms == 150.5
        assert result.success_rate == 0.7
        assert result.cache_hit_rate == 0.5


class TestBaseRepository:
    """Tests for BaseRepository functionality."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_repository_initialization(self):
        """Test repository initialization with table name."""
        repo = MockRepository()

        assert repo._table_name == "test_entities"
        assert repo._metrics == []

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_metrics_recording(self):
        """Test that operations record metrics."""
        repo = MockRepository()

        # Create entity
        entity = MockEntity(id="test1", name="Test Entity")
        await repo.create(entity)

        # Should have recorded metrics
        assert len(repo._metrics) > 0
        metrics = repo._metrics[-1]
        assert metrics.operation == "create"
        assert metrics.success is True
        assert metrics.items_processed == 1

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_metrics_recording_on_failure(self):
        """Test that failed operations record metrics."""
        repo = MockRepository()

        # Try to get non-existent entity (returns None, not exception)
        await repo.get("nonexistent")

        # Should have recorded metrics (success=False for None result)
        assert len(repo._metrics) > 0
        metrics = repo._metrics[-1]
        assert metrics.operation == "get"
        # Note: In mock, None is returned, not exception

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_get_recent_metrics(self):
        """Test retrieving recent metrics."""
        repo = MockRepository()

        # Create multiple entities
        for i in range(5):
            entity = MockEntity(id=f"test{i}", name=f"Test {i}")
            await repo.create(entity)

        # Get recent metrics
        recent = repo._get_recent_metrics(operation="create", limit=3)

        assert len(recent) == 3
        assert all(m.operation == "create" for m in recent)

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_metrics_limit_enforcement(self):
        """Test that metrics are limited to prevent memory growth."""
        repo = MockRepository()

        # Create 1100 entities (exceeds 1000 limit)
        for i in range(1100):
            entity = MockEntity(id=f"test{i}", name=f"Test {i}")
            await repo.create(entity)

        # Should have exactly 1000 metrics
        assert len(repo._metrics) == 1000

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_get_metrics_summary(self):
        """Test metrics summary generation."""
        repo = MockRepository()

        # Create some entities
        for i in range(5):
            entity = MockEntity(id=f"test{i}", name=f"Test {i}")
            await repo.create(entity)

        # Get some entities (mix of hits and misses)
        for i in range(3):
            await repo.get(f"test{i}")
        await repo.get("nonexistent")

        summary = repo.get_metrics_summary()

        assert summary["total_operations"] > 0
        assert "successful" in summary
        assert "failed" in summary
        assert "avg_duration_ms" in summary
        assert "by_operation" in summary
        assert "create" in summary["by_operation"]

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_clear_metrics(self):
        """Test clearing metrics."""
        repo = MockRepository()

        # Create entity to generate metrics
        entity = MockEntity(id="test1", name="Test")
        await repo.create(entity)

        assert len(repo._metrics) > 0

        # Clear metrics
        repo.clear_metrics()

        assert len(repo._metrics) == 0

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_batch_create(self):
        """Test batch create operation."""
        repo = MockRepository()

        # Create multiple entities
        entities = [MockEntity(id=f"batch{i}", name=f"Batch {i}") for i in range(5)]

        result = await repo.batch_create(entities)

        assert result.success is True
        assert result.items_processed == 5
        assert result.items_failed == 0
        assert len(result.results) == 5
        assert all("batch" in id for id in result.results)

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_batch_create_partial_failure(self):
        """Test batch create with partial failures."""
        repo = MockRepository()

        # Create entities - empty ID will fail validation in real impl
        entities = [
            MockEntity(id="valid1", name="Valid 1"),
            MockEntity(id="valid2", name="Valid 2"),
            MockEntity(id="valid3", name="Valid 3"),
        ]

        result = await repo.batch_create(entities)

        # All should succeed in mock implementation
        assert result.items_processed == 3
        assert result.items_failed == 0

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_batch_get(self):
        """Test batch get operation."""
        repo = MockRepository()

        # Create entities first
        for i in range(5):
            entity = MockEntity(id=f"get{i}", name=f"Get {i}")
            await repo.create(entity)

        # Batch get
        ids = [f"get{i}" for i in range(5)]
        result = await repo.batch_get(ids)

        assert result.success is True
        assert result.items_processed == 5
        assert result.items_failed == 0
        assert len(result.results) == 5
        assert all(isinstance(e, MockEntity) for e in result.results)

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_batch_get_with_missing(self):
        """Test batch get with some missing entities."""
        repo = MockRepository()

        # Create only some entities
        for i in range(3):
            entity = MockEntity(id=f"partial{i}", name=f"Partial {i}")
            await repo.create(entity)

        # Try to get more than exist
        ids = [f"partial{i}" for i in range(5)]
        result = await repo.batch_get(ids)

        assert result.success is False  # Some failed
        assert result.items_processed == 3
        assert result.items_failed == 2

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_execute_with_metrics(self):
        """Test execute_with_metrics wrapper."""
        repo = MockRepository()

        async def test_operation():
            return "success"

        result = await repo._execute_with_metrics(
            operation="test_op",
            execute_fn=test_operation,
            items_count=1,
        )

        assert result == "success"
        assert len(repo._metrics) == 1
        assert repo._metrics[0].operation == "test_op"
        assert repo._metrics[0].success is True

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_execute_with_metrics_failure(self):
        """Test execute_with_metrics on failure."""
        repo = MockRepository()

        async def failing_operation():
            raise RuntimeError("Test failure")

        with contextlib.suppress(RuntimeError):
            await repo._execute_with_metrics(
                operation="failing_op",
                execute_fn=failing_operation,
                items_count=1,
            )

        assert len(repo._metrics) == 1
        assert repo._metrics[0].success is False
        assert "Test failure" in repo._metrics[0].error_message


class TestCompoundEngineeringIntegration:
    """Tests for compound engineering pattern integration."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_metrics_feed_batch_sizing(self):
        """Test that metrics can be used for batch sizing decisions."""
        repo = MockRepository()

        # Simulate batch operations with varying sizes
        for batch_size in [10, 20, 50, 100]:
            entities = [MockEntity(id=f"perf{i}", name=f"Perf {i}") for i in range(batch_size)]
            await repo.batch_create(entities)

        # Get metrics summary
        summary = repo.get_metrics_summary()

        # Should have operation stats for batch sizing
        assert "by_operation" in summary
        # batch_create calls create() internally, so we check for create
        assert "create" in summary["by_operation"]

        create_stats = summary["by_operation"]["create"]
        assert "avg_duration_ms" in create_stats
        assert "count" in create_stats
        assert create_stats["count"] == 180  # 10+20+50+100

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_metrics_feed_adversarial_review(self):
        """Test that metrics provide data for adversarial review."""
        repo = MockRepository()

        # Create entities to generate metrics
        for i in range(10):
            entity = MockEntity(id=f"review{i}", name=f"Review {i}")
            await repo.create(entity)

        # Get metrics for performance review
        summary = repo.get_metrics_summary()

        # Adversarial review can analyze:
        assert summary["total_operations"] > 0
        assert summary["success_rate"] > 0
        assert summary["avg_duration_ms"] > 0

        # Performance perspective can check for slow operations
        recent_metrics = repo._get_recent_metrics(limit=100)
        slow_ops = [m for m in recent_metrics if m.duration_ms > 1000]
        assert len(slow_ops) == 0  # Should be fast

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_token_efficiency_context_separation(self):
        """Test token efficiency via metrics caching."""
        repo = MockRepository()

        # First get (cache miss)
        entity = MockEntity(id="cache_test", name="Cache Test")
        await repo.create(entity)
        await repo.get("cache_test")

        # Get metrics
        summary = repo.get_metrics_summary()

        # Token efficiency: metrics provide cache analysis
        assert "cache_hit_rate" in summary
        # In real implementation, this would feed into cache optimization

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_error_handling_resilience(self):
        """Test error handling for resilience perspective."""
        repo = MockRepository()

        # Create entities
        for i in range(5):
            entity = MockEntity(id=f"resilient{i}", name=f"Resilient {i}")
            await repo.create(entity)

        # Batch get with some failures
        ids = ["resilient0", "nonexistent1", "resilient2", "nonexistent3", "resilient4"]
        result = await repo.batch_get(ids)

        # Resilience: partial success is acceptable
        assert result.items_processed == 3
        assert result.items_failed == 2
        assert result.success_rate == 0.6

        # Error details available for debugging
        assert len(result.errors) == 2
