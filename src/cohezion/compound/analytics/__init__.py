"""Execution analytics sub-package for compound engineering."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.analytics.engine import (
        AnalysisConfig as AnalysisConfig,
        ExecutionAnalyzer as ExecutionAnalyzer,
        SimpleAnalyzer as SimpleAnalyzer,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.analytics.metrics import (
        MetricsCollector as MetricsCollector,
        MetricsSnapshot as MetricsSnapshot,
        SimpleMetrics as SimpleMetrics,
    )
