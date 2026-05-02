"""API endpoints for observability dashboard.

Exposes:
- /metrics/unified - Comprehensive metrics snapshot
- /metrics/cache - Cache performance analytics
- /metrics/efficiency - Token efficiency metrics
- /metrics/health - System health score and recommendations
- /metrics/trends - Trend analysis for key metrics
- /metrics/dashboard - Full dashboard report
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from cohezion.observability.metrics_analytics import MetricsAnalytics
from cohezion.observability.unified_metrics import get_metrics_collector


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["observability"])

# Global analytics instance
_analytics: MetricsAnalytics | None = None


def get_analytics() -> MetricsAnalytics:
    """Get or create global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = MetricsAnalytics(window_size=100)
    return _analytics


@router.get("/unified")
async def get_unified_metrics():
    """Get comprehensive unified metrics snapshot.

    Returns current state of all subsystems:
    - Guardrail operations
    - Cache performance by tier
    - Token usage and efficiency
    - Session management
    - Resource utilization

    Returns:
        dict with all current metrics
    """
    try:
        collector = get_metrics_collector()
        metrics = collector.get_current_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.to_dict(),
        }
    except Exception as e:
        logger.error("Failed to get unified metrics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/cache")
async def get_cache_analytics():
    """Get cache performance analytics.

    Returns:
        dict with cache hit rates by tier, health status, recommendations
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        # Add current metrics to analytics
        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        cache_analytics = analytics.get_cache_analytics()

        return {
            "timestamp": datetime.now().isoformat(),
            "cache_performance": cache_analytics,
        }
    except Exception as e:
        logger.error("Failed to get cache analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/efficiency")
async def get_token_efficiency():
    """Get token efficiency metrics.

    Returns:
        dict with tokens per second, average duration, efficiency health
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        efficiency_analytics = analytics.get_token_efficiency_analytics()

        return {
            "timestamp": datetime.now().isoformat(),
            "token_efficiency": efficiency_analytics,
        }
    except Exception as e:
        logger.error("Failed to get token efficiency metrics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/guardrails")
async def get_guardrail_analytics():
    """Get guardrail performance metrics.

    Returns:
        dict with block rates, check counts, health status
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        guardrail_analytics = analytics.get_guardrail_analytics()

        return {
            "timestamp": datetime.now().isoformat(),
            "guardrail_performance": guardrail_analytics,
        }
    except Exception as e:
        logger.error("Failed to get guardrail analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/resources")
async def get_resource_analytics():
    """Get resource utilization metrics.

    Returns:
        dict with memory usage, concurrency waits, resource health
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        resource_analytics = analytics.get_resource_analytics()

        return {
            "timestamp": datetime.now().isoformat(),
            "resource_performance": resource_analytics,
        }
    except Exception as e:
        logger.error("Failed to get resource analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def get_health_score():
    """Get system health score and recommendations.

    Returns:
        dict with health score (0.0-1.0) and actionable recommendations
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        health_score = analytics.compute_health_score()

        # Map health score to status
        if health_score >= 0.90:
            status = "excellent"
        elif health_score >= 0.75:
            status = "good"
        elif health_score >= 0.60:
            status = "fair"
        else:
            status = "poor"

        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": round(health_score, 3),
            "status": status,
            "recommendations": [],  # Will be populated in full dashboard
        }
    except Exception as e:
        logger.error("Failed to get health score: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/trends/{metric_name}")
async def get_metric_trend(metric_name: str, window: int = 10):
    """Get trend for a specific metric.

    Args:
        metric_name: Metric to track (e.g., "total_cache_hit_rate")
        window: Number of historical records to analyze

    Returns:
        dict with current value, previous value, trend direction, anomaly info
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        trend = analytics.get_trend(metric_name, window)

        if trend is None:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data for metric '{metric_name}' or metric not found",
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "metric": metric_name,
            "trend": {
                "current_value": round(trend.current_value, 2),
                "previous_value": round(trend.previous_value, 2),
                "change_percent": round(trend.change_percent, 2),
                "direction": trend.trend_direction,
                "anomaly_detected": trend.anomaly_detected,
                "anomaly_reason": trend.anomaly_reason,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get metric trend: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/dashboard")
async def get_full_dashboard():
    """Get comprehensive dashboard report.

    Combines all metrics, analytics, and recommendations into single response.

    Returns:
        dict with complete dashboard data including:
        - All subsystem metrics
        - Trend information
        - Health scores
        - Actionable recommendations
        - System status
    """
    try:
        analytics = get_analytics()
        collector = get_metrics_collector()

        metrics = collector.get_current_metrics()
        analytics.add_metrics(metrics)

        # Generate comprehensive report
        report = analytics.generate_dashboard_report()

        # Get aggregate statistics
        aggregate_metrics = collector.get_aggregate_metrics()

        # Get key trends
        cache_trend = analytics.get_trend("total_cache_hit_rate")
        efficiency_trend = analytics.get_trend("l2_cache_hit_rate")

        return {
            "timestamp": report.timestamp.isoformat(),
            "system_status": {
                "overall_health_score": round(report.overall_health_score, 3),
                "health_status": (
                    "excellent"
                    if report.overall_health_score >= 0.90
                    else (
                        "good"
                        if report.overall_health_score >= 0.75
                        else ("fair" if report.overall_health_score >= 0.60 else "poor")
                    )
                ),
            },
            "metrics": {
                "cache": report.cache_performance,
                "token_efficiency": report.token_efficiency,
                "guardrails": report.guardrail_performance,
                "resources": report.resource_performance,
            },
            "aggregate_statistics": {
                "total_operations": aggregate_metrics["total_operations"],
                "aggregate_tokens": aggregate_metrics["aggregate_tokens"],
                "aggregate_duration_ms": round(aggregate_metrics["aggregate_duration_ms"], 2),
                "avg_tokens_per_operation": round(aggregate_metrics["avg_tokens_per_operation"], 1),
                "avg_duration_ms": round(aggregate_metrics["avg_duration_ms"], 2),
                "total_guardrail_blocks": aggregate_metrics["total_guardrail_blocks"],
                "total_cache_hits": aggregate_metrics["total_cache_hits"],
                "aggregate_cache_hit_rate": round(aggregate_metrics["aggregate_cache_hit_rate"], 2),
                "uptime_seconds": round(aggregate_metrics["uptime_seconds"], 1),
            },
            "trends": {
                "cache_hit_rate": (
                    {
                        "current": round(cache_trend.current_value, 2),
                        "change_percent": round(cache_trend.change_percent, 2),
                        "direction": cache_trend.trend_direction,
                        "anomaly": cache_trend.anomaly_detected,
                    }
                    if cache_trend
                    else None
                ),
                "l2_hit_rate": (
                    {
                        "current": round(efficiency_trend.current_value, 2),
                        "change_percent": round(efficiency_trend.change_percent, 2),
                        "direction": efficiency_trend.trend_direction,
                        "anomaly": efficiency_trend.anomaly_detected,
                    }
                    if efficiency_trend
                    else None
                ),
            },
            "recommendations": report.recommendations,
        }
    except Exception as e:
        logger.error("Failed to generate dashboard: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reset")
async def reset_metrics():
    """Reset current metrics (archive to history).

    Useful for clearing metrics between sessions or test cycles.

    Returns:
        dict with confirmation
    """
    try:
        collector = get_metrics_collector()
        collector.reset_current_metrics()
        analytics = get_analytics()
        analytics.add_metrics(collector.get_current_metrics())

        return {
            "status": "success",
            "message": "Metrics reset and archived to history",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Failed to reset metrics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
