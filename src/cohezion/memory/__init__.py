"""Cohezion memory layer integrations.

Currently hosts the mem0 adapter (LLM-extracted conversational memory). This
package COMPLEMENTS the existing memory surfaces rather than replacing them:

  - cohezion.cache.SemanticCache  -> embedding similarity dedup (L1/L2/L3)
  - cohezion.persistence (SurrealDB) -> structured bi-temporal storage
  - cohezion.compound.JourneyTracker -> 12D agent trajectory
  - cohezion.mcp.servers.memory      -> Entity-Relation-Observation graph

mem0 owns LLM-extracted, self-consolidating conversational *facts*
(ADD/UPDATE/DELETE/NOOP dedup) — a capability none of the above provide.
"""

from __future__ import annotations

from cohezion.memory.mem0_adapter import (
    Mem0Config,
    build_local_mem0,
    mem0_available,
)


__all__ = ["Mem0Config", "build_local_mem0", "mem0_available"]
