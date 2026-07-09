"""ARC-AGI specialist agents (ADK-backed) — guard-wrapped; google.adk API may drift."""

from __future__ import annotations

import contextlib


# Wiring-sweep 2026-06-22: manifold_agent was a genuine import-graph orphan.
# Note: ARCManifoldAgent uses @adk.tool decorator that is absent in adk>=2.x; suppressed.
with contextlib.suppress(Exception):
    from cohezion.agents.arc_specialists.manifold_agent import (
        ARCManifoldAgent as ARCManifoldAgent,
    )
