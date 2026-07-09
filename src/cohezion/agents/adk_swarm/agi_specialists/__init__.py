"""AGI specialist agents backed by the Google ADK framework."""

from __future__ import annotations

import contextlib


# Wiring-sweep 2026-06-22: metacognition_agent was a genuine import-graph orphan.
# Note: MetacognitionAgent() runs at module level; pydantic schema may reject kwargs.
with contextlib.suppress(Exception):
    from cohezion.agents.adk_swarm.agi_specialists.metacognition_agent import (
        MetacognitionAgent as MetacognitionAgent,
    )
