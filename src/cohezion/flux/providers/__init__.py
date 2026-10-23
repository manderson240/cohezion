"""FLUX provider implementations — cache, history, SurrealDB, tools, vault."""

import contextlib


__all__ = [
    "CacheFlux",
    "HistoryFlux",
    "SurrealFlux",
    "ToolFlux",
    "VaultFlux",
]


with contextlib.suppress(Exception):
    from cohezion.flux.providers.cache_flux import CacheFlux as CacheFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.history_flux import HistoryFlux as HistoryFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.surreal_flux import SurrealFlux as SurrealFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.tool_flux import ToolFlux as ToolFlux

with contextlib.suppress(Exception):
    from cohezion.flux.providers.vault_flux import VaultFlux as VaultFlux

# Guarded imports above may fail; list only names that actually bound, so
# `from <package> import *` cannot raise on a missing optional dependency.
__all__ = [_name for _name in __all__ if _name in globals()]
