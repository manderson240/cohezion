"""AIMO mathematical specialist agents backed by the Google ADK framework."""

from __future__ import annotations

import contextlib


# Wiring-sweep 2026-06-22: agent (AlgebraistAgent) was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.aimo_specialists.agent import (
        AlgebraistAgent as AlgebraistAgent,
    )

# Wiring-sweep 2026-06-22: number_theorist was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.aimo_specialists.number_theorist import (
        NumberTheoristAgent as NumberTheoristAgent,
    )

# Wiring-sweep 2026-06-22: orchestrator was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.aimo_specialists.orchestrator import (
        AIMOOrchestrator as AIMOOrchestrator,
    )
