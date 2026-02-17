"""Tests for observability dashboard and metrics analytics.

Phase 2 Priority 3 Implementation Tests.
"""

import pytest

from cohezion.observability.metrics_analytics import MetricsAnalytics, PerformanceReport
from cohezion.observability.unified_metrics import (
    InferenceMetrics,
    UnifiedMetricsCollector,
)


class TestMetricsAnalytics:
    """Test metrics analytics and trend tracking."""

    @pytest.fixture
    def analytics(self):
        """Create analytics instance for testing."""
        return MetricsAnalytics(window_size=50)

    def test_analytics_initialization(self, analytics):
        """Test analytics initializes correctly."""
        assert analytics.window_size == 50
        assert len(analytics.history) == 0
        assert analytics.thresholds["cache_hit_rate_low"] == 70

    def test_add_metrics_to_history(self, analytics):
        """Test adding metrics to history."""
        metric = InferenceMetrics(
            cache_l1_hits=10,
            cache_l2_hits=5,
            cache_l3_hits=2,
            cache_misses=3,
            total_tokens=100,
            total_duration_ms=1000,
        )

        analytics.add_metrics(metric)
        assert len(analytics.history) == 1

        # Add another
        analytics.add_metrics(metric)
        assert len(analytics.history) == 2

    def test_window_size_enforcement(self, analytics):
        """Test that history is limited to window_size."""
        metric = InferenceMetrics()

        # Add more than window_size entries
        for _ in range(100):
            analytics.add_metrics(metric)

        assert len(analytics.history) <= 50

    def test_cache_analytics_with_no_data(self, analytics):
        """Test cache analytics with empty history."""
        cache_stats = analytics.get_cache_analytics()

        assert cache_stats["l1_hit_rate_avg"] == 0.0
        assert cache_stats["total_hit_rate_avg"] == 0.0
        assert cache_stats["cache_health"] == "no_data"

    def test_cache_analytics_excellent_health(self, analytics):
        """Test cache analytics with excellent hit rate."""
        # Create metric with ~85% hit rate (good)
        metric = InferenceMetrics(
            cache_l1_hits=425,
            cache_l2_hits=200,
            cache_l3_hits=100,
            cache_misses=275,
        )

        analytics.add_metrics(metric)
        cache_stats = analytics.get_cache_analytics()

        assert cache_stats["cache_health"] in ("good", "excellent")
        assert cache_stats["total_hit_rate_avg"] > 70

    def test_cache_analytics_poor_health(self, analytics):
        """Test cache analytics with low hit rate."""
        metric = InferenceMetrics(
            cache_l1_hits=5,
            cache_l2_hits=5,
            cache_l3_hits=2,
            cache_misses=988,  # Very low hit rate (~1.2%)
        )

        analytics.add_metrics(metric)
        cache_stats = analytics.get_cache_analytics()

        # With very low hit rate, health should not be excellent
        assert cache_stats["cache_health"] != "excellent"
        assert cache_stats["total_hit_rate_avg"] < 20

    def test_token_efficiency_analytics(self, analytics):
        """Test token efficiency metrics."""
        metric = InferenceMetrics(
            total_tokens=500,
            total_duration_ms=5000,  # 5 seconds
            model_usage={"gpt-4": 300, "gpt-3": 200},
        )

        analytics.add_metrics(metric)
        efficiency_stats = analytics.get_token_efficiency_analytics()

        assert efficiency_stats["total_tokens"] == 500
        assert efficiency_stats["avg_tokens_per_op"] == 500
        assert "tokens_per_sec" in efficiency_stats
        assert "efficiency_gap" in efficiency_stats

    def test_guardrail_analytics_high_block_rate(self, analytics):
        """Test guardrail analytics with high block rate."""
        metric = InferenceMetrics(
            guardrail_checks=100,
            guardrail_blocks=10,  # 10% block rate
            guardrail_sanitizations=5,
        )

        analytics.add_metrics(metric)
        guardrail_stats = analytics.get_guardrail_analytics()

        assert guardrail_stats["total_checks"] == 100
        assert guardrail_stats["total_blocks"] == 10
        assert guardrail_stats["block_rate_percent"] == 10.0
        assert guardrail_stats["guardrail_health"] == "warning"

    def test_resource_analytics(self, analytics):
        """Test resource utilization analytics."""
        metric = InferenceMetrics(
            peak_memory_gb=50.0,
            concurrency_waits=5,
        )

        analytics.add_metrics(metric)
        resource_stats = analytics.get_resource_analytics()

        assert resource_stats["peak_memory_gb"] == 50.0
        assert resource_stats["avg_concurrency_waits"] == 5
        assert resource_stats["memory_utilization_percent"] == 39.1

    def test_resource_analytics_critical_memory(self, analytics):
        """Test resource analytics with critical memory usage."""
        metric = InferenceMetrics(peak_memory_gb=115.0)

        analytics.add_metrics(metric)
        resource_stats = analytics.get_resource_analytics()

        assert resource_stats["resource_health"] == "critical"

    def test_health_score_computation(self, analytics):
        """Test overall health score computation."""
        # Add metrics representing good health
        metric = InferenceMetrics(
            cache_l1_hits=400,
            cache_l2_hits=100,
            cache_l3_hits=50,
            cache_misses=50,  # 90% hit rate
            total_tokens=500,
            total_duration_ms=2000,  # 250 tok/sec
            guardrail_checks=100,
            guardrail_blocks=1,  # 1% block rate
            peak_memory_gb=50.0,
        )

        analytics.add_metrics(metric)
        health_score = analytics.compute_health_score()

        assert 0.0 <= health_score <= 1.0
        assert health_score > 0.5  # Should be decent

    def test_dashboard_report_generation(self, analytics):
        """Test comprehensive dashboard report generation."""
        metric = InferenceMetrics(
            cache_l1_hits=300,
            cache_l2_hits=100,
            cache_l3_hits=50,
            cache_misses=50,
            total_tokens=1000,
            total_duration_ms=3000,
            guardrail_checks=100,
            guardrail_blocks=2,
            peak_memory_gb=60.0,
        )

        analytics.add_metrics(metric)
        report = analytics.generate_dashboard_report()

        assert isinstance(report, PerformanceReport)
        assert report.cache_performance is not None
        assert report.token_efficiency is not None
        assert report.guardrail_performance is not None
        assert report.resource_performance is not None
        assert 0.0 <= report.overall_health_score <= 1.0
        assert len(report.recommendations) > 0

    def test_trend_detection_stable(self, analytics):
        """Test trend detection for stable metric."""
        # Add series of stable metrics
        for _ in range(5):
            metric = InferenceMetrics(
                cache_l1_hits=450,
                cache_l2_hits=200,
                cache_l3_hits=150,
                cache_misses=200,  # ~85% hit rate
            )
            analytics.add_metrics(metric)

        trend = analytics.get_trend("total_cache_hit_rate", window=3)

        assert trend is not None
        assert trend.trend_direction == "stable"
        assert not trend.anomaly_detected

    def test_trend_detection_increasing(self, analytics):
        """Test trend detection for increasing metric."""
        # Add increasing sequence of total hit rate
        for hit_count in [100, 200, 300, 400, 500]:
            metric = InferenceMetrics(
                cache_l1_hits=hit_count,
                cache_l2_hits=hit_count // 2,
                cache_l3_hits=0,
                cache_misses=100,
            )
            analytics.add_metrics(metric)

        trend = analytics.get_trend("total_cache_hit_rate", window=3)

        assert trend is not None
        assert trend.trend_direction == "up"
        assert trend.current_value > trend.previous_value

    def test_anomaly_detection(self, analytics):
        """Test anomaly detection in metrics."""
        # Add normal metrics
        for _ in range(3):
            metric = InferenceMetrics(
                cache_l1_hits=300,
                cache_l2_hits=100,
                cache_misses=100,
            )
            analytics.add_metrics(metric)

        # Add anomalous spike
        anomaly_metric = InferenceMetrics(
            cache_l1_hits=50,
            cache_l2_hits=10,
            cache_misses=940,  # Sudden drop in hit rate
        )
        analytics.add_metrics(anomaly_metric)

        trend = analytics.get_trend("total_cache_hit_rate", window=5)

        assert trend is not None
        assert trend.anomaly_detected

    def test_cache_recommendation_generation(self, analytics):
        """Test that cache recommendations are appropriate."""
        # Low hit rate scenario
        low_rate_metric = InferenceMetrics(
            cache_l1_hits=10,
            cache_l2_hits=1,
            cache_misses=989,
        )

        analytics.add_metrics(low_rate_metric)
        cache_stats = analytics.get_cache_analytics()

        # Should have a recommendation (either about low hit rate or L2 utilization)
        assert (
            "cache" in cache_stats["recommendation"].lower()
            or "low" in cache_stats["recommendation"].lower()
            or "threshold" in cache_stats["recommendation"].lower()
        )

    def test_guardrail_recommendation_generation(self, analytics):
        """Test that guardrail recommendations are appropriate."""
        # High block rate scenario
        high_block_metric = InferenceMetrics(
            guardrail_checks=100,
            guardrail_blocks=20,  # 20% block rate
        )

        analytics.add_metrics(high_block_metric)
        guardrail_stats = analytics.get_guardrail_analytics()

        assert "high" in guardrail_stats["recommendation"].lower()


class TestUnifiedMetricsCollector:
    """Test unified metrics collection."""

    def test_collector_initialization(self):
        """Test collector initializes correctly."""
        collector = UnifiedMetricsCollector()

        assert collector.current_metrics is not None
        assert len(collector.history) == 0

    def test_record_guardrail_action(self):
        """Test recording guardrail actions."""
        collector = UnifiedMetricsCollector()

        collector.record_guardrail_action("allow", latency_ms=5.0)
        assert collector.current_metrics.guardrail_checks == 1

        collector.record_guardrail_action("block", latency_ms=3.0)
        assert collector.current_metrics.guardrail_blocks == 1
        assert collector.current_metrics.guardrail_checks == 2

    def test_record_cache_hits(self):
        """Test recording cache hits by tier."""
        collector = UnifiedMetricsCollector()

        collector.record_cache_hit(1)
        assert collector.current_metrics.cache_l1_hits == 1

        collector.record_cache_hit(2)
        assert collector.current_metrics.cache_l2_hits == 1

        collector.record_cache_hit(3)
        assert collector.current_metrics.cache_l3_hits == 1

    def test_record_cache_miss(self):
        """Test recording cache misses."""
        collector = UnifiedMetricsCollector()

        collector.record_cache_miss()
        assert collector.current_metrics.cache_misses == 1

        collector.record_cache_miss()
        assert collector.current_metrics.cache_misses == 2

    def test_record_execution(self):
        """Test recording execution metrics."""
        collector = UnifiedMetricsCollector()

        collector.record_execution(tokens=100, duration_ms=500, model="gpt-4")
        assert collector.current_metrics.total_tokens == 100
        assert collector.current_metrics.total_duration_ms == 500
        assert collector.current_metrics.model_usage["gpt-4"] == 100

        collector.record_execution(tokens=50, duration_ms=200, model="gpt-3")
        assert collector.current_metrics.total_tokens == 150
        assert collector.current_metrics.model_usage["gpt-3"] == 50

    def test_metrics_snapshot(self):
        """Test getting metrics snapshot."""
        collector = UnifiedMetricsCollector()

        collector.record_cache_hit(1)
        collector.record_cache_miss()
        collector.record_execution(tokens=100, duration_ms=500)

        snapshot = collector.get_current_metrics()

        assert snapshot.cache_l1_hits == 1
        assert snapshot.cache_misses == 1
        assert snapshot.total_tokens == 100

    def test_aggregate_metrics(self):
        """Test aggregate metrics calculation."""
        collector = UnifiedMetricsCollector()

        # First operation
        collector.record_cache_hit(1)
        collector.record_execution(tokens=100, duration_ms=500)
        collector.reset_current_metrics()

        # Second operation
        collector.record_cache_hit(2)
        collector.record_execution(tokens=50, duration_ms=250)

        aggregate = collector.get_aggregate_metrics()

        assert aggregate["aggregate_tokens"] == 150
        assert aggregate["total_operations"] == 2
        assert aggregate["total_cache_hits"] == 2

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metric = InferenceMetrics(
            cache_l1_hits=10,
            cache_l2_hits=5,
            cache_misses=3,
            total_tokens=100,
        )

        metric_dict = metric.to_dict()

        assert metric_dict["cache_l1_hits"] == 10
        assert metric_dict["cache_l2_hits"] == 5
        assert metric_dict["total_cache_hit_rate"] == (15 / 18 * 100)


class TestObservabilityIntegration:
    """Integration tests for observability dashboard."""

    def test_full_metrics_lifecycle(self):
        """Test complete metrics lifecycle."""
        collector = UnifiedMetricsCollector()
        analytics = MetricsAnalytics(window_size=10)

        # Simulate multiple operations
        for _i in range(5):
            collector.record_cache_hit(1)
            collector.record_execution(tokens=100, duration_ms=500, model="gpt-4")
            metrics = collector.get_current_metrics()
            analytics.add_metrics(metrics)

        # Generate report
        report = analytics.generate_dashboard_report()

        assert report is not None
        assert report.cache_performance["l1_hit_rate_avg"] == 100.0
        assert len(report.recommendations) > 0
        assert 0.0 <= report.overall_health_score <= 1.0

    def test_metrics_export_to_dict(self):
        """Test exporting all metrics to dictionary."""
        collector = UnifiedMetricsCollector()

        collector.record_cache_hit(1)
        collector.record_cache_hit(2)
        collector.record_cache_miss()
        collector.record_guardrail_action("block")
        collector.record_execution(tokens=200, duration_ms=1000)

        metrics = collector.get_current_metrics()
        metrics_dict = metrics.to_dict()

        assert "cache_l1_hits" in metrics_dict
        assert "total_cache_hit_rate" in metrics_dict
        assert "guardrail_block_rate" in metrics_dict
        assert metrics_dict["cache_l1_hits"] == 1
        assert metrics_dict["cache_l2_hits"] == 1
