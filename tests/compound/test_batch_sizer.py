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

        for _i in range(15):
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

        for size, throughput in zip(batch_sizes, throughputs, strict=False):
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
        _size, conf = predictor.predict_optimal_size("analyze", 10)

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

        _size, conf = predictor.predict_optimal_size("search", 10)

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
        size, _conf = predictor.predict_optimal_size("analyze", 10)

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

        size, _conf = predictor.predict_optimal_size("search", 10)

        assert isinstance(size, int)
        assert size > 0


class TestVaultPersistence:
    """Test vault persistence for batch metrics learning."""

    def test_learn_from_vault_no_client(self, predictor):
        """Test learn_from_vault with no vault client configured."""
        # Predictor has no vault_client
        assert predictor.vault_client is None
        count = predictor.learn_from_vault()
        assert count == 0

    def test_learn_from_vault_with_mock_client(self, predictor):
        """Test learn_from_vault with mocked vault client."""

        # Create a mock vault client
        class MockVaultClient:
            def vault_search(self, query, scope="all"):
                # Return empty results
                return []

            def vault_read(self, path):
                return ""

        predictor.vault_client = MockVaultClient()
        count = predictor.learn_from_vault()
        assert count == 0

    def test_parse_yaml_metrics(self, predictor):
        """Test parsing metrics from YAML format."""
        yaml_content = """
batch_size: 32
task_count: 10
task_types: analyze, search, analyze
execution_time: 5.0
tokens_used: 1600
throughput: 320.0
cache_hit_rate: 0.75
errors: 0
timestamp: 2026-02-08T12:00:00
"""
        metrics = predictor._parse_yaml_metrics(yaml_content)
        assert metrics is not None
        assert metrics.batch_size == 32
        assert metrics.task_count == 10
        assert metrics.execution_time == 5.0
        assert metrics.throughput == 320.0
        assert "analyze" in metrics.task_types
        assert "search" in metrics.task_types

    def test_parse_json_metrics(self, predictor):
        """Test parsing metrics from JSON format."""
        json_content = """
Some markdown before

{
  "batch_size": 16,
  "task_count": 5,
  "task_types": ["generate"],
  "execution_time": 3.0,
  "tokens_used": 800,
  "throughput": 266.7,
  "cache_hit_rate": 0.6
}

Some markdown after
"""
        metrics = predictor._parse_batch_metrics(json_content)
        assert metrics is not None
        assert metrics.batch_size == 16
        assert metrics.task_count == 5
        assert metrics.throughput == 266.7

    def test_parse_markdown_fields(self, predictor):
        """Test parsing metrics from markdown fields."""
        markdown_content = """# Batch Execution Report

**batch_size**: 24
**task_count**: 8
**execution_time**: 4.0
**tokens_used**: 1200
**throughput**: 300.0
**cache_hit_rate**: 0.8
**errors**: 0
**task_types**: [analyze, transform]
"""
        metrics = predictor._parse_batch_metrics(markdown_content)
        assert metrics is not None
        assert metrics.batch_size == 24
        assert metrics.task_count == 8
        assert metrics.throughput == 300.0
        assert metrics.cache_hit_rate == 0.8

    def test_parse_invalid_metrics_returns_none(self, predictor):
        """Test parsing invalid content returns None."""
        content = "This is not valid metrics content"
        metrics = predictor._parse_batch_metrics(content)
        assert metrics is None

    def test_parse_incomplete_metrics_returns_none(self, predictor):
        """Test parsing incomplete metrics returns None."""
        # Missing required fields
        content = """
batch_size: 32
task_count: 10
# Missing execution_time and throughput
"""
        metrics = predictor._parse_batch_metrics(content)
        assert metrics is None

    def test_dict_to_metrics_complete(self, predictor):
        """Test converting complete dict to metrics."""
        data = {
            "batch_size": 32,
            "task_count": 10,
            "task_types": ["analyze"],
            "execution_time": 5.0,
            "tokens_used": 1600,
            "throughput": 320.0,
            "cache_hit_rate": 0.75,
            "errors": 0,
            "timestamp": "2026-02-08T12:00:00",
        }
        metrics = predictor._dict_to_metrics(data)
        assert metrics is not None
        assert metrics.batch_size == 32
        assert metrics.throughput == 320.0

    def test_dict_to_metrics_missing_required_fields(self, predictor):
        """Test dict to metrics with missing required fields."""
        data = {
            "batch_size": 32,
            "task_count": 10,
            # Missing execution_time and throughput
        }
        metrics = predictor._dict_to_metrics(data)
        assert metrics is None

    def test_dict_to_metrics_with_defaults(self, predictor):
        """Test dict to metrics uses defaults for optional fields."""
        data = {
            "batch_size": 32,
            "task_count": 10,
            "execution_time": 5.0,
            "throughput": 320.0,
            # Optional fields not provided
        }
        metrics = predictor._dict_to_metrics(data)
        assert metrics is not None
        assert metrics.tokens_used == 0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.task_types == ["unknown"]

    def test_learn_from_vault_integration_with_recording(self, predictor):
        """Test that loaded metrics are recorded correctly."""
        # Start with empty history
        assert len(predictor.history) == 0

        # Manually add a metric as if loaded from vault
        metrics = BatchExecutionMetrics(
            batch_size=32,
            task_count=10,
            task_types=["analyze"],
            execution_time=5.0,
            tokens_used=1600,
            throughput=320.0,
            cache_hit_rate=0.75,
        )
        predictor.record_execution(metrics)

        # Verify it's in history
        assert "analyze" in predictor.history
        assert len(predictor.history["analyze"]) == 1

        # Make a prediction from this data
        size, conf = predictor.predict_optimal_size("analyze", 10)
        assert size == 32
        assert conf > 0.3  # Should have some confidence from one sample

    def test_parse_metrics_with_various_formats(self, predictor):
        """Test parsing metrics with various markdown formats."""
        # Test with different formatting variations
        content = """
### Batch Performance Metrics

Execution Details:
- **batch_size**: 48
- **task_count**: 12
- execution_time: 6.0
- tokens_used: 2000
- throughput: 333.33
- cache_hit_rate: 0.8

Task Types: [generate, search]
"""
        metrics = predictor._parse_batch_metrics(content)
        assert metrics is not None
        assert metrics.batch_size == 48
        assert metrics.throughput == 333.33
