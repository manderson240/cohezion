"""Governance layer — AutonomyEngine, ConciergeAgent, KnowledgeBridge, FlumeBridge."""

import contextlib


# Wiring-sweep 2026-06-06: concierge was a genuine production orphan (ConciergeAgent had 0 src
# importers; only its test referenced it). Guarded re-export puts the documented governance
# component on the package surface + makes it statically reachable (cycle-safe, fail-soft).
with contextlib.suppress(Exception):
    from cohezion.governance.concierge import (
        ConciergeAgent as ConciergeAgent,
    )
    from cohezion.governance.concierge import (
        RoutingRecord as RoutingRecord,
    )
    from cohezion.governance.concierge import (
        RoutingSuggestion as RoutingSuggestion,
    )
    from cohezion.governance.concierge import (
        SessionBriefing as SessionBriefing,
    )
