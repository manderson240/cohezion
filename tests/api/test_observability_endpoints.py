"""Tests for api/observability_endpoints.py.

Covers metrics analytics and system health endpoints.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.api.observability_endpoints import (
    get_cache_analytics,
    get_health_score,
    get_unified_metrics,
    reset_metrics,
)


@pytest.fixture
def mock_collector():
    collector = MagicMock()
    metrics = MagicMock()
    metrics.to_dict.return_value = {"l1_hits": 10, "l2_hits": 5}
    collector.get_current_metrics.return_value = metrics
    collector.get_aggregate_metrics.return_value = {
        "total_operations": 100,
        "aggregate_tokens": 1000,
        "aggregate_duration_ms": 500.0,
        "avg_tokens_per_operation": 10.0,
        "avg_duration_ms": 5.0,
        "total_guardrail_blocks": 2,
        "total_cache_hits": 15,
        "aggregate_cache_hit_rate": 15.0,
        "uptime_seconds": 3600.0,
    }
    return collector

@pytest.fixture
def mock_analytics():
    analytics = MagicMock()
    analytics.get_cache_analytics.return_value = {"hit_rate": 0.8}
    analytics.get_token_efficiency_analytics.return_value = {"tokens_per_sec": 50.0}
    analytics.compute_health_score.return_value = 0.95
    return analytics

@pytest.mark.asyncio
async def test_get_unified_metrics(mock_collector):
    """[P0] Should return unified metrics."""
    with patch("cohezion.api.observability_endpoints.get_metrics_collector", return_value=mock_collector):
        result = await get_unified_metrics()
        assert "timestamp" in result
        assert "metrics" in result
        assert result["metrics"]["l1_hits"] == 10

@pytest.mark.asyncio
async def test_get_cache_analytics(mock_collector, mock_analytics):
    """[P0] Should return cache analytics."""
    with patch("cohezion.api.observability_endpoints.get_metrics_collector", return_value=mock_collector), \
         patch("cohezion.api.observability_endpoints.get_analytics", return_value=mock_analytics):
        result = await get_cache_analytics()
        assert "cache_performance" in result
        assert result["cache_performance"]["hit_rate"] == 0.8

@pytest.mark.asyncio
async def test_get_health_score(mock_collector, mock_analytics):
    """[P0] Should return system health score."""
    with patch("cohezion.api.observability_endpoints.get_metrics_collector", return_value=mock_collector), \
         patch("cohezion.api.observability_endpoints.get_analytics", return_value=mock_analytics):
        result = await get_health_score()
        assert result["health_score"] == 0.95
        assert result["status"] == "excellent"

@pytest.mark.asyncio
async def test_reset_metrics(mock_collector, mock_analytics):
    """[P0] Should reset metrics."""
    with patch("cohezion.api.observability_endpoints.get_metrics_collector", return_value=mock_collector), \
         patch("cohezion.api.observability_endpoints.get_analytics", return_value=mock_analytics):
        result = await reset_metrics()
        assert result["status"] == "success"
        mock_collector.reset_current_metrics.assert_called_once()
