"""Memory and trust hierarchy for Cohezion agents."""

import contextlib

# Wiring-sweep 2026-06-22: trust_hierarchy was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.memory.trust_hierarchy import TrustTier as TrustTier
    from cohezion.memory.trust_hierarchy import TrustedFact as TrustedFact
