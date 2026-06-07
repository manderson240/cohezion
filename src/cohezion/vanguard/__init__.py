"""Vanguard — source discovery, attribution, and sandbox validation for ingested artifacts.

Public re-exports so each vanguard module is reachable from a STATIC production import edge, not
only from the test suite. Before this, `vanguard/__init__.py` was empty, leaving `attribution`
and `connectors` as intra-package orphans (imported by `tests/vanguard/*` alone);
`sandbox_validation` (via `compound/executor_integration`) and `source_connector` (via
`connectors`/`attribution`) were already reachable. Re-exported here for a uniform surface
(wiring-sweep, 2026-06-07). The `X as X` alias marks each an intentional re-export.
"""

from cohezion.vanguard.attribution import AttributionEngine as AttributionEngine
from cohezion.vanguard.connectors import VanguardScoutReport as VanguardScoutReport
from cohezion.vanguard.sandbox_validation import SubstrateSandbox as SubstrateSandbox
from cohezion.vanguard.source_connector import SourceConnector as SourceConnector


__all__ = [
    "AttributionEngine",
    "SourceConnector",
    "SubstrateSandbox",
    "VanguardScoutReport",
]
