"""Cohezion Ouroboros — resilience layer: detection, healing, monitoring, recording."""

import contextlib

# Wiring-sweep 2026-06-22: all four sibling modules were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.ouroboros.detector import (
        AnomalyDetector as AnomalyDetector,
    )

with contextlib.suppress(Exception):
    from cohezion.ouroboros.healer import (
        HealerAgent as HealerAgent,
    )

with contextlib.suppress(Exception):
    from cohezion.ouroboros.monitor import (
        OuroborosMonitor as OuroborosMonitor,
    )

with contextlib.suppress(Exception):
    from cohezion.ouroboros.recorder import (
        OuroborosRecorder as OuroborosRecorder,
    )
