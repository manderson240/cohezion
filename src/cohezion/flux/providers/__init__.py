"""FLUX concrete providers — the FluxProvider implementations.

Public re-exports so each provider is reachable from a STATIC import edge in production
(`from cohezion.flux.providers import CacheFlux`), not only from the test suite. Before
this, `cache_flux`/`surreal_flux`/`tool_flux`/`vault_flux` were intra-package orphans —
imported by `tests/flux/test_providers.py` alone (wiring-sweep, 2026-06-06). `HistoryFlux`
is also imported by `flux/aggregator.py`; it is re-exported here too for a uniform surface.

The `X as X` alias form marks each name an intentional re-export (ruff keeps it; a plain
`from … import X` would be flagged F401). Non-destructive: this populated an empty
``__init__`` — it adds the missing import edges, it does not change provider behaviour
(the aggregator still registers providers explicitly at runtime).
"""

from cohezion.flux.providers.cache_flux import CacheFlux as CacheFlux
from cohezion.flux.providers.history_flux import HistoryFlux as HistoryFlux
from cohezion.flux.providers.surreal_flux import SurrealFlux as SurrealFlux
from cohezion.flux.providers.tool_flux import ToolFlux as ToolFlux
from cohezion.flux.providers.vault_flux import VaultFlux as VaultFlux


__all__ = [
    "CacheFlux",
    "HistoryFlux",
    "SurrealFlux",
    "ToolFlux",
    "VaultFlux",
]
