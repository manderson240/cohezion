"""Tests for BatchSizePredictor - Sprint 1 Experience-Guided Batch Sizing."""

from __future__ import annotations

import pytest

from cohezion.compound.batch_sizer import (
    BatchExecutionMetrics,
    BatchSizePredictor,
    get_batch_size_predictor,
)


@pytest.fixture
def predictor() -> BatchSizePredictor:
    """Create a batch size predictor instance."""
    return BatchSizePredictor(history_size=50)


@pytest.fixture
def sample_metrics() -> BatchExecutionMetrics:
    """Create sample execution metrics."""
    return BatchExecutionMetrics(
        batch_size=32,
        task_count=10,
        task_types=["analyze", "analyze", "search"],
        execution_time=5.0,
        tokens_used=1600,
        throughput=320.0,
        cache_hit_rate=0.75,
        timestamp="2026-02-08T12:00:00",
    )


class TestBatchExecutionMetrics:
    """Test BatchExecutionMetrics dataclass."""

    def test_initialization(self, sample_metrics):
        """Test metrics initialization."""
        assert sample_metrics.batch_size == 32
        assert sample_metrics.task_count == 10
        assert sample_metrics.throughput == 320.0

    def test_tokens_per_task(self, sample_metrics):
        """Test tokens per task calculation."""
        assert sample_metrics.tokens_per_task == 160.0  # 1600 / 10

    def test_primary_task_type(self, sample_metrics):
        """Test primary task type detection."""
        assert sample_metrics.primary_task_type == "analyze"  # Most common


class TestBatchSizePredictorInit:
    """Test predictor initialization."""

    def test_initialization_defaults(self, predictor):
        """Test initialization with defaults."""
        assert predictor.history_size == 50
        assert predictor.min_confidence_threshold == 0.5
        assert len(predictor.history) == 0

    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        predictor = BatchSizePredictor(history_size=200, min_confidence_threshold=0.7)
        assert predictor.history_size == 200
        assert predictor.min_confidence_threshold == 0.7

    def test_default_batch_sizes(self, predictor):
        """Test default batch size heuristics."""
        assert predictor.DEFAULT_BATCH_SIZES["generate"] == 16
        assert predictor.DEFAULT_BATCH_SIZES["search"] == 64
        assert predictor.DEFAULT_BATCH_SIZES["unknown"] == 32


class TestRecordExecution:
    """Test recording executions."""

    def test_record_single_execution(self, predictor, sample_metrics):
        """Test recording a single execution."""
        predictor.record_execution(sample_metrics)

        assert "analyze" in predictor.history
        assert len(predictor.history["analyze"]) == 1
        assert predictor.history["analyze"][0].batch_size == 32

    def test_record_multiple_executions(self, predictor, sample_metrics):
        """Test recording multiple executions."""
        for i in range(5):
            metrics = BatchExecutionMetrics(
                batch_size=16 + (i * 8),
                task_count=10,
                task_types=["analyze"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=100.0 + (i * 10),
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        assert len(predictor.history["analyze"]) == 5

    def test_history_size_limit(self, predictor, sample_metrics):
        """Test history size limit enforcement."""
        predictor.history_size = 10

        for i in range(15):
            metrics = BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=["analyze"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=100.0,
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        # Should keep only last 10
        assert len(predictor.history["analyze"]) == 10

    def test_record_multiple_task_types(self, predictor):
        """Test recording executions for different task types."""
        for task_type in ["generate", "analyze", "search"]:
            metrics = BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=[task_type],
                execution_time=5.0,
                tokens_used=1600,
                throughput=100.0,
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        assert len(predictor.history) == 3
        assert "generate" in predictor.history
        assert "analyze" in predictor.history
        assert "search" in predictor.history


class TestPredictOptimalSize:
    """Test batch size prediction."""

    def test_predict_no_history_fallback(self, predictor):
        """Test prediction falls back to heuristic when no history."""
        size, confidence = predictor.predict_optimal_size("analyze", 10)

        assert size == 32  # Heuristic for analyze
        assert confidence == 0.3  # Low confidence (heuristic)

    def test_predict_unknown_task_type(self, predictor):
        """Test prediction for unknown task type."""
        size, confidence = predictor.predict_optimal_size("unknown", 10)

        assert size == 32  # Default heuristic
        assert confidence == 0.3

    def test_predict_with_single_execution(self, predictor, sample_metrics):
        """Test prediction with single historical execution."""
        predictor.record_execution(sample_metrics)

        size, confidence = predictor.predict_optimal_size("analyze", 10)

        assert size == 32  # The one batch size we have
        assert confidence > 0.3  # Higher than heuristic

    def test_predict_finds_optimal_throughput(self, predictor):
        """Test prediction finds batch size with highest throughput."""
        # Record executions with increasing throughput
        batch_sizes = [16, 32, 48, 64]
        throughputs = [100.0, 150.0, 140.0, 120.0]  # Peak at batch_size=32

        for size, throughput in zip(batch_sizes, throughputs):
            metrics = BatchExecutionMetrics(
                batch_size=size,
                task_count=10,
                task_types=["search"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=throughput,
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        size, confidence = predictor.predict_optimal_size("search", 10)

        assert size == 32  # Highest throughput
        assert confidence > 0.5

    def test_predict_multiple_samples_increases_confidence(self, predictor):
        """Test that more historical samples increase confidence."""
        # Record 3 executions at batch_size=32
        for _ in range(3):
            metrics = BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=["search"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=150.0,
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        size1, conf1 = predictor.predict_optimal_size("search", 10)

        # Record more executions
        for _ in range(5):
            metrics = BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=["search"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=151.0,
                cache_hit_rate=0.7,
            )
            predictor.record_execution(metrics)

        size2, conf2 = predictor.predict_optimal_size("search", 10)

        assert size1 == size2
        assert conf2 > conf1  # More data = higher confidence


class TestGetConfidence:
    """Test confidence reporting."""

    def test_confidence_no_prediction(self, predictor):
        """Test confidence when no prediction made."""
        assert predictor.get_confidence() == 0.0

    def test_confidence_after_prediction(self, predictor, sample_metrics):
        """Test confidence after prediction."""
        predictor.record_execution(sample_metrics)
        size, conf = predictor.predict_optimal_size("analyze", 10)

        assert predictor.get_confidence() == conf

    def test_confidence_bounds(self, predictor):
        """Test confidence stays between 0-1."""
        predictor.record_execution(
            BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=["search"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=150.0,
                cache_hit_rate=0.7,
            )
        )

        for _ in range(50):
            predictor.record_execution(
                BatchExecutionMetrics(
                    batch_size=32,
                    task_count=10,
                    task_types=["search"],
                    execution_time=5.0,
                    tokens_used=1600,
                    throughput=150.0,
                    cache_hit_rate=0.7,
                )
            )

        size, conf = predictor.predict_optimal_size("search", 10)

        assert 0.0 <= conf <= 1.0
        assert conf <= 0.95  # Should be capped


class TestGetStats:
    """Test statistics reporting."""

    def test_stats_empty_predictor(self, predictor):
        """Test stats on empty predictor."""
        stats = predictor.get_stats()

        assert "task_types_learned" in stats
        assert stats["total_records"] == 0
        assert stats["history_per_type"] == {}

    def test_stats_with_data(self, predictor):
        """Test stats with recorded data."""
        for task_type in ["generate", "analyze"]:
            for i in range(3):
                predictor.record_execution(
                    BatchExecutionMetrics(
                        batch_size=32 + i,
                        task_count=10,
                        task_types=[task_type],
                        execution_time=5.0,
                        tokens_used=1600,
                        throughput=100.0,
                        cache_hit_rate=0.7,
                    )
                )

        stats = predictor.get_stats()

        assert len(stats["task_types_learned"]) == 2
        assert stats["total_records"] == 6
        assert stats["history_per_type"]["generate"] == 3
        assert stats["history_per_type"]["analyze"] == 3


class TestSingletonFactory:
    """Test singleton factory function."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        p1 = get_batch_size_predictor()
        p2 = get_batch_size_predictor()

        assert p1 is p2

    def test_reset_singleton(self):
        """Test resetting singleton."""
        p1 = get_batch_size_predictor()
        p1.record_execution(
            BatchExecutionMetrics(
                batch_size=32,
                task_count=10,
                task_types=["analyze"],
                execution_time=5.0,
                tokens_used=1600,
                throughput=100.0,
                cache_hit_rate=0.7,
            )
        )

        assert len(p1.history) > 0

        p2 = get_batch_size_predictor(reset=True)

        assert p1 is not p2
        assert len(p2.history) == 0


class TestEdgeCases:
    """Test edge cases."""

    def test_predict_zero_task_count(self, predictor):
        """Test prediction with zero tasks."""
        size, confidence = predictor.predict_optimal_size("analyze", 0)

        assert isinstance(size, int)
        assert 0 <= confidence <= 1

    def test_mixed_task_types_in_batch(self, predictor):
        """Test handling of mixed task types in batch."""
        metrics = BatchExecutionMetrics(
            batch_size=32,
            task_count=10,
            task_types=["generate", "analyze", "search", "analyze"],
            execution_time=5.0,
            tokens_used=1600,
            throughput=100.0,
            cache_hit_rate=0.7,
        )
        predictor.record_execution(metrics)

        # Should use most common type (analyze)
        size, conf = predictor.predict_optimal_size("analyze", 10)

        assert size == 32

    def test_empty_task_types(self, predictor):
        """Test handling of empty task types."""
        metrics = BatchExecutionMetrics(
            batch_size=32,
            task_count=10,
            task_types=[],
            execution_time=5.0,
            tokens_used=1600,
            throughput=100.0,
            cache_hit_rate=0.7,
        )
        predictor.record_execution(metrics)

        # Should fallback to unknown
        assert "unknown" in predictor.history

    def test_very_low_throughput(self, predictor):
        """Test handling of very low throughput."""
        metrics = BatchExecutionMetrics(
            batch_size=32,
            task_count=10,
            task_types=["search"],
            execution_time=100.0,  # Very slow
            tokens_used=100,  # Very few tokens
            throughput=1.0,  # Very low throughput
            cache_hit_rate=0.0,
        )
        predictor.record_execution(metrics)

        size, conf = predictor.predict_optimal_size("search", 10)

        assert isinstance(size, int)
        assert size > 0
