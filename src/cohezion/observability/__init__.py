"""Observability and metrics infrastructure."""

import contextlib

from cohezion.observability.unified_metrics import (
    InferenceMetrics,
    UnifiedMetricsCollector,
)


__all__ = ["InferenceMetrics", "UnifiedMetricsCollector"]

with contextlib.suppress(Exception):
    from cohezion.observability.gpu_monitor import GPUMetrics as GPUMetrics
    from cohezion.observability.gpu_monitor import GPUMonitor as GPUMonitor
    from cohezion.observability.gpu_monitor import (
        ThermalProfilingResult as ThermalProfilingResult,
    )

with contextlib.suppress(Exception):
    from cohezion.observability.metrics_analytics import (
        MetricsAnalytics as MetricsAnalytics,
    )
    from cohezion.observability.metrics_analytics import MetricsTrend as MetricsTrend
    from cohezion.observability.metrics_analytics import (
        PerformanceReport as PerformanceReport,
    )
