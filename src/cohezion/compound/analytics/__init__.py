"""Execution analytics sub-package for compound engineering."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.compound.analytics.engine import (
        AnalysisConfig as AnalysisConfig,
    )
    from cohezion.compound.analytics.engine import (
        ExecutionAnalyzer as ExecutionAnalyzer,
    )
    from cohezion.compound.analytics.engine import (
        SimpleAnalyzer as SimpleAnalyzer,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.analytics.metrics import (
        MetricsCollector as MetricsCollector,
    )
    from cohezion.compound.analytics.metrics import (
        MetricsSnapshot as MetricsSnapshot,
    )
    from cohezion.compound.analytics.metrics import (
        SimpleMetrics as SimpleMetrics,
    )
