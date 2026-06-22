"""ADK Swarm — Google ADK-backed specialist sub-agents for AGI and AIMO benchmarks."""

from __future__ import annotations

import contextlib

# Wiring-sweep 2026-06-22: agi_specialists sub-package was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.agi_specialists import (
        MetacognitionAgent as MetacognitionAgent,
    )

# Wiring-sweep 2026-06-22: aimo_specialists sub-package was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.aimo_specialists import (
        AIMOOrchestrator as AIMOOrchestrator,
    )
