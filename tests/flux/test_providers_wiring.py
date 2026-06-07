"""Wiring test: flux/providers/__init__ re-exports every provider (wiring-sweep 2026-06-06).

Before this, the empty `flux/providers/__init__.py` left `cache_flux`/`surreal_flux`/
`tool_flux`/`vault_flux` reachable ONLY from the test suite (intra-package orphans). The
re-export adds the missing STATIC production import edge.

Discriminating: each test asserts the name re-exported from the PACKAGE is the SAME object
as the class in its module — so removing (or mis-pointing) a re-export edge FAILS, not just
"a name exists". A plain `hasattr(pkg, "CacheFlux")` would pass a wrong re-export; identity
does not.
"""

from __future__ import annotations

import cohezion.flux.providers as providers
from cohezion.flux.providers.cache_flux import CacheFlux
from cohezion.flux.providers.history_flux import HistoryFlux
from cohezion.flux.providers.surreal_flux import SurrealFlux
from cohezion.flux.providers.tool_flux import ToolFlux
from cohezion.flux.providers.vault_flux import VaultFlux


def test_each_provider_reexported_is_the_real_class() -> None:
    assert providers.CacheFlux is CacheFlux
    assert providers.HistoryFlux is HistoryFlux
    assert providers.SurrealFlux is SurrealFlux
    assert providers.ToolFlux is ToolFlux
    assert providers.VaultFlux is VaultFlux


def test_all_lists_every_provider() -> None:
    assert set(providers.__all__) == {
        "CacheFlux",
        "HistoryFlux",
        "SurrealFlux",
        "ToolFlux",
        "VaultFlux",
    }
