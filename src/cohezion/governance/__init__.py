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

# Wiring-sweep 2026-06-22: autonomy_engine, fleet_monitor, flume_bridge, guardian,
# knowledge_bridge, quadrature_nexus were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.governance.autonomy_engine import (
        AgentAutonomyState as AgentAutonomyState,
    )
    from cohezion.governance.autonomy_engine import (
        AutonomyTier as AutonomyTier,
    )

with contextlib.suppress(Exception):
    from cohezion.governance.fleet_monitor import (
        FleetMonitor as FleetMonitor,
    )

with contextlib.suppress(Exception):
    from cohezion.governance.guardian import (
        GuardianRegistry as GuardianRegistry,
    )

with contextlib.suppress(Exception):
    from cohezion.governance.knowledge_bridge import (
        Learning as Learning,
    )
    from cohezion.governance.knowledge_bridge import (
        persist_to_vault as persist_to_vault,
    )

with contextlib.suppress(Exception):
    from cohezion.governance.quadrature_nexus import (
        QuadratureNexus as QuadratureNexus,
    )

with contextlib.suppress(Exception):
    from cohezion.governance.flume_bridge import (
        data_product_similarity as data_product_similarity,
    )
    from cohezion.governance.flume_bridge import encode_prompt as encode_prompt
