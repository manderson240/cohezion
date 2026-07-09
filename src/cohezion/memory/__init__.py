"""Memory and trust hierarchy for Cohezion agents."""

import contextlib


# Wiring-sweep 2026-06-22: trust_hierarchy was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.memory.trust_hierarchy import TrustedFact as TrustedFact
    from cohezion.memory.trust_hierarchy import TrustTier as TrustTier

# Wiring-sweep: mem0_adapter local-first memory integration.
with contextlib.suppress(Exception):
    from cohezion.memory import mem0_adapter as mem0_adapter
    from cohezion.memory.mem0_adapter import Mem0Config as Mem0Config
    from cohezion.memory.mem0_adapter import build_local_mem0 as build_local_mem0
    from cohezion.memory.mem0_adapter import mem0_available as mem0_available
